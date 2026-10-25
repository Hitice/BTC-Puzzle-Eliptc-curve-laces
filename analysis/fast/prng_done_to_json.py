#!/usr/bin/env python3
"""Converte as linhas DONE/HIT de analysis/sweeps/prng/*.txt em JSONs de cobertura (um por arquivo)
para o ledger (build_hypotheses.py le analysis/sweeps/*.json). Idempotente."""
import glob, json, os, re
HERE = os.path.dirname(os.path.abspath(__file__)); SW = os.path.join(HERE, "..", "sweeps")
GEN = {0: "glibc-rand", 1: "msvc-rand", 2: "bsd-rand-parkmiller", 3: "v8-mwc18030", 4: "lcg48-java-spidermonkey", 5: "mt19937-init_genrand(numpy/ruby)", 6: "php5-mt_rand"}
n = 0
for p in sorted(glob.glob(os.path.join(SW, "prng", "*.txt"))):
    txt = open(p).read()
    done = [l for l in txt.splitlines() if l.startswith("DONE")]
    if not done:
        continue
    hits = [l for l in txt.splitlines() if l.startswith("HIT")]
    d = dict(re.findall(r"(\w+)=(\S+)", done[-1]))
    gen = GEN.get(int(d["gen"]), d["gen"])
    rec = {"family": "prng-direct:" + gen, "encoder": "state-recovery" if "recover" in done[-1] else "int32-seed",
           "mask": "low|high", "index_map": "stream(s256|fit;be|le)", "index_base": 0,
           "range": [int(x) for x in d["range"].split("-")] if "range" in d else None,
           "candidates": int(d.get("candidates", d.get("states", 0))), "combos": int(d.get("combos", 1)),
           "layout": " ".join(k + "=" + v for k, v in d.items() if k in ("unit", "chunk", "order", "mask")),
           "elapsed_s": float(d.get("elapsed_s", 0)), "hits": hits, "anchor_only": [], "hits_detail": hits,
           "source_txt": os.path.relpath(p, os.path.join(HERE, "..", ".."))}
    out = os.path.join(SW, "prng-" + os.path.basename(p).replace(".txt", ".json"))
    json.dump(rec, open(out, "w"), indent=1); n += 1
print("prng JSONs:", n)
