#!/usr/bin/env python3
"""Varredura de SEED MESTRE contra as chaves conhecidas do Bitcoin Puzzle.

Motivacao
---------
O criador declarou "consecutive keys from a deterministic wallet (masked with
leading 000...0001)". Em toda carteira deterministica aditiva (BIP32, Electrum
v1) a chave filha e `m + H(...)`: as DIFERENCAS entre chaves de puzzle sao
pseudo-aleatorias mesmo que a seed mestre seja trivialmente fraca. Por isso os
testes de relacao ENTRE chaves do repositorio (LCG, linear, autocorrelacao,
hash-chain sobre chave mascarada) nao tem poder contra essa hipotese: eles
falhariam identicamente com uma seed de 16 bits.

O unico teste com poder e enumerar a SEED e reproduzir as chaves. E o que este
script faz.

Modelo de mascara
-----------------
    puzzle_n = 2**(n-1) | (child_{idx(n)} mod 2**(n-1))
    idx(n)   = index_base + (n - 1)

Estrategia
----------
A ancora e o puzzle resolvido com mais bits conhecidos (#130 -> 129 bits). Nas
familias de acesso aleatorio basta 1 derivacao para testar 129 bits, entao o
custo por candidato e ~1-2 HMAC (+1 multiplicacao k*G quando o ultimo nivel e
nao-endurecido). Sobreviventes sao confirmados contra TODAS as chaves conhecidas
e contra os enderecos.

Falso positivo na ancora: 2**-129 por candidato. Um acerto e conclusivo.

Uso
---
    python3 analysis/master_seed_sweep.py --self-test
    python3 analysis/master_seed_sweep.py --family bip32 --path "m/0/i" \
        --encoder mt256 --range 1400000000-1421345234 --jobs 8
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import random
import sys
import time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import secp_fast as EC  # noqa: E402

N = EC.N


# --------------------------------------------------------------------------
# dados
# --------------------------------------------------------------------------
def load_solved(path=None):
    path = path or os.path.join(HERE, "..", "data", "puzzles.json")
    with open(path) as f:
        puz = json.load(f)["puzzles"]
    return {p["puzzle"]: p["privkey_int"] for p in puz if p["status"] == "solved"}


def mask_low(n, value):
    """Mascara declarada pelo criador: zera os bits altos e forca o bit n-1."""
    return (value & ((1 << (n - 1)) - 1)) | (1 << (n - 1))


def mask_high(n, value):
    """Variante: usa os n bits ALTOS do filho de 256 bits, forcando o bit n-1."""
    top = value >> (256 - n)
    return (top & ((1 << (n - 1)) - 1)) | (1 << (n - 1))


def mask_low_le(n, value):
    """Variante: filho serializado em little-endian antes do truncamento."""
    le = int.from_bytes(value.to_bytes(32, "big")[::-1], "big")
    return (le & ((1 << (n - 1)) - 1)) | (1 << (n - 1))


MASKS = {"low": mask_low, "high": mask_high, "low_le": mask_low_le}
mask_of = mask_low  # compatibilidade


class IndexMap:
    """Mapeia numero de puzzle -> indice da carteira.

    consecutive: base + stride*(n-1)          (modelo assumido em todo o repo)
    reverse:     base + stride*(total - n)    (#256 no comeco da carteira)
    rejection:   sequencial com descarte — o criador sortearia filhos em ordem e
                 pularia os que nao tivessem o bit n-1 naturalmente setado. Nao
                 tem forma fechada: exige percorrer a sequencia.
    """

    def __init__(self, kind="consecutive", base=0, stride=1, total=256):
        if kind not in ("consecutive", "reverse", "rejection"):
            raise ValueError(kind)
        self.kind = kind
        self.base = base
        self.stride = stride
        self.total = total
        self.random_access = kind != "rejection"
        self.name = "%s(base=%d,stride=%d)" % (kind, base, stride)

    def index_for(self, n):
        if self.kind == "consecutive":
            return self.base + self.stride * (n - 1)
        if self.kind == "reverse":
            return self.base + self.stride * (self.total - n)
        raise TypeError("rejection nao tem forma fechada")

    def walk(self, fam, ctx, maskfn, wanted, max_draws):
        """Percorre a carteira atribuindo filhos aos puzzles 1,2,3,... por descarte.

        Devolve dict {puzzle: chave} ate o maior puzzle em `wanted`, ou None se
        estourar max_draws. Para no primeiro desacordo com `wanted`.
        """
        out = {}
        n = 1
        j = self.base
        top = max(wanted)
        drawn = 0
        while n <= top and drawn < max_draws:
            child = fam.child(ctx, j)
            j += self.stride
            drawn += 1
            if not (child >> (n - 1)) & 1:
                continue  # filho descartado: bit n-1 nao esta setado
            key = maskfn(n, child)
            if n in wanted and wanted[n] != key:
                return None
            out[n] = key
            n += 1
        return out if n > top else None


# --------------------------------------------------------------------------
# codificadores de seed: inteiro candidato -> bytes da seed
# --------------------------------------------------------------------------
def _mt256(t):
    return random.Random(t).getrandbits(256).to_bytes(32, "big")


def _mt128hex(t):
    return ("%032x" % random.Random(t).getrandbits(128)).encode()


# H9: `bx seed` do libbitcoin-explorer 2.0.0/2.1.0 (src/utility/utility.cpp):
#     std::default_random_engine engine(std::random_device()());
#     byte = engine() % std::numeric_limits<uint8_t>::max();   // % 255
# Uma unica seed de 32 bits; padrao -b 128 (16 bytes). default_random_engine e
# minstd_rand0 no libstdc++, minstd_rand no libc++ e mt19937 no MSVC. Nos dois
# LCG o estado e s mod (2^31-1), com 0 -> 1: o espaco util e t em [1, 2^31-1).
# Conferido contra C++ compilado (libc++) e vetores normativos [rand.predef].
_MINSTD_M = 2147483647


def _bx2_lcg(a, nbytes=16):
    def enc(t):
        x = t % _MINSTD_M or 1
        out = bytearray(nbytes)
        for j in range(nbytes):
            x = x * a % _MINSTD_M
            out[j] = x % 255
        return bytes(out)
    return enc


def _bx2_mt19937(t, nbytes=16):
    st = [t & 0xFFFFFFFF]
    for i in range(1, 624):
        p = st[-1]
        st.append((1812433253 * (p ^ (p >> 30)) + i) & 0xFFFFFFFF)
    r = random.Random()
    r.setstate((3, tuple(st + [624]), None))
    return bytes(r.getrandbits(32) % 255 for _ in range(nbytes))


ENCODERS = {
    "raw4be":    lambda t: (t & 0xFFFFFFFF).to_bytes(4, "big"),
    "raw4le":    lambda t: (t & 0xFFFFFFFF).to_bytes(4, "little"),
    "raw8be":    lambda t: (t & ((1 << 64) - 1)).to_bytes(8, "big"),
    "int256":    lambda t: t.to_bytes(32, "big"),  # inteiro pequeno como chave de 32 bytes
    "ascii":     lambda t: str(t).encode(),
    "asciihex":  lambda t: ("%x" % t).encode(),
    "sha256":    lambda t: hashlib.sha256(str(t).encode()).digest(),
    "mt256":     _mt256,     # os 32 bytes que random.seed(t) produziria
    "mt128hex":  _mt128hex,  # seed hex de 128 bits estilo Electrum v1
    "bx2-minstd0":    _bx2_lcg(16807),   # bx 2.0 `seed`, libstdc++ (Linux/GCC)
    "bx2-minstd":     _bx2_lcg(48271),   # bx 2.0 `seed`, libc++ (macOS/clang)
    "bx2-mt19937":    _bx2_mt19937,      # bx 2.0 `seed`, MSVC (Windows)
    "bx2-minstd0-256": _bx2_lcg(16807, 32),
    "bx2-minstd-256":  _bx2_lcg(48271, 32),
}


# --------------------------------------------------------------------------
# familias de derivacao
# --------------------------------------------------------------------------
def _hmac512(key, data):
    return hmac.new(key, data, hashlib.sha512).digest()


class Bip32:
    """BIP32 com caminho fixo terminando no indice variavel.

    path: "m/0/i", "m/0h/i", "m/i", "m/ih", "m/44h/0h/0h/0/i", ...
    O sufixo 'h' marca nivel endurecido.
    """

    random_access = True

    def __init__(self, path="m/0/i"):
        parts = path.strip().split("/")
        if parts[0] != "m" or len(parts) < 2:
            raise ValueError("caminho invalido: %s" % path)
        leaf = parts[-1]
        if leaf not in ("i", "ih"):
            raise ValueError("ultimo nivel do caminho deve ser 'i' ou 'ih'")
        self.leaf_hardened = leaf == "ih"
        self.fixed = []
        for p in parts[1:-1]:
            hardened = p.endswith("h") or p.endswith("'")
            num = int(p.rstrip("h'"))
            self.fixed.append(num + (0x80000000 if hardened else 0))
        self.name = "bip32:" + path

    @staticmethod
    def _ckd(k, cc, index):
        if index >= 0x80000000:
            data = b"\x00" + k.to_bytes(32, "big") + index.to_bytes(4, "big")
        else:
            pt = EC.mul_g(k)
            data = EC.ser_compressed(pt) + index.to_bytes(4, "big")
        I = _hmac512(cc, data)
        return (int.from_bytes(I[:32], "big") + k) % N, I[32:]

    def prepare(self, seed):
        I = _hmac512(b"Bitcoin seed", seed)
        k = int.from_bytes(I[:32], "big")
        cc = I[32:]
        if k == 0 or k >= N:
            return None
        for index in self.fixed:
            k, cc = self._ckd(k, cc, index)
        ser = None
        if not self.leaf_hardened:
            ser = EC.ser_compressed(EC.mul_g(k))
        return (k, cc, ser)

    def child(self, ctx, index):
        k, cc, ser = ctx
        if self.leaf_hardened:
            index |= 0x80000000
            data = b"\x00" + k.to_bytes(32, "big") + index.to_bytes(4, "big")
        else:
            data = ser + index.to_bytes(4, "big")
        I = _hmac512(cc, data)
        return (int.from_bytes(I[:32], "big") + k) % N


class HashSeq:
    """child_i = H(seed || enc(i)) — gerador ingenuo indexado."""

    random_access = True

    def __init__(self, hash_name="sha256", index_enc="be4"):
        self.hash_name = hash_name
        self.index_enc = index_enc
        self.name = "hashseq:%s/%s" % (hash_name, index_enc)

    def _h(self, b):
        if self.hash_name == "sha256d":
            return hashlib.sha256(hashlib.sha256(b).digest()).digest()
        return hashlib.new(self.hash_name, b).digest()

    def _enc(self, i):
        if self.index_enc == "be4":
            return i.to_bytes(4, "big")
        if self.index_enc == "le4":
            return i.to_bytes(4, "little")
        if self.index_enc == "str":
            return str(i).encode()
        raise ValueError(self.index_enc)

    def prepare(self, seed):
        return seed

    def child(self, ctx, index):
        return int.from_bytes(self._h(ctx + self._enc(index)), "big") % N


class HashChain:
    """x_0 = H(seed); x_{i+1} = H(x_i); child_i = x_i (estado inteiro, nao mascarado)."""

    random_access = False

    def __init__(self, hash_name="sha256"):
        self.hash_name = hash_name
        self.name = "hashchain:%s" % hash_name

    def _h(self, b):
        if self.hash_name == "sha256d":
            return hashlib.sha256(hashlib.sha256(b).digest()).digest()
        return hashlib.new(self.hash_name, b).digest()

    def prepare(self, seed):
        return {"seed": seed, "cache": {}}

    def child(self, ctx, index):
        cache = ctx["cache"]
        if index in cache:
            return cache[index]
        x = self._h(ctx["seed"])
        cache[0] = int.from_bytes(x, "big") % N
        for i in range(1, index + 1):
            x = self._h(x)
            cache[i] = int.from_bytes(x, "big") % N
        return cache[index]


def _sha256d(b):
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def _armory_hmac256(key, msg):
    """HMAC do Armory (ArmoryUtils.HMAC com hashsz=32): a chave e completada ate
    32 bytes, NAO ate o bloco de 64 do SHA-256. Difere do HMAC-SHA256 padrao."""
    key = hashlib.sha256(key).digest() if len(key) > 32 else key
    key = key.ljust(32, b"\0")
    okey = bytes(0x5C ^ c for c in key)
    ikey = bytes(0x36 ^ c for c in key)
    return hashlib.sha256(okey + hashlib.sha256(ikey + msg).digest()).digest()


class Armory:
    """Carteira deterministica do Armory, wallet 1.35 (0.88 a 0.93, 2013-2015).

    Fonte: etotheipi/BitcoinArmory 24550b6 (2015-01-15),
    CryptoECDSA::ComputeChainedPrivateKey e PyBtcWallet.createNewWallet:
        cc  = HMAC256(SHA256d(root), 'Derive Chaincode from Root Key')
        k_i = (int(SHA256d(pub65(k_{i-1})) XOR cc) * k_{i-1}) mod n,  k_{-1} = root
    Cadeia sequencial com pubkey NAO comprimida. O primeiro endereco da carteira e
    k_0; com root_first o proprio root conta como indice 0.
    """

    random_access = True
    ascending_checks = True  # cada passo custa um k*G: rejeitar pelos puzzles pequenos

    def __init__(self, root_first=False):
        self.offset = 0 if root_first else 1
        self.name = "armory135" + (":root0" if root_first else "")

    def prepare(self, seed):
        if len(seed) != 32:
            raise ValueError("raiz do Armory tem 32 bytes; use um encoder de 32 bytes")
        k = int.from_bytes(seed, "big")
        if not 0 < k < N:
            return None
        cc = _armory_hmac256(_sha256d(seed), b"Derive Chaincode from Root Key")
        return {"chain": [k], "cc": int.from_bytes(cc, "big")}

    @staticmethod
    def step(k, cc):
        pub = EC.ser_uncompressed(EC.mul_g(k))
        return (int.from_bytes(_sha256d(pub), "big") ^ cc) * k % N

    def child(self, ctx, index):
        chain, j = ctx["chain"], index + self.offset
        while len(chain) <= j:
            chain.append(self.step(chain[-1], ctx["cc"]))
        return chain[j]


class ElectrumV1:
    """Electrum 1.x OldAccount: m = stretch(seed); child = (m + H(i:branch:MPK)) mod n.

    CARO: 100.000 SHA256 por candidato. Use apenas em espacos de seed pequenos.
    """

    random_access = True

    def __init__(self, branch=0):
        self.branch = branch
        self.name = "electrum1:branch%d" % branch

    @staticmethod
    def stretch(seed):
        x = seed
        for _ in range(100000):
            x = hashlib.sha256(x + seed).digest()
        return int.from_bytes(x, "big")

    def prepare(self, seed):
        m = self.stretch(seed) % N
        if m == 0:
            return None
        return (m, EC.ser_xy(EC.mul_g(m)))

    def child(self, ctx, index):
        m, mpk = ctx
        d = hashlib.sha256(
            hashlib.sha256(("%d:%d:" % (index, self.branch)).encode() + mpk).digest()
        ).digest()
        return (m + int.from_bytes(d, "big")) % N


def build_family(args):
    if args.family == "bip32":
        return Bip32(args.path)
    if args.family == "hashseq":
        return HashSeq(args.hash, args.index_enc)
    if args.family == "hashchain":
        return HashChain(args.hash)
    if args.family == "electrum1":
        return ElectrumV1(args.branch)
    if args.family == "armory":
        return Armory(root_first=getattr(args, "armory_root", False))
    raise ValueError(args.family)


# --------------------------------------------------------------------------
# nucleo da varredura
# --------------------------------------------------------------------------
_W = {}


def _init_worker(state):
    _W.update(state)


def _scan_chunk(bounds):
    lo, hi = bounds
    fam = _W["family"]
    enc = ENCODERS[_W["encoder"]]
    imap = _W["index_map"]
    maskfn = MASKS[_W["mask"]]
    anchor_n, anchor_key = _W["anchor"]
    checks = _W["checks"]
    nm_bits = _W.get("near_miss_bits") or 0
    nm_mask = (1 << nm_bits) - 1
    nm_target = anchor_key & nm_mask
    max_draws = _W.get("max_draws", 4096)
    hits = []
    near = []
    partial = []  # ancora casa (129 bits, conclusivo) mas nem todas as outras chaves

    J = _W.get("any_index") or 0
    if J:
        # Modo sem indice: cada filho 0..J-1 e procurado entre TODAS as chaves com
        # n >= any_min_n. Cobre geradores intercalados, lotes, offsets, ordem
        # invertida e chaves a mao. Chave do dicionario: 32 bits baixos (mascara low).
        min_n = _W["any_min_n"]
        pool = {}
        for n, k in checks + [(anchor_n, anchor_key)]:
            if n >= min_n:
                pool.setdefault(k & 0xFFFFFFFF, []).append((n, k))
        for t in range(lo, hi):
            ctx = fam.prepare(enc(t))
            if ctx is None:
                continue
            for j in range(J):
                c = fam.child(ctx, j)
                for n, k in pool.get(c & 0xFFFFFFFF, ()):
                    if maskfn(n, c) == k:
                        partial.append((t, n, j))
        return lo, hi, hits, near, partial

    if imap.random_access and getattr(fam, "ascending_checks", False):
        # familia sequencial cara: confere na ordem do indice da carteira e para no
        # primeiro desacordo (o #2 ja rejeita metade, o #3 mais 3/4...)
        asc = sorted(checks + [(anchor_n, anchor_key)], key=lambda nk: imap.index_for(nk[0]))
        asc = [(imap.index_for(n), n, k) for n, k in asc]
        for t in range(lo, hi):
            ctx = fam.prepare(enc(t))
            if ctx is None:
                continue
            if all(maskfn(n, fam.child(ctx, i)) == k for i, n, k in asc):
                hits.append(t)
    elif imap.random_access:
        anchor_idx = imap.index_for(anchor_n)
        for t in range(lo, hi):
            ctx = fam.prepare(enc(t))
            if ctx is None:
                continue
            key = maskfn(anchor_n, fam.child(ctx, anchor_idx))
            if nm_bits and ((key ^ anchor_key) & nm_mask) == 0:
                near.append((t, key & nm_mask))
            if key != anchor_key:
                continue
            # As chaves podem nao ter saido todas da mesma geracao (lotes, ramos,
            # offsets diferentes). A ancora sozinha ja e conclusiva para o #130:
            # nunca descartar o candidato por falhar nas demais.
            matched = [n for n, k in checks if maskfn(n, fam.child(ctx, imap.index_for(n))) == k]
            if len(matched) == len(checks):
                hits.append(t)
            else:
                partial.append((t, len(matched)))
    else:
        wanted = dict(checks)
        wanted[anchor_n] = anchor_key
        for t in range(lo, hi):
            ctx = fam.prepare(enc(t))
            if ctx is None:
                continue
            if imap.walk(fam, ctx, maskfn, wanted, max_draws) is not None:
                hits.append(t)
    return lo, hi, hits, near, partial


def sweep(family, encoder, lo, hi, solved, index_map=None, jobs=1, chunk=20000,
          progress=True, near_miss_bits=0, mask="low", max_draws=4096, skip_below=1,
          any_index=0, any_min_n=56):
    if any_index and mask != "low":
        raise ValueError("--any-index so implementado para mascara low")
    if index_map is None:
        index_map = IndexMap("consecutive", 0)
    if isinstance(index_map, int):           # compat: inteiro = base consecutivo
        index_map = IndexMap("consecutive", index_map)
    # skip_below: as primeiras chaves podem ter sido escolhidas a mao; elas saem da
    # confirmacao e do filtro sequencial (a carteira pode comecar em #skip_below).
    solved = {n: k for n, k in solved.items() if n >= skip_below}
    if index_map.random_access and index_map.index_for(min(solved)) < 0:
        raise ValueError("index_base deixa indice negativo para #%d; aumente --skip-below"
                         % min(solved))
    anchor_n = max(solved)
    anchor = (anchor_n, solved[anchor_n])
    checks = sorted(((n, k) for n, k in solved.items() if n != anchor_n), reverse=True)
    state = {
        "family": family, "encoder": encoder, "index_map": index_map,
        "mask": mask, "max_draws": max_draws,
        "anchor": anchor, "checks": checks, "near_miss_bits": near_miss_bits,
        "any_index": any_index, "any_min_n": any_min_n,
    }
    bounds = [(a, min(a + chunk, hi)) for a in range(lo, hi, chunk)]
    hits = []
    near = []
    done = 0
    t0 = time.perf_counter()
    if jobs <= 1:
        _init_worker(state)
        it = map(_scan_chunk, bounds)
    else:
        pool = Pool(jobs, initializer=_init_worker, initargs=(state,))
        it = pool.imap_unordered(_scan_chunk, bounds)
    partial = []
    for a, b, h, nm, pt in it:
        done += b - a
        hits.extend(h)
        near.extend(nm)
        partial.extend(pt)
        if progress and time.perf_counter() - t0 > 2:
            rate = done / (time.perf_counter() - t0)
            pct = 100.0 * done / max(1, hi - lo)
            sys.stderr.write("\r  %.1f%%  %d/%d  %.0f cand/s  hits=%d   "
                             % (pct, done, hi - lo, rate, len(hits)))
            sys.stderr.flush()
    if jobs > 1:
        pool.close()
        pool.join()
    if progress:
        sys.stderr.write("\n")
    return {
        "family": family.name,
        "encoder": encoder,
        "mask": mask,
        "index_map": index_map.name,
        "index_base": index_map.base,
        "range": [lo, hi],
        "candidates": hi - lo,
        "anchor_puzzle": anchor_n,
        "anchor_bits": anchor_n - 1,
        "confirm_puzzles": len(checks),
        "skip_below": skip_below,
        "any_index": any_index,
        "any_index_min_n": any_min_n if any_index else None,
        "elapsed_s": round(time.perf_counter() - t0, 3),
        "rate_per_s": round((hi - lo) / max(1e-9, time.perf_counter() - t0), 1),
        "hits": hits,
        # sem --any-index: (candidato, chaves confirmadas alem da ancora)
        # com --any-index: (candidato, puzzle, indice do filho) para cada chave achada
        "anchor_only": sorted(partial),
        "near_miss_bits": near_miss_bits,
        "near_miss_observed": len(near),
        "near_miss_expected": round((hi - lo) / float(1 << near_miss_bits), 3) if near_miss_bits else None,
        "near_miss": sorted(near)[:200],
    }


# --------------------------------------------------------------------------
# controles sinteticos
# --------------------------------------------------------------------------
def synthetic_keys(family, seed_bytes, puzzles, index_map=None, mask="low"):
    if index_map is None:
        index_map = IndexMap("consecutive", 0)
    if isinstance(index_map, int):
        index_map = IndexMap("consecutive", index_map)
    ctx = family.prepare(seed_bytes)
    maskfn = MASKS[mask]
    if index_map.random_access:
        return {n: maskfn(n, family.child(ctx, index_map.index_for(n))) for n in puzzles}
    # rejection: percorre a carteira gerando a sequencia inteira
    out = {}
    n, j = 1, index_map.base
    top = max(puzzles)
    while n <= top:
        child = family.child(ctx, j)
        j += index_map.stride
        if (child >> (n - 1)) & 1:
            out[n] = maskfn(n, child)
            n += 1
    return {n: out[n] for n in puzzles}


def _one_control(fam, encname, imap, mask, real, puzzles, jobs):
    lo, hi, secret = 900000, 900400, 900137
    keys = synthetic_keys(fam, ENCODERS[encname](secret), puzzles, imap, mask)
    kw = dict(index_map=imap, mask=mask, jobs=jobs, chunk=100, progress=False)
    pos = sweep(fam, encname, lo, hi, keys, **kw)
    tampered = dict(keys)
    tampered[max(tampered)] ^= 1
    neg = sweep(fam, encname, lo, hi, tampered, **kw)
    realneg = sweep(fam, encname, lo, hi, real, **kw)
    rec = {
        "family": fam.name, "encoder": encname, "index_map": imap.name, "mask": mask,
        "positive_recovered": pos["hits"] == [secret],
        "tampered_rejected": neg["hits"] == [],
        "real_data_no_hit_in_control_range": realneg["hits"] == [],
        "rate_per_s": pos["rate_per_s"],
    }
    rec["ok"] = (rec["positive_recovered"] and rec["tampered_rejected"]
                 and rec["real_data_no_hit_in_control_range"])
    print("  %-24s enc=%-9s %-26s mask=%-7s rec=%-5s adult_rej=%-5s %8.0f c/s"
          % (fam.name, encname, imap.name, mask, rec["positive_recovered"],
             rec["tampered_rejected"], rec["rate_per_s"]))
    return rec


def self_test(jobs=1):
    real = load_solved()
    puzzles = sorted(real)
    results = []
    CONS = IndexMap("consecutive", 0)
    print("\n-- familias (mapa consecutivo, mascara low) --")
    for fam, encname in [
        (Bip32("m/0/i"), "raw4be"),
        (Bip32("m/0h/i"), "raw4be"),
        (Bip32("m/ih"), "mt256"),
        (Bip32("m/44h/0h/0h/0/i"), "raw4be"),
        (HashSeq("sha256", "be4"), "raw4be"),
        (HashSeq("sha256d", "str"), "ascii"),
        (HashChain("sha256"), "raw4be"),
        (ElectrumV1(0), "mt128hex"),
    ]:
        results.append(_one_control(fam, encname, CONS, "low", real, puzzles, jobs))

    print("\n-- bx 2.0 `seed` -> hd-new -> hd-private (H9) --")
    for fam, encname in [
        (Bip32("m/i"), "bx2-minstd0"),
        (Bip32("m/ih"), "bx2-minstd"),
        (Bip32("m/i"), "bx2-mt19937"),
        (Bip32("m/0/i"), "bx2-minstd0-256"),
    ]:
        results.append(_one_control(fam, encname, CONS, "low", real, puzzles, jobs))

    print("\n-- Armory wallet 1.35 (H10) --")
    for fam, encname, imap in [
        (Armory(), "sha256", CONS),
        (Armory(root_first=True), "int256", CONS),
        (Armory(), "int256", IndexMap("consecutive", 3)),
    ]:
        results.append(_one_control(fam, encname, imap, "low", real, puzzles, jobs))

    print("\n-- geracao em lotes: so a ancora vem da seed --")
    lo, hi, secret = 900000, 900400, 900137
    for fam, encname in [(Bip32("m/0h/i"), "raw4be"), (HashSeq("sha256", "be4"), "raw4be")]:
        mixed = synthetic_keys(fam, ENCODERS[encname](secret + 1), puzzles, CONS, "low")
        mixed[max(puzzles)] = synthetic_keys(fam, ENCODERS[encname](secret), [max(puzzles)],
                                             CONS, "low")[max(puzzles)]
        r = sweep(fam, encname, lo, hi, mixed, index_map=CONS, jobs=jobs, chunk=100, progress=False)
        # uma ancora so enxerga o lote do #130; o outro lote fica invisivel (por desenho)
        ok = r["hits"] == [] and [t for t, _ in r["anchor_only"]] == [secret]
        print("  %-24s enc=%-9s ancora isolada -> anchor_only=%s, carteira do lote -> hits=%s  ok=%s"
              % (fam.name, encname, [t for t, _ in r["anchor_only"]], r["hits"], ok))
        results.append({"family": fam.name, "encoder": encname, "control": "batch_anchor_only",
                        "ok": ok})

    print("\n-- primeiras chaves feitas a mao (skip-below + base negativa) --")
    import random as _r
    rng = _r.Random(5)
    for fam, encname in [(Armory(), "int256"), (Bip32("m/0h/i"), "raw4be")]:
        imap = IndexMap("consecutive", -5)          # carteira comeca no puzzle #6
        keys = synthetic_keys(fam, ENCODERS[encname](secret), [n for n in puzzles if n >= 6],
                              imap, "low")
        for n in range(1, 6):                        # #1..#5 escolhidas a mao
            keys[n] = (1 << (n - 1)) | rng.getrandbits(max(n - 1, 0)) if n > 1 else 1
        kw = dict(index_map=imap, jobs=jobs, chunk=100, progress=False)
        found = sweep(fam, encname, lo, hi, keys, skip_below=6, **kw)
        strict = sweep(fam, encname, lo, hi, keys, index_map=IndexMap("consecutive", 0),
                       jobs=jobs, chunk=100, progress=False)
        ok = found["hits"] == [secret] and strict["hits"] == []
        print("  %-24s enc=%-9s skip_below=6 base=-5 -> hits=%s ; modelo antigo -> hits=%s  ok=%s"
              % (fam.name, encname, found["hits"], strict["hits"], ok))
        results.append({"family": fam.name, "encoder": encname, "control": "handmade_first_keys",
                        "ok": ok})

    print("\n-- dois geradores intercalados (--any-index) --")
    for fam, encname in [(Bip32("m/0h/i"), "raw4be"), (HashSeq("sha256", "be4"), "raw4be")]:
        rng = _r.Random(9)
        keys = {n: (1 << (n - 1)) | rng.getrandbits(n - 1) if n > 1 else 1 for n in puzzles}
        a = synthetic_keys(fam, ENCODERS[encname](secret), list(range(1, 257)),
                           IndexMap("consecutive", 0), "low")
        # gerador A deu os puzzles pares >= 60 nos seus filhos 0,1,2,...; o resto e outro gerador
        planted = {}
        for j, n in enumerate(n for n in puzzles if n >= 60 and n % 2 == 0):
            child = fam.child(fam.prepare(ENCODERS[encname](secret)), j)
            keys[n] = MASKS["low"](n, child)
            planted[n] = j
        r = sweep(fam, encname, lo, hi, keys, index_map=CONS, jobs=jobs, chunk=100,
                  progress=False, any_index=32)
        got = {(n, j) for t, n, j in r["anchor_only"] if t == secret}
        others = [x for x in r["anchor_only"] if x[0] != secret]
        ok = got == set(planted.items()) and not others and r["hits"] == []
        print("  %-24s enc=%-9s J=32 plantadas=%d achadas=%d falsos=%d  ok=%s"
              % (fam.name, encname, len(planted), len(got), len(others), ok))
        results.append({"family": fam.name, "encoder": encname, "control": "interleaved_any_index",
                        "ok": ok})

    print("\n-- variantes de mascara (H2) --")
    for mask in ("high", "low_le"):
        for fam, encname in [(Bip32("m/0h/i"), "raw4be"), (HashSeq("sha256", "be4"), "raw4be")]:
            results.append(_one_control(fam, encname, CONS, mask, real, puzzles, jobs))

    print("\n-- variantes de mapa de indice (H2) --")
    for imap in (IndexMap("consecutive", 7), IndexMap("consecutive", 0, stride=2),
                 IndexMap("reverse", 0), IndexMap("rejection", 0)):
        for fam, encname in [(Bip32("m/0h/i"), "raw4be"), (HashSeq("sha256", "be4"), "raw4be")]:
            results.append(_one_control(fam, encname, imap, "low", real, puzzles, jobs))
    return results


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--family", choices=["bip32", "hashseq", "hashchain", "electrum1", "armory"],
                    default="bip32")
    ap.add_argument("--path", default="m/0/i", help="caminho BIP32, ex: m/0h/i")
    ap.add_argument("--hash", default="sha256")
    ap.add_argument("--index-enc", default="be4", choices=["be4", "le4", "str"])
    ap.add_argument("--branch", type=int, default=0, help="ramo do Electrum v1")
    ap.add_argument("--armory-root", action="store_true",
                    help="Armory: o proprio root e o indice 0 da carteira")
    ap.add_argument("--encoder", default="mt256", choices=sorted(ENCODERS))
    ap.add_argument("--range", help="LO-HI (inteiros; unix time e so um inteiro)")
    ap.add_argument("--index-base", type=int, default=0)
    ap.add_argument("--index-map", default="consecutive",
                    choices=["consecutive", "reverse", "rejection"])
    ap.add_argument("--index-stride", type=int, default=1)
    ap.add_argument("--any-index", type=int, default=0, metavar="J",
                    help="procura cada filho 0..J-1 entre todas as chaves com n >= --any-min-n "
                         "(geradores intercalados/lotes/offsets); custo x J")
    ap.add_argument("--any-min-n", type=int, default=56,
                    help="menor puzzle usado no modo --any-index (falso positivo 2^-(n-1) por teste)")
    ap.add_argument("--skip-below", type=int, default=1, metavar="N",
                    help="ignora #1..#N-1 (possivelmente feitas a mao); use --index-base=-K "
                         "para carteira que comeca no puzzle K+1")
    ap.add_argument("--mask", default="low", choices=sorted(MASKS),
                    help="low = mascara declarada pelo criador; high = n bits altos; "
                         "low_le = filho em little-endian antes do truncamento")
    ap.add_argument("--max-draws", type=int, default=4096,
                    help="limite de filhos sorteados por candidato no mapa rejection")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2)))
    ap.add_argument("--chunk", type=int, default=20000)
    ap.add_argument("--near-miss", type=int, default=0, metavar="BITS",
                    help="registra candidatos que casam os BITS baixos da ancora "
                         "(falsos positivos de um filtro mais fraco)")
    ap.add_argument("--puzzles-json", default=None)
    ap.add_argument("--output", default=None)
    args = ap.parse_args()

    if args.self_test:
        print("CONTROLES SINTETICOS (positivo + adulterado + dados reais)")
        res = self_test(jobs=1)
        allok = all(r["ok"] for r in res)
        print("\n  todos os controles passaram: %s" % allok)
        if args.output:
            with open(args.output, "w") as f:
                json.dump({"self_test": res, "all_ok": allok}, f, indent=1)
        return 0 if allok else 1

    if not args.range:
        ap.error("--range e obrigatorio fora de --self-test")
    lo, hi = (int(x, 0) for x in args.range.split("-", 1))
    solved = load_solved(args.puzzles_json)
    fam = build_family(args)
    imap = IndexMap(args.index_map, args.index_base, args.index_stride)
    print("familia=%s encoder=%s mask=%s indices=%s ancora=#%d (%d bits) confirmacao=%d chaves"
          % (fam.name, args.encoder, args.mask, imap.name, max(solved), max(solved) - 1,
             len(solved) - 1))
    print("candidatos=%d jobs=%d" % (hi - lo, args.jobs))
    out = sweep(fam, args.encoder, lo, hi, solved, imap, args.jobs,
                args.chunk, near_miss_bits=args.near_miss, mask=args.mask,
                max_draws=args.max_draws, skip_below=args.skip_below,
                any_index=args.any_index, any_min_n=args.any_min_n)
    out["hits_detail"] = []
    for t in out["hits"] + sorted({a[0] for a in out["anchor_only"]}):
        ctx = fam.prepare(ENCODERS[args.encoder](t))
        det = {"candidate": t, "seed_hex": ENCODERS[args.encoder](t).hex()}
        if imap.random_access:
            det["predicted_71"] = hex(MASKS[args.mask](71, fam.child(ctx, imap.index_for(71))))
        else:
            seq = synthetic_keys(fam, ENCODERS[args.encoder](t), [71], imap, args.mask)
            det["predicted_71"] = hex(seq[71])
        out["hits_detail"].append(det)
    # candidatos acertados sao a seed: so contagens no stdout/log; detalhes so no --output
    printable = {k: v for k, v in out.items()
                 if k not in ("hits_detail", "near_miss", "hits", "anchor_only")}
    printable["hits_count"] = len(out["hits"])
    printable["anchor_only_count"] = len(out["anchor_only"])
    print(json.dumps(printable, indent=1))
    if args.near_miss:
        print("\n  falsos positivos com filtro de %d bits (ate 200 listados):" % args.near_miss)
        for t, v in out["near_miss"][:200]:
            print("    candidato=%-12d bits_baixos_da_ancora=0x%x" % (t, v))
    if out["anchor_only"]:
        print("\n  *** ACERTO DA ANCORA (#%d) SEM CARTEIRA COMPLETA *** lotes/offsets diferentes?"
              % out["anchor_puzzle"])
        print("  NAO publique; siga o protocolo de acerto da skill puzzle-research.")
    if out["hits"]:
        print("\n  *** ACERTO *** detalhes so no arquivo --output; siga o protocolo da skill.")
    if args.output:
        with open(args.output, "w") as f:
            json.dump(out, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
