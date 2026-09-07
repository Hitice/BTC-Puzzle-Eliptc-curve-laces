#!/usr/bin/env python3
"""Estado do workspace em um comando. Rode isto em vez de ler resultados em prosa.

Verifica a integridade dos dados, resume a cobertura ja varrida e lista as
hipoteses abertas. Alguns segundos, sem rede.
"""
import glob, hashlib, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import secp_fast as EC

B58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def b58check(b):
    b = b + hashlib.sha256(hashlib.sha256(b).digest()).digest()[:4]
    n = int.from_bytes(b, 'big')
    o = ''
    while n:
        n, r = divmod(n, 58)
        o = B58[r] + o
    return '1' * (len(b) - len(b.lstrip(b'\0'))) + o


def p2pkh(pubkey_bytes):
    h = hashlib.new('ripemd160', hashlib.sha256(pubkey_bytes).digest()).digest()
    return b58check(b'\x00' + h)


def sha256_file(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16]


def main():
    print("=" * 74)
    print("ESTADO DO WORKSPACE — Bitcoin Puzzle")
    print("=" * 74)

    try:
        commit = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                                         text=True).strip()
        dirty = subprocess.check_output(["git", "-C", ROOT, "status", "--porcelain"],
                                        text=True).strip().splitlines()
        print("\ngit: %s  (%d arquivos nao commitados)" % (commit, len(dirty)))
    except Exception as e:
        print("\ngit: indisponivel (%s)" % e)

    # --- dados ---
    print("\n[1] INTEGRIDADE DOS DADOS")
    pj = os.path.join(ROOT, "data", "puzzles.json")
    doc = json.load(open(pj))
    puz = doc["puzzles"]
    solved = [p for p in puz if p["status"] == "solved"]
    bad = []
    for p in solved:
        d = p["privkey_int"]
        n = p["puzzle"]
        if not ((1 << (n - 1)) <= d < (1 << n)):
            bad.append((n, "fora do intervalo"))
            continue
        ser = EC.ser_compressed(EC.mul_g(d))
        if p2pkh(ser) != p["address"]:
            bad.append((n, "endereco nao confere"))
        elif p.get("pubkey") and p["pubkey"] != ser.hex():
            bad.append((n, "pubkey nao confere"))
    print("   data/puzzles.json           sha=%s  %d puzzles, %d resolvidos"
          % (sha256_file(pj), len(puz), len(solved)))
    print("   chaves -> endereco          %d/%d conferem%s"
          % (len(solved) - len(bad), len(solved), "" if not bad else "  FALHAS: %s" % bad))
    print("   alvos com pubkey exposta    %s" % doc["meta"].get("unsolved_with_pubkey"))
    print("   ancora da varredura         puzzle #%d (%d bits conhecidos)"
          % (max(p["puzzle"] for p in solved), max(p["puzzle"] for p in solved) - 1))
    for name in ("puzzles_161_256.json", "creator_txs.json", "signatures.json"):
        f = os.path.join(ROOT, "data", name)
        if os.path.exists(f):
            print("   data/%-23s sha=%s  %d KB" % (name, sha256_file(f),
                                                   os.path.getsize(f) // 1024))

    # --- cobertura ---
    print("\n[2] COBERTURA DE VARREDURA DE SEED")
    rows = []
    for p in sorted(glob.glob(os.path.join(HERE, "sweeps", "*.json"))):
        d = json.load(open(p))
        if "candidates" in d:
            rows.append(d)
    if not rows:
        print("   nenhuma varredura registrada")
    tot = sum(r["candidates"] for r in rows)
    hits = sum(len(r.get("hits") or []) for r in rows)
    for r in rows:
        print("   %-26s %-9s base=%d  %13d cand  hits=%d"
              % (r.get("family"), r.get("encoder"), r.get("index_base", 0),
                 r["candidates"], len(r.get("hits") or [])))
    print("   TOTAL                                       %13d cand  hits=%d" % (tot, hits))

    log = os.path.join(HERE, "sweeps", "run.log")
    if os.path.exists(log):
        with open(log, "rb") as f:
            f.seek(max(0, os.path.getsize(log) - 4000))
            tail = f.read().decode("utf8", "replace").replace("\r", "\n").strip().splitlines()
        if tail:
            print("   fila (ultima linha): %s" % tail[-1].strip())

    # --- hipoteses ---
    print("\n[3] HIPOTESES")
    hp = os.path.join(ROOT, "HYPOTHESES.json")
    if not os.path.exists(hp):
        print("   HYPOTHESES.json ausente — rode python3 analysis/build_hypotheses.py")
    else:
        h = json.load(open(hp))
        print("   regra: %s" % h["rule"])
        for e in h["hypotheses"]:
            pc = e.get("positive_control", {})
            mark = "ok " if pc.get("executed") else ("-- " if pc.get("required") else "n/a")
            print("   [%s] %-18s %-22s %s" % (mark, e["id"], e["status"], e["title"][:34]))
        print("   'ok' = controle positivo executado; '--' = exigido e AUSENTE "
              "(resultado nao conta como negativo)")

    print("\n[4] PROXIMO PASSO")
    print("   Leia BRIEFING.md secao 9. Prioridade atual: H1 forense -> H2 mascara -> H3 seeds.")
    print("=" * 74)


if __name__ == "__main__":
    main()
