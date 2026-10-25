#!/usr/bin/env python3
"""MT19937 com semeadura/saida DIFERENTES do `random` do Python: numpy, PHP 5.x, Ruby.

O `random` do Python ja esta coberto (encoders mt256 e H11). Mas o mesmo MT19937 com
outra semeadura ou outro uso da saida da fluxos diferentes:

  numpy  np.random.seed(int)  -> init_genrand(seed)  (nao init_by_array como o Python)
         bytes(32): 4 bytes por palavra, little-endian;  randint(0,256): 1 palavra & 0xFF;
         randint(0,2^32): 1 palavra
  php    mt_srand(seed), PHP 5.x-7.0: init_genrand + twist COM BUG (loBit(u) em vez de
         loBit(v)); mt_rand() = tempered >> 1 (31 bits); mt_rand(0,255) = n >> 23;
         mt_rand(0,15) = n >> 27
  ruby   Random.new(seed): init_genrand(seed) se seed < 2^32 (rand_init), senao init_by_array; bytes(32): 4 bytes/palavra LE;
         rand(256): palavra & 0xFF; rand(2^32): 1 palavra

Chave do puzzle n = unidades consecutivas do fluxo (bytes, nibbles ou palavras),
em dois recortes (32 bytes por chave e "so o necessario para n bits"), montadas em
big ou little-endian, com mascara low ou high. Rejeicao no primeiro puzzle resolvido
que nao bate; reproduzir todos ate #130 e conclusivo.

    python3 analysis/mt_variants_sweep.py --self-test
    python3 analysis/mt_variants_sweep.py --range 1418753234-1423937234 --jobs 8 --output ...
"""
import argparse
import json
import multiprocessing as mp
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from master_seed_sweep import load_solved  # noqa: E402

N_MT, M_MT = 624, 397
MASK32 = 0xFFFFFFFF


def init_genrand(seed):
    st = [seed & MASK32]
    for i in range(1, N_MT):
        p = st[-1]
        st.append((1812433253 * (p ^ (p >> 30)) + i) & MASK32)
    return st


def init_by_array(key):
    st = init_genrand(19650218)
    i, j = 1, 0
    for _ in range(max(N_MT, len(key))):
        st[i] = ((st[i] ^ ((st[i - 1] ^ (st[i - 1] >> 30)) * 1664525)) + key[j] + j) & MASK32
        i += 1
        j += 1
        if i >= N_MT:
            st[0] = st[N_MT - 1]
            i = 1
        if j >= len(key):
            j = 0
    for _ in range(N_MT - 1):
        st[i] = ((st[i] ^ ((st[i - 1] ^ (st[i - 1] >> 30)) * 1566083941)) - i) & MASK32
        i += 1
        if i >= N_MT:
            st[0] = st[N_MT - 1]
            i = 1
    st[0] = 0x80000000
    return st


def temper(y):
    y ^= y >> 11
    y ^= (y << 7) & 0x9D2C5680
    y ^= (y << 15) & 0xEFC60000
    y ^= y >> 18
    return y & MASK32


def php_reload(st):
    """Twist do PHP 5.x: usa loBit(u) (bug); o MT padrao usa loBit(v)."""
    out = st[:]
    def twist(m, u, v):
        return m ^ (((u & 0x80000000) | (v & 0x7FFFFFFF)) >> 1) ^ ((-(u & 1)) & 0x9908B0DF) & MASK32
    for i in range(N_MT - M_MT):
        out[i] = twist(out[i + M_MT], out[i], out[i + 1])
    for i in range(N_MT - M_MT, N_MT - 1):
        out[i] = twist(out[i + M_MT - N_MT], out[i], out[i + 1])
    out[N_MT - 1] = twist(out[M_MT - 1], out[N_MT - 1], out[0])
    return out


class Stream:
    """Fluxo preguicoso de palavras de 32 bits (ja temperadas)."""

    def __init__(self, gen, seed):
        self.gen = gen
        self.words = []
        if gen == "php":
            self.state = php_reload(init_genrand(seed))
            self.pos = 0
        else:
            if gen == "numpy" or (gen == "ruby" and seed < (1 << 32)):
                st = init_genrand(seed)   # Ruby rand_init: seed de 1 palavra -> init_genrand
            else:
                st = init_by_array([seed & MASK32, seed >> 32])
            self.rng = random.Random()
            self.rng.setstate((3, tuple(st) + (N_MT,), None))

    def word(self, i):
        while len(self.words) <= i:
            if self.gen == "php":
                if self.pos >= N_MT:
                    self.state = php_reload(self.state)
                    self.pos = 0
                self.words.append(temper(self.state[self.pos]) >> 1)
                self.pos += 1
            else:
                self.words.append(self.rng.getrandbits(32))
        return self.words[i]


