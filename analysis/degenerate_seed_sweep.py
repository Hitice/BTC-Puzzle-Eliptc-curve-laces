#!/usr/bin/env python3
"""Seeds DEGENERADAS em todas as familias: a falha "achavel em segundos" numero 1.

Uma pessoa montando um experimento que trata como brincadeira usa seed trivial:
bytes todos iguais, padroes repetidos (deadbeef...), sequencias (00 01 02...),
strings hex em ASCII ("000...0001"), senhas classicas, inteiros pequenos em varias
larguras e endianness. Nenhuma varredura anterior cobre isso de forma sistematica:
os sweeps de inteiros usam UM encoder por vez e as frases vem de dicionario.

Para cada (familia, seed): ancora #130 com offsets de indice -4..+4 e 3 mascaras;
familias sequenciais/caras (armory, hashchain, electrum1) sao checadas em ordem
ascendente com rejeicao no primeiro puzzle resolvido que nao bate.

    python3 analysis/degenerate_seed_sweep.py --self-test
    python3 analysis/degenerate_seed_sweep.py --jobs 8 --output analysis/sweeps/degenerate-seeds.json
"""
import argparse
import hashlib
import json
import multiprocessing as mp
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from master_seed_sweep import (MASKS, Armory, Bip32, ElectrumV1, HashChain, HashSeq,  # noqa: E402
                               load_solved, synthetic_keys)

