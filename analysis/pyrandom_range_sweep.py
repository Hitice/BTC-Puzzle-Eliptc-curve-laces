#!/usr/bin/env python3
"""H11: PRNG do Python sorteando cada chave DIRETAMENTE na faixa do puzzle.

Modelo: o criador escreveu um script, semeou `random` e, para n = 1..256,
sorteou key_n dentro de [2^(n-1), 2^n). Nao e "carteira deterministica" no
sentido HD, mas e o que um programador faz para "fazer caber em cada faixa";
ideia do usuario (moedas por faixa), formalizada aqui com PRNG enumeravel.

Sem mascara: a chave sorteada ja esta na faixa. A informacao esta na ORDEM dos
sorteios: cada candidato (seed, variante) reproduz a sequencia inteira e e
rejeitado no primeiro puzzle resolvido que nao bate (#2 ja da 1 bit, #5 da 4...).
Um candidato que reproduz todos os resolvidos ate #130 e conclusivo.

Variantes de sorteio (bits consumidos do MT19937 diferem entre elas):
  py3-randrange   randrange(2^(n-1), 2^n) do Python >= 3.2: getrandbits(n) com rejeicao
  py2-randrange   randrange do Python 2.7 / <= 3.1: random()*width se width < 2^53,
                  senao getrandbits(k) com k = int(1.00001 + log2(width-1))
  grb-n-or        getrandbits(n) | 2^(n-1)
  grb-n1-or       getrandbits(n-1) | 2^(n-1)   (n = 1 nao consome nada)
  stream256       child_i = getrandbits(256), i = 0..; puzzle_n = mascara low do child_{n-1}
  stream-rr256    child_i = randrange(2^256) (getrandbits(257) com rejeicao), mascara low
  stream-randintN  child_i = randint(1, N-1) = 1 + getrandbits(256) com rejeicao, mascara low
Ordem: ascendente 1..256 (padrao) ou descendente 256..1; inicio em #1 ou em #5
(#1-#4 feitas a mao).

Seeds:
  --seed-kind int      random.seed(t), t inteiro (inclui timestamps em s e ms)
  --seed-kind py3str   random.seed(frase) do Python 3: int(frase + sha512(frase))
  --seed-kind py2str   random.seed(frase) do Python 2.7 (64 bits): hash(str) como unsigned

Controle positivo obrigatorio (BRIEFING secao 3): --self-test planta seeds
conhecidas em cada variante, exige recuperacao e exige rejeicao de conjunto
adulterado.

    python3 analysis/pyrandom_range_sweep.py --self-test
    python3 analysis/pyrandom_range_sweep.py --seed-kind int --range 1356998400-1421345235 --jobs 8 \
        --output analysis/sweeps/h11-pyrandom-int-time.json
"""
import argparse
import hashlib
import json
import math
import multiprocessing as mp
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from master_seed_sweep import load_solved, mask_low  # noqa: E402

N_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
MAXWIDTH = 1 << 53

VARIANTS = ["py3-randrange", "py2-randrange", "grb-n-or", "grb-n1-or",
            "stream256", "stream-rr256", "stream-randintN"]
ORDERS = ["asc", "desc"]
STARTS = [1, 5]


# --------------------------------------------------------------------------
# semeadura
# --------------------------------------------------------------------------
def py2_str_hash(s):
    """hash() de str no CPython 2.7 de 64 bits (sem -R), como unsigned."""
    b = s.encode("utf-8")
    if not b:
        return 0
    M = (1 << 64) - 1
    x = (b[0] << 7) & M
    for c in b:
        x = ((1000003 * x) & M) ^ c
    x ^= len(b)
    # interpretado como long com sinal; -1 vira -2
    if x == M:
        x = M - 1
    return x  # (unsigned long) hash


def make_rng(kind, value):
    if kind == "int":
        return random.Random(value)
    if kind == "py3str":
        return random.Random(value)  # str -> version 2: int(a + sha512(a))
    if kind == "py2str":
        return random.Random(py2_str_hash(value))
    raise ValueError(kind)


# --------------------------------------------------------------------------
# sorteio por faixa
# --------------------------------------------------------------------------
def draw_py3_randrange(rng, n):
    # randrange(2^(n-1), 2^n): width = 2^(n-1); _randbelow(width): k = width.bit_length() = n
    width = 1 << (n - 1)
    r = rng.getrandbits(n)
    while r >= width:
        r = rng.getrandbits(n)
    return width + r


def draw_py2_randrange(rng, n):
    width = 1 << (n - 1)
    if width < MAXWIDTH:
        return width + int(rng.random() * width)
    k = int(1.00001 + math.log(width - 1, 2.0))
    r = rng.getrandbits(k)
    while r >= width:
        r = rng.getrandbits(k)
    return width + r


def draw_grb_n_or(rng, n):
    return rng.getrandbits(n) | (1 << (n - 1))


def draw_grb_n1_or(rng, n):
    if n == 1:
        return 1
    return rng.getrandbits(n - 1) | (1 << (n - 1))


