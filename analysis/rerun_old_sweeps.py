#!/usr/bin/env python3
"""Refaz, no lugar, as varreduras feitas no modelo de carteira unica.

Ate 2026-10-18 o master_seed_sweep descartava em silencio um candidato que
acertava a ancora #130 (129 bits, conclusivo) mas falhava em alguma das outras
81 chaves. Se as primeiras chaves foram feitas a mao, ou se ha lotes/geradores
intercalados, a seed verdadeira teria sido jogada fora. JSONs sem o campo
"anchor_only" vieram desse codigo; este script os refaz com os mesmos
parametros e substitui o arquivo so quando a nova execucao termina.

    python3 analysis/rerun_old_sweeps.py            # lista o que seria refeito
    python3 analysis/rerun_old_sweeps.py --run --jobs 8
"""
import argparse, glob, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
SKIP = {"nearmiss-hashseq-20bit.json"}  # calibracao de falso positivo, nao cobertura


def family_args(d):
    fam = d["family"]
    kind, _, rest = fam.partition(":")
    if kind == "hashseq":
        h, enc = rest.split("/")
        return ["--family", "hashseq", "--hash", h, "--index-enc", enc]
    if kind == "hashchain":
        return ["--family", "hashchain", "--hash", rest]
    if kind == "bip32":
        return ["--family", "bip32", "--path", rest]
    if kind == "electrum1":
        return ["--family", "electrum1", "--branch", rest.replace("branch", "")]
    if kind == "armory135":
        return ["--family", "armory"] + (["--armory-root"] if rest == "root0" else [])
    raise ValueError("familia desconhecida: %s" % fam)


def index_args(d):
    name = d.get("index_map") or "consecutive(base=%s,stride=1)" % d.get("index_base", 0)
    kind, _, params = name.partition("(")
    kv = dict(p.split("=") for p in params.rstrip(")").split(","))
    return ["--index-map", kind, "--index-base=%s" % kv["base"], "--index-stride", kv["stride"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--jobs", type=int, default=8)
    args = ap.parse_args()
    todo = []
    for p in sorted(glob.glob(os.path.join(HERE, "sweeps", "*.json"))):
        d = json.load(open(p))
        if "candidates" not in d or "anchor_only" in d or os.path.basename(p) in SKIP:
            continue
        lo, hi = d["range"]
        cmd = [sys.executable, "-B", os.path.join(HERE, "master_seed_sweep.py"),
               "--jobs", str(args.jobs), "--encoder", d["encoder"],
               "--mask", d.get("mask", "low"), "--range", "%d-%d" % (lo, hi),
               "--output", p + ".rerun"] + family_args(d) + index_args(d)
        todo.append((p, d["candidates"], cmd))
    total = sum(c for _, c, _ in todo)
    print("%d varreduras antigas, %d candidatos" % (len(todo), total))
    for p, c, cmd in todo:
        print("  %-42s %14d" % (os.path.basename(p), c))
        if not args.run:
            continue
        print("### rerun %s" % " ".join(cmd[3:]), flush=True)
        r = subprocess.run(["nice", "-n", "19"] + cmd, cwd=ROOT)
        if r.returncode != 0 or not os.path.exists(p + ".rerun"):
            print("FALHOU %s (rc=%d); original mantido" % (p, r.returncode), flush=True)
            continue
        os.replace(p + ".rerun", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