OFFSETS = list(range(-4, 5))
LENGTHS = [1, 2, 4, 8, 16, 20, 32, 64]
WORDS = ["", "0", "1", "a", "b", "x", "test", "seed", "secret", "password", "Password", "password1",
         "bitcoin", "Bitcoin", "satoshi", "Satoshi", "puzzle", "Puzzle", "admin", "qwerty", "abc", "abc123",
         "letmein", "111111", "000000", "123456", "1234567", "12345678", "123456789", "1234567890",
         "iloveyou", "dragon", "monkey", "master", "hello", "hello world", "Hello World", "foo", "bar",
         "foobar", "asdf", "asdfgh", "asdfghjkl", "qwertyuiop", "zxcvbnm", "aaaaaa", "changeme", "default",
         "welcome", "root", "toor", "god", "love", "money", "trustno1", "xxx", "key", "private", "privkey",
         "wallet", "deterministic", "deterministic wallet", "brainwallet", "brain wallet", "challenge",
         "treasure", "hunt", "lol", "none", "null", "nil", "void", "dummy", "example", "sample", "demo",
         "correct horse battery staple", "the quick brown fox", "lorem ipsum", "to be or not to be",
         "saatoshi_rising", "saatoshi", "rising", "0000000000000000000000000000000000000000000000000000000000000001",
         "00000000000000000000000000000001", "1" * 32, "1" * 64, "0" * 32, "0" * 64, "a" * 32, "a" * 64,
         "f" * 32, "f" * 64, "0123456789abcdef", "0123456789abcdef" * 2, "0123456789abcdef" * 4,
         "deadbeef", "deadbeef" * 4, "deadbeef" * 8, "cafebabe" * 8, "0123456789", "abcdefghijklmnopqrstuvwxyz",
         "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "0123456789ABCDEF" * 4]
PATTERNS = [b"\x00\x01", b"\x01\x02", b"\x00\xff", b"\xff\x00", b"\x01\x23", b"\x12\x34", b"\xab\xcd",
            b"\xde\xad", b"\xbe\xef", b"\xca\xfe", b"\xba\xbe", b"\xde\xad\xbe\xef", b"\xca\xfe\xba\xbe",
            b"\x01\x23\x45\x67", b"\x89\xab\xcd\xef", b"\x01\x23\x45\x67\x89\xab\xcd\xef", b"\x00\x00\x00\x01",
            b"\x80\x00\x00\x00", b"\x7f\xff\xff\xff", b"\xff\xff\xff\xfe", b"\x55\xaa", b"\xaa\x55",
            b"\x0f\xf0", b"\xf0\x0f", b"\x12\x34\x56\x78", b"\x87\x65\x43\x21", b"\x11\x22\x33\x44"]
NUMBERS = list(range(0, 1024)) + [2015, 2014, 2013, 1337, 31337, 4096, 65535, 65536, 32896, 256, 255,
                                   20150115, 15012015, 1421345234, 339085, 1000000, 999999, 123456789,
                                   987654321, 1234567890, 3141592653, 2718281828, 4294967295, 4294967296,
                                   2147483647, 2147483648, 1 << 32, 1 << 63, (1 << 64) - 1]


def seeds():
    out = set()
    for L in LENGTHS:
        for b in range(256):
            out.add(bytes([b]) * L)
        out.add(bytes(range(L)) if L <= 256 else b"")
        out.add(bytes(range(1, L + 1)))
        out.add(bytes(range(L, 0, -1)))
        out.add(bytes(range(255, 255 - L, -1)))
        for p in PATTERNS:
            out.add((p * (L // len(p) + 1))[:L])
    for w in WORDS:
        out.add(w.encode())
        out.add((w + "\n").encode())
    for n in NUMBERS:
        for L in (1, 2, 4, 8, 16, 32):
            if n < (1 << (8 * L)):
                out.add(n.to_bytes(L, "big"))
                out.add(n.to_bytes(L, "little"))
        out.add(str(n).encode())
        out.add(("%x" % n).encode())
        out.add(("%064x" % n).encode())
        out.add(("%032x" % n).encode() if n < (1 << 128) else b"")
    out.discard(None)
    return sorted(out, key=lambda b: (len(b), b))


def families():
    fams = [HashSeq("sha256", "be4"), HashSeq("sha256", "str"), HashSeq("sha256d", "be4"), HashSeq("sha256", "le4"),
            HashChain("sha256"), HashChain("sha256d"),
            Bip32("m/i"), Bip32("m/ih"), Bip32("m/0/i"), Bip32("m/0h/i"), Bip32("m/0h/0/i"), Bip32("m/44h/0h/0h/0/i"),
            ElectrumV1(0), ElectrumV1(1), Armory(), Armory(root_first=True)]
    return {f.name: f for f in fams}


def fam_seed(fam, seed):
    """Adapta a seed a familia: Armory exige 32 bytes (usa sha256 da seed quando nao tem)."""
    if fam.name.startswith("armory"):
        return seed if len(seed) == 32 else hashlib.sha256(seed).digest()
    return seed


def check_one(fam, seed, solved, anchor=130):
    """Devolve lista de (offset, mask) que reproduzem #130 (e, para sequenciais, todos ate #130)."""
    hits = []
    try:
        ctx = fam.prepare(fam_seed(fam, seed))
    except Exception:
        return hits
    if ctx is None:
        return hits
    sequential = not getattr(fam, "random_access", True) or getattr(fam, "ascending_checks", False)
    for off in OFFSETS:
        for mname, mfn in MASKS.items():
            if sequential:
                ok = True
                for n in sorted(solved):
                    if n > anchor:
                        break
                    j = off + n - 1
                    if j < 0:
                        continue  # puzzle anterior ao inicio da carteira (feito a mao)
                    try:
                        c = fam.child(ctx, j)
                    except Exception:
                        ok = False
                        break
                    if mfn(n, c) != solved[n]:
                        ok = False
                        break
                if ok:
                    hits.append((off, mname))
            else:
                j = off + anchor - 1
                if j < 0:
                    continue
                try:
                    c = fam.child(ctx, j)
                except Exception:
                    continue
                if mfn(anchor, c) == solved[anchor]:
                    hits.append((off, mname))
    return hits


_S = {}


def _init(solved):
    _S["solved"] = solved
    _S["fams"] = families()


def _work(task):
    fname, chunk = task
    fam = _S["fams"][fname]
    out = []
    for seed in chunk:
        h = check_one(fam, seed, _S["solved"])
        if h:
            out.append({"family": fname, "seed_hex": seed.hex(), "matches": h})
    return fname, len(chunk), out


def self_test():
    solved = load_solved()
    puzzles = sorted(solved)
    fams = families()
    ok = True
    cases = [("bip32:m/i", b"\xaa" * 32, 2, "high"), ("hashseq:sha256/be4", b"deadbeef" * 4, -3, "low"),
             ("hashchain:sha256", b"\x00" * 16, 0, "low_le"), ("armory135", b"\x01\x02" * 16, 1, "low"),
             ("electrum1:branch0", b"password", 0, "low"), ("bip32:m/44h/0h/0h/0/i", b"1" * 32, -1, "low")]
    for fname, seed, off, mask in cases:
        fam = fams[fname]
        inside = [n for n in puzzles if off + n - 1 >= 0]
        synth = dict(solved)  # puzzles fora da carteira ficam com o valor real
        synth.update(synthetic_keys(fam, fam_seed(fam, seed), inside, off, mask))
        got = check_one(fam, seed, synth)
        bad = dict(synth)
        bad[130] ^= 1 << 40
        got_bad = check_one(fam, seed, bad)
        good = (off, mask) in got and (off, mask) not in got_bad
        ok &= good
        print("  %-24s off=%+d mask=%-6s rec=%s adult_rej=%s" % (fname, off, mask, (off, mask) in got, (off, mask) not in got_bad))
    print("\n  todos os controles passaram: %s" % ok)
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--output")
    args = ap.parse_args()
    if args.self_test:
        sys.exit(0 if self_test() else 1)
    solved = load_solved()
    S = seeds()
    fams = families()
    print("seeds degeneradas: %d  familias: %d  offsets: %d  mascaras: 3" % (len(S), len(fams), len(OFFSETS)), flush=True)
    tasks = []
    for fname in fams:
        step = 200 if not fname.startswith("electrum1") else 40
        for i in range(0, len(S), step):
            tasks.append((fname, S[i:i + step]))
    t0 = time.time()
    hits = []
    done = {}
    with mp.Pool(args.jobs, initializer=_init, initargs=(solved,)) as pool:
        for fname, n, out in pool.imap_unordered(_work, tasks):
            done[fname] = done.get(fname, 0) + n
            hits += out
            if done[fname] == len(S):
                print("  %-24s %6d seeds  hits=%d  %.0fs" % (fname, len(S), sum(1 for h in hits if h["family"] == fname), time.time() - t0), flush=True)
    el = time.time() - t0
    print("FIM seeds=%d familias=%d testes=%d hits=%d %.0fs" % (len(S), len(fams), len(S) * len(fams) * len(OFFSETS) * 3, len(hits), el))
    if hits:
        print("ACERTO(S): veja o JSON; nao cole seeds em logs/commits (BRIEFING secao 5).")
    if args.output:
        json.dump({"family": "degenerate:" + "+".join(fams), "encoder": "degenerate-seeds",
                   "mask": "low|high|low_le", "index_map": "consecutive(base=-4..4)", "index_base": 0,
                   "range": None, "candidates": len(S) * len(fams), "seeds": len(S), "families": list(fams),
                   "elapsed_s": round(el, 1), "rate_per_s": round(len(S) * len(fams) / el, 1),
                   "hits": hits, "anchor_only": [], "hits_detail": hits}, open(args.output, "w"), indent=1)


if __name__ == "__main__":
    main()