def stream_grb256(rng):
    return rng.getrandbits(256)


def stream_rr256(rng):
    r = rng.getrandbits(257)
    while r >= (1 << 256):
        r = rng.getrandbits(257)
    return r


def stream_randintN(rng):
    # randint(1, N-1) = 1 + randbelow(N-1); (N-1).bit_length() = 256
    r = rng.getrandbits(256)
    while r >= N_ORDER - 1:
        r = rng.getrandbits(256)
    return 1 + r


DRAWERS = {"py3-randrange": draw_py3_randrange, "py2-randrange": draw_py2_randrange,
           "grb-n-or": draw_grb_n_or, "grb-n1-or": draw_grb_n1_or}
STREAMS = {"stream256": stream_grb256, "stream-rr256": stream_rr256,
           "stream-randintN": stream_randintN}


def generate(rng, variant, order, start, upto):
    """Gera {n: key} para n de start..upto na ordem dada (sequencia completa)."""
    ns = list(range(start, 257))
    if order == "desc":
        ns = ns[::-1]
    out = {}
    if variant in DRAWERS:
        d = DRAWERS[variant]
        for n in ns:
            out[n] = d(rng, n)
    else:
        s = STREAMS[variant]
        for n in ns:
            out[n] = mask_low(n, s(rng))
    return {n: k for n, k in out.items() if n <= upto}


def check(rng, variant, order, start, wanted_sorted):
    """Reproduz a sequencia e compara com as chaves conhecidas; rejeita cedo.

    wanted_sorted: lista de (n, key) na ORDEM em que sao geradas.
    Devolve True se todas batem.
    """
    if variant in DRAWERS:
        d = DRAWERS[variant]
        if order == "asc":
            n = start
            for wn, wk in wanted_sorted:
                while n < wn:
                    d(rng, n)
                    n += 1
                if d(rng, n) != wk:
                    return False
                n += 1
            return True
        n = 256
        for wn, wk in wanted_sorted:
            while n > wn:
                d(rng, n)
                n -= 1
            if d(rng, n) != wk:
                return False
            n -= 1
        return True
    s = STREAMS[variant]
    if order == "asc":
        n = start
        for wn, wk in wanted_sorted:
            while n < wn:
                s(rng)
                n += 1
            if mask_low(n, s(rng)) != wk:
                return False
            n += 1
        return True
    n = 256
    for wn, wk in wanted_sorted:
        while n > wn:
            s(rng)
            n -= 1
        if mask_low(n, s(rng)) != wk:
            return False
        n -= 1
    return True


# --------------------------------------------------------------------------
# varredura
# --------------------------------------------------------------------------
_STATE = {}


def _init(kind, combos, wanted_by_combo):
    _STATE["kind"] = kind
    _STATE["combos"] = combos
    _STATE["wanted"] = wanted_by_combo


def _work_ints(chunk):
    lo, hi = chunk
    kind = _STATE["kind"]
    hits = []
    for t in range(lo, hi):
        for (variant, order, start) in _STATE["combos"]:
            rng = random.Random(t)
            if check(rng, variant, order, start, _STATE["wanted"][(order, start)]):
                hits.append({"seed": t, "variant": variant, "order": order, "start": start})
    return hi - lo, hits


def _work_phrases(phrases):
    kind = _STATE["kind"]
    hits = []
    for p in phrases:
        for (variant, order, start) in _STATE["combos"]:
            rng = make_rng(kind, p)
            if check(rng, variant, order, start, _STATE["wanted"][(order, start)]):
                hits.append({"seed": p, "variant": variant, "order": order, "start": start})
    return len(phrases), hits


def wanted_lists(solved, upto=130):
    out = {}
    for order in ORDERS:
        for start in STARTS:
            items = [(n, k) for n, k in solved.items() if start <= n <= upto]
            items.sort(key=lambda x: x[0], reverse=(order == "desc"))
            out[(order, start)] = items
    return out


