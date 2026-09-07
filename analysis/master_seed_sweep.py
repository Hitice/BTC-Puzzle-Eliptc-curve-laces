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


def mask_of(n, value):
    """Aplica a mascara declarada pelo criador a um inteiro derivado."""
    return (value & ((1 << (n - 1)) - 1)) | (1 << (n - 1))


# --------------------------------------------------------------------------
# codificadores de seed: inteiro candidato -> bytes da seed
# --------------------------------------------------------------------------
def _mt256(t):
    return random.Random(t).getrandbits(256).to_bytes(32, "big")


def _mt128hex(t):
    return ("%032x" % random.Random(t).getrandbits(128)).encode()


ENCODERS = {
    "raw4be":    lambda t: (t & 0xFFFFFFFF).to_bytes(4, "big"),
    "raw4le":    lambda t: (t & 0xFFFFFFFF).to_bytes(4, "little"),
    "raw8be":    lambda t: (t & ((1 << 64) - 1)).to_bytes(8, "big"),
    "ascii":     lambda t: str(t).encode(),
    "asciihex":  lambda t: ("%x" % t).encode(),
    "sha256":    lambda t: hashlib.sha256(str(t).encode()).digest(),
    "mt256":     _mt256,     # os 32 bytes que random.seed(t) produziria
    "mt128hex":  _mt128hex,  # seed hex de 128 bits estilo Electrum v1
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
    base = _W["index_base"]
    anchor_n, anchor_key = _W["anchor"]
    anchor_idx = base + anchor_n - 1
    checks = _W["checks"]
    nm_bits = _W.get("near_miss_bits") or 0
    nm_mask = (1 << nm_bits) - 1
    nm_target = anchor_key & nm_mask
    hits = []
    near = []
    for t in range(lo, hi):
        ctx = fam.prepare(enc(t))
        if ctx is None:
            continue
        child = fam.child(ctx, anchor_idx)
        if nm_bits and (child & nm_mask) == nm_target:
            near.append((t, child & nm_mask))
        if mask_of(anchor_n, child) != anchor_key:
            continue
        # confirmacao completa
        if all(mask_of(n, fam.child(ctx, base + n - 1)) == k for n, k in checks):
            hits.append(t)
    return lo, hi, hits, near


def sweep(family, encoder, lo, hi, solved, index_base=0, jobs=1, chunk=20000,
          progress=True, near_miss_bits=0):
    anchor_n = max(solved)
    anchor = (anchor_n, solved[anchor_n])
    checks = sorted(((n, k) for n, k in solved.items() if n != anchor_n), reverse=True)
    state = {
        "family": family, "encoder": encoder, "index_base": index_base,
        "anchor": anchor, "checks": checks, "near_miss_bits": near_miss_bits,
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
    for a, b, h, nm in it:
        done += b - a
        hits.extend(h)
        near.extend(nm)
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
        "index_base": index_base,
        "range": [lo, hi],
        "candidates": hi - lo,
        "anchor_puzzle": anchor_n,
        "anchor_bits": anchor_n - 1,
        "confirm_puzzles": len(checks),
        "elapsed_s": round(time.perf_counter() - t0, 3),
        "rate_per_s": round((hi - lo) / max(1e-9, time.perf_counter() - t0), 1),
        "hits": hits,
        "near_miss_bits": near_miss_bits,
        "near_miss_observed": len(near),
        "near_miss_expected": round((hi - lo) / float(1 << near_miss_bits), 3) if near_miss_bits else None,
        "near_miss": sorted(near)[:200],
    }


# --------------------------------------------------------------------------
# controles sinteticos
# --------------------------------------------------------------------------
def synthetic_keys(family, seed_bytes, puzzles, index_base=0):
    ctx = family.prepare(seed_bytes)
    return {n: mask_of(n, family.child(ctx, index_base + n - 1)) for n in puzzles}


def self_test(jobs=1):
    real = load_solved()
    puzzles = sorted(real)
    results = []
    cases = [
        (Bip32("m/0/i"), "raw4be"),
        (Bip32("m/0h/i"), "raw4be"),
        (Bip32("m/ih"), "mt256"),
        (Bip32("m/44h/0h/0h/0/i"), "raw4be"),
        (HashSeq("sha256", "be4"), "raw4be"),
        (HashSeq("sha256d", "str"), "ascii"),
        (HashChain("sha256"), "raw4be"),
        (ElectrumV1(0), "mt128hex"),
    ]
    for fam, encname in cases:
        lo, hi = 900000, 900400
        secret = 900137
        keys = synthetic_keys(fam, ENCODERS[encname](secret), puzzles)
        pos = sweep(fam, encname, lo, hi, keys, jobs=jobs, chunk=100, progress=False)
        tampered = dict(keys)
        top = max(tampered)
        tampered[top] ^= 1
        neg = sweep(fam, encname, lo, hi, tampered, jobs=jobs, chunk=100, progress=False)
        # controle negativo 2: dados reais nao devem casar nesse intervalo minusculo
        realneg = sweep(fam, encname, lo, hi, real, jobs=jobs, chunk=100, progress=False)
        ok = pos["hits"] == [secret] and neg["hits"] == [] and realneg["hits"] == []
        results.append({
            "family": fam.name, "encoder": encname,
            "positive_recovered": pos["hits"] == [secret],
            "tampered_rejected": neg["hits"] == [],
            "real_data_no_hit_in_control_range": realneg["hits"] == [],
            "rate_per_s": pos["rate_per_s"], "ok": ok,
        })
        print("  %-28s enc=%-9s recuperou=%s  adulterado_rejeitado=%s  %.0f cand/s"
              % (fam.name, encname, pos["hits"] == [secret], neg["hits"] == [],
                 pos["rate_per_s"]))
    return results


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--family", choices=["bip32", "hashseq", "hashchain", "electrum1"],
                    default="bip32")
    ap.add_argument("--path", default="m/0/i", help="caminho BIP32, ex: m/0h/i")
    ap.add_argument("--hash", default="sha256")
    ap.add_argument("--index-enc", default="be4", choices=["be4", "le4", "str"])
    ap.add_argument("--branch", type=int, default=0, help="ramo do Electrum v1")
    ap.add_argument("--encoder", default="mt256", choices=sorted(ENCODERS))
    ap.add_argument("--range", help="LO-HI (inteiros; unix time e so um inteiro)")
    ap.add_argument("--index-base", type=int, default=0)
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
    print("familia=%s encoder=%s index_base=%d ancora=#%d (%d bits) confirmacao=%d chaves"
          % (fam.name, args.encoder, args.index_base, max(solved), max(solved) - 1,
             len(solved) - 1))
    print("candidatos=%d jobs=%d" % (hi - lo, args.jobs))
    out = sweep(fam, args.encoder, lo, hi, solved, args.index_base, args.jobs,
                args.chunk, near_miss_bits=args.near_miss)
    out["hits_detail"] = []
    for t in out["hits"]:
        ctx = fam.prepare(ENCODERS[args.encoder](t))
        out["hits_detail"].append({
            "candidate": t,
            "seed_hex": ENCODERS[args.encoder](t).hex(),
            "predicted_71": hex(mask_of(71, fam.child(ctx, args.index_base + 70))),
        })
    printable = {k: v for k, v in out.items() if k not in ("hits_detail", "near_miss")}
    print(json.dumps(printable, indent=1))
    if args.near_miss:
        print("\n  falsos positivos com filtro de %d bits (ate 200 listados):" % args.near_miss)
        for t, v in out["near_miss"][:200]:
            print("    candidato=%-12d bits_baixos_da_ancora=0x%x" % (t, v))
    if out["hits"]:
        print("\n  *** ACERTO *** verificar imediatamente:")
        print(json.dumps(out["hits_detail"], indent=1))
    if args.output:
        with open(args.output, "w") as f:
            json.dump(out, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