# unidade -> (bits, funcao(stream, k) -> valor da k-esima unidade)
def unit_funcs(gen):
    if gen == "php":
        return {"byte": (8, lambda s, k: s.word(k) >> 23),
                "nibble": (4, lambda s, k: s.word(k) >> 27),
                "word31": (31, lambda s, k: s.word(k))}
    # numpy / ruby: bytes() preenche 4 bytes por palavra em little-endian
    return {"bytes": (8, lambda s, k: (s.word(k // 4) >> (8 * (k % 4))) & 0xFF),
            "byte": (8, lambda s, k: s.word(k) & 0xFF),
            "word32": (32, lambda s, k: s.word(k))}


def key_from_units(vals, bits, order):
    v = 0
    seq = vals if order == "be" else vals[::-1]
    for u in seq:
        v = (v << bits) | u
    return v


def mask_val(n, v, total_bits, mask):
    if mask == "high":
        v = v >> max(0, total_bits - n)
    return (v & ((1 << (n - 1)) - 1)) | (1 << (n - 1))


def check(stream, ufn, bits, chunk, order, mask, wanted_sorted, upto=130):
    """Percorre os puzzles 1..upto em ordem consumindo unidades; rejeita cedo."""
    k = 0
    wi = 0
    for n in range(1, upto + 1):
        cnt = (256 + bits - 1) // bits if chunk == "s256" else max(1, (n - 1 + bits - 1) // bits)
        if wi < len(wanted_sorted) and wanted_sorted[wi][0] == n:
            vals = [ufn(stream, k + t) for t in range(cnt)]
            v = mask_val(n, key_from_units(vals, bits, order), cnt * bits, mask)
            if v != wanted_sorted[wi][1]:
                return False
            wi += 1
        k += cnt
        if wi >= len(wanted_sorted):
            return True
    return True


def combos(gen):
    out = []
    for uname, (bits, fn) in unit_funcs(gen).items():
        for chunk in ("s256", "fit"):
            for order in ("be", "le"):
                for mask in ("low", "high"):
                    if chunk == "fit" and mask == "high" and bits == 8:
                        pass
                    out.append((uname, bits, fn, chunk, order, mask))
    return out


GENS = ["numpy", "php", "ruby"]
_S = {}


def _init(wanted, gens):
    _S["wanted"] = wanted
    _S["gens"] = gens
    _S["combos"] = {g: combos(g) for g in gens}


def _work(rng_):
    lo, hi = rng_
    hits = []
    for t in range(lo, hi):
        for g in _S["gens"]:
            s = Stream(g, t)
            for (uname, bits, fn, chunk, order, mask) in _S["combos"][g]:
                if check(s, fn, bits, chunk, order, mask, _S["wanted"]):
                    hits.append({"seed": t, "gen": g, "unit": uname, "chunk": chunk, "order": order, "mask": mask})
    return hi - lo, hits


def synth(gen, seed, uname, chunk, order, mask, puzzles, upto=130):
    bits, fn = unit_funcs(gen)[uname]
    s = Stream(gen, seed)
    out = {}
    k = 0
    for n in range(1, upto + 1):
        cnt = (256 + bits - 1) // bits if chunk == "s256" else max(1, (n - 1 + bits - 1) // bits)
        vals = [fn(s, k + t) for t in range(cnt)]
        if n in puzzles:
            out[n] = mask_val(n, key_from_units(vals, bits, order), cnt * bits, mask)
        k += cnt
    return out


def self_test():
    import subprocess
    ok = True
    # vetores do MT19937: init_genrand(5489) -> 3499211612 ; init_by_array({0x123,0x234,0x345,0x456}) -> 1067595299
    r = random.Random(); r.setstate((3, tuple(init_genrand(5489)) + (N_MT,), None)); v1 = r.getrandbits(32)
    r = random.Random(); r.setstate((3, tuple(init_by_array([0x123, 0x234, 0x345, 0x456])) + (N_MT,), None)); v2 = r.getrandbits(32)
    print("  MT init_genrand(5489) -> %d (esperado 3499211612)  init_by_array -> %d (esperado 1067595299)" % (v1, v2))
    ok &= v1 == 3499211612 and v2 == 1067595299
    # PHP 5.x (modo MT_RAND_PHP no 7.1+): mt_srand(1); mt_rand() == 1244335972; o corrigido da 895547922
    s = Stream("php", 1); p1 = s.word(0)
    print("  PHP5 mt_srand(1); mt_rand() -> %d (esperado 1244335972; PHP>=7.1 corrigido da 895547922)" % p1)
    ok &= p1 == 1244335972
    try:
        php = subprocess.run(["php", "-d", "display_errors=0", "-r", "mt_srand(7, MT_RAND_PHP); $a=[]; for($i=0;$i<6;$i++){$a[]=mt_rand();} "
                              "mt_srand(7, MT_RAND_PHP); $b=[]; for($i=0;$i<6;$i++){$b[]=mt_rand(0,255);} echo json_encode([$a,$b]);"],
                             capture_output=True, text=True, timeout=20).stdout
        a, b = json.loads(php)
        s = Stream("php", 7)
        mine = [s.word(i) for i in range(6)]
        mineb = [s.word(i) >> 23 for i in range(6)]
        print("  PHP (binario local, modo MT_RAND_PHP) seed 7: palavras %s bytes %s" % (mine == a, mineb == b))
        ok &= mine == a and mineb == b
    except Exception as e:
        print("  PHP local indisponivel (%s); so o vetor documentado foi conferido" % e)
    try:
        rb = subprocess.run(["ruby", "-e", 'r=Random.new(12345); puts r.bytes(12).unpack("H*")[0]; r=Random.new(12345); puts (0...6).map{r.rand(256)}.join(","); r=Random.new(12345); puts (0...3).map{r.rand(2**32)}.join(",")'],
                            capture_output=True, text=True, timeout=20).stdout.split()
        s = Stream("ruby", 12345)
        uf = unit_funcs("ruby")
        myb = bytes(uf["bytes"][1](s, k) for k in range(12)).hex()
        my256 = ",".join(str(uf["byte"][1](s, k)) for k in range(6))
        myw = ",".join(str(uf["word32"][1](s, k)) for k in range(3))
        print("  Ruby local seed 12345: bytes %s rand(256) %s rand(2^32) %s" % (myb == rb[0], my256 == rb[1], myw == rb[2]))
        ok &= myb == rb[0] and my256 == rb[1] and myw == rb[2]
    except Exception as e:
        print("  Ruby local indisponivel (%s)" % e)
    # numpy: sem numpy local; init_genrand conferido pelo vetor 5489. bytes/randint seguem o legado (rk_random & mask).
    solved = load_solved()
    puzzles = sorted(n for n in solved if n <= 130)
    for gen in GENS:
        for (uname, bits, fn, chunk, order, mask) in combos(gen):
            seed = 777000 + (hash((gen, uname, chunk, order, mask)) & 0xFFF)
            w = synth(gen, seed, uname, chunk, order, mask, set(puzzles))
            ws = sorted(w.items())
            got = check(Stream(gen, seed), fn, bits, chunk, order, mask, ws)
            bad = dict(w); bad[130] ^= 1 << 33
            gotb = check(Stream(gen, seed), fn, bits, chunk, order, mask, sorted(bad.items()))
            ok &= got and not gotb
            if not (got and not gotb):
                print("  FALHA", gen, uname, chunk, order, mask, got, gotb)
    print("  controles plantados: %d combinacoes x (recuperacao + adulterado)" % sum(len(combos(g)) for g in GENS))
    print("\n  todos os controles passaram: %s" % ok)
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--range")
    ap.add_argument("--gens", default=",".join(GENS))
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--chunk", type=int, default=2000)
    ap.add_argument("--output")
    args = ap.parse_args()
    if args.self_test:
        sys.exit(0 if self_test() else 1)
    solved = load_solved()
    wanted = sorted((n, k) for n, k in solved.items() if n <= 130)
    gens = args.gens.split(",")
    lo, hi = (int(x, 0) for x in args.range.split("-"))
    total = hi - lo
    ncomb = sum(len(combos(g)) for g in gens)
    print("mt_variants_sweep gens=%s range=%d-%d combos=%d jobs=%d" % (gens, lo, hi, ncomb, args.jobs), flush=True)
    t0 = time.time(); done = 0; hits = []; last = 0
    with mp.Pool(args.jobs, initializer=_init, initargs=(wanted, gens)) as pool:
        for n, h in pool.imap_unordered(_work, ((a, min(a + args.chunk, hi)) for a in range(lo, hi, args.chunk))):
            done += n; hits += h
            if time.time() - last > 15:
                last = time.time()
                print("  %5.1f%%  %d/%d  %.0f cand/s  hits=%d" % (100.0 * done / total, done, total, done / (time.time() - t0), len(hits)), flush=True)
    el = time.time() - t0
    print("FIM candidatos=%d combos=%d hits=%d %.0fs" % (total, ncomb, len(hits), el))
    if hits:
        print("ACERTO(S): veja o JSON; nao cole seeds em logs/commits (BRIEFING secao 5).")
    if args.output:
        json.dump({"family": "mtvariants:" + "+".join(gens), "encoder": "int", "mask": "low|high", "index_map": "stream(s256|fit;be|le)",
                   "index_base": 0, "range": [lo, hi], "candidates": total, "candidates_x_combos": total * ncomb,
                   "elapsed_s": round(el, 1), "rate_per_s": round(total / el, 1), "hits": hits, "anchor_only": [], "hits_detail": hits},
                  open(args.output, "w"), indent=1)


if __name__ == "__main__":
    main()