def self_test(jobs):
    solved = load_solved()
    ok_all = True
    rate_seen = []
    for variant in VARIANTS:
        for order in ORDERS:
            for start in STARTS:
                seed = 90000 + (sum(map(ord, variant + order)) * 31 + start) % 5000
                rng = random.Random(seed)
                synth = generate(rng, variant, order, start, 256)
                # usa so os puzzles que estao resolvidos no conjunto real (mesma visibilidade)
                wanted = {n: synth[n] for n in solved if n >= start}
                wl = {(order, start): sorted(wanted.items(), key=lambda x: x[0], reverse=(order == "desc"))}
                _init("int", [(variant, order, start)], wl)
                t0 = time.time()
                n, hits = _work_ints((seed - 20000, seed + 20000))
                dt = time.time() - t0
                rate_seen.append(n / dt)
                rec = [h for h in hits if h["seed"] == seed]
                bad = dict(wanted)
                top = max(bad)
                bad[top] ^= 1 << (top // 2)
                wl2 = {(order, start): sorted(bad.items(), key=lambda x: x[0], reverse=(order == "desc"))}
                _init("int", [(variant, order, start)], wl2)
                n2, hits2 = _work_ints((seed - 20000, seed + 20000))
                rej = not any(h["seed"] == seed for h in hits2)
                good = bool(rec) and rej and len(hits) == 1
                ok_all &= good
                print("  %-16s %-4s start=%d  rec=%s  adult_rej=%s  falsos=%d  %7.0f c/s" % (
                    variant, order, start, bool(rec), rej, len(hits) - len(rec), n / dt))
    # py2str e py3str: semeadura
    r3 = make_rng("py3str", "saatoshi")
    assert r3.getrandbits(32) == random.Random("saatoshi").getrandbits(32)
    # vetor conhecido do hash de str no CPython 2.7 de 64 bits: hash("abc") == 1453079729188098211
    assert py2_str_hash("abc") == 1453079729188098211, py2_str_hash("abc")
    # hash("") == 0; hash("a") == 12416037344
    assert py2_str_hash("") == 0 and py2_str_hash("a") == 12416037344
    print("  py2_str_hash: vetores de CPython 2.7 (64 bits) ok")
    print("\n  todos os controles passaram: %s   (taxa media por variante: %.0f c/s, 1 processo)" % (
        ok_all, sum(rate_seen) / len(rate_seen)))
    return ok_all


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--seed-kind", default="int", choices=["int", "py3str", "py2str"])
    ap.add_argument("--range", help="LO-HI para seed-kind int")
    ap.add_argument("--phrase-file", help="uma frase por linha (py3str/py2str)")
    ap.add_argument("--dict", action="store_true", help="dicionario do sistema + tematico (phrase_seed_sweep)")
    ap.add_argument("--variants", default=",".join(VARIANTS))
    ap.add_argument("--orders", default=",".join(ORDERS))
    ap.add_argument("--starts", default="1,5")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--chunk", type=int, default=20000)
    ap.add_argument("--output")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(0 if self_test(args.jobs) else 1)

    solved = load_solved()
    wl = wanted_lists(solved)
    variants = args.variants.split(",")
    orders = args.orders.split(",")
    starts = [int(s) for s in args.starts.split(",")]
    combos = [(v, o, s) for v in variants for o in orders for s in starts]
    for v in variants:
        assert v in VARIANTS, v

    t0 = time.time()
    done = 0
    hits = []
    if args.seed_kind == "int":
        lo, hi = (int(x, 0) for x in args.range.split("-"))
        total = hi - lo
        chunks = ((a, min(a + args.chunk, hi)) for a in range(lo, hi, args.chunk))
        worker = _work_ints
        label = "range=%d-%d" % (lo, hi)
    else:
        if args.phrase_file:
            phrases = [l.rstrip("\n") for l in open(args.phrase_file, encoding="utf-8", errors="replace") if l.strip()]
        elif args.dict:
            from phrase_seed_sweep import phrases_dict, phrases_theme
            phrases = list(phrases_dict()) + list(phrases_theme())
        else:
            ap.error("py3str/py2str exigem --phrase-file ou --dict")
        total = len(phrases)
        chunks = (phrases[i:i + 2000] for i in range(0, total, 2000))
        worker = _work_phrases
        label = "phrases=%d" % total
    print("pyrandom_range_sweep seed-kind=%s %s variantes=%d ordens=%s inicios=%s combos=%d jobs=%d" % (
        args.seed_kind, label, len(variants), orders, starts, len(combos), args.jobs), flush=True)
    with mp.Pool(args.jobs, initializer=_init, initargs=(args.seed_kind, combos, wl)) as pool:
        last = 0
        for n, h in pool.imap_unordered(worker, chunks):
            done += n
            hits += h
            if time.time() - last > 15:
                last = time.time()
                print("  %5.1f%%  %d/%d  %.0f cand/s  hits=%d" % (100.0 * done / total, done, total,
                                                                   done / (time.time() - t0), len(hits)), flush=True)
    el = time.time() - t0
    res = {"family": "pyrandom:" + "+".join(variants), "encoder": args.seed_kind, "mask": "range-direct",
           "index_map": "orders=%s;starts=%s" % ("/".join(orders), "/".join(map(str, starts))),
           "index_base": 0, "range": [lo, hi] if args.seed_kind == "int" else None,
           "candidates": total, "candidates_x_combos": total * len(combos),
           "anchor_puzzle": "all solved <= 130 (sequential)", "anchor_bits": sum(n - 1 for n in solved if n <= 130),
           "confirm_puzzles": len(solved), "elapsed_s": round(el, 1), "rate_per_s": round(total / el, 1),
           "hits": hits, "anchor_only": [], "hits_detail": hits}
    print("FIM candidatos=%d combos=%d hits=%d %.0fs" % (total, len(combos), len(hits), el))
    if hits:
        print("ACERTO(S): veja o JSON; nao cole seeds em logs/commits (BRIEFING secao 5).")
    if args.output:
        with open(args.output, "w") as f:
            json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
