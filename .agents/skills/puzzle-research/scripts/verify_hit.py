#!/usr/bin/env python3
"""Verificacao independente de um acerto do master_seed_sweep, sem vazar segredos.

Deriva as 256 chaves a partir de (familia, encoder, candidato, mascara, indice) e
confere contra TODO o dado publico: as 82 chaves resolvidas, os 160 enderecos de
data/puzzles.json (inclusive os nao resolvidos) e as 96 pubkeys de #161-#256.

Segredos (seed, chaves) vao SO para um arquivo 0600 fora do repositorio. O stdout
mostra apenas contagens e enderecos, que sao publicos. Assim nada sensivel entra
no transcript da conversa, em logs ou no git.

    python3 .claude/skills/puzzle-research/scripts/verify_hit.py --self-test
    python3 .claude/skills/puzzle-research/scripts/verify_hit.py \
        --family bip32 --path m/i --encoder bx2-minstd0 --candidate 123456
"""
import argparse, hashlib, json, os, random, sys, time

ROOT = os.getcwd()
sys.path.insert(0, os.path.join(ROOT, "analysis"))
try:
    import master_seed_sweep as S
    import secp_fast as EC
except ImportError:
    sys.exit("rode a partir da raiz do repositorio (analysis/master_seed_sweep.py nao encontrado)")

B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def p2pkh(pub):
    h = b"\x00" + hashlib.new("ripemd160", hashlib.sha256(pub).digest()).digest()
    b = h + hashlib.sha256(hashlib.sha256(h).digest()).digest()[:4]
    n, o = int.from_bytes(b, "big"), ""
    while n:
        n, r = divmod(n, 58)
        o = B58[r] + o
    return "1" * (len(b) - len(b.lstrip(b"\0"))) + o


def load_public():
    puz = json.load(open(os.path.join(ROOT, "data", "puzzles.json")))["puzzles"]
    solved = {p["puzzle"]: p["privkey_int"] for p in puz if p["status"] == "solved"}
    addresses = {p["puzzle"]: p["address"] for p in puz}
    hi = json.load(open(os.path.join(ROOT, "data", "puzzles_161_256.json")))["puzzles"]
    pubkeys = {p["puzzle"]: p["pubkey"] for p in hi}
    return solved, addresses, pubkeys


def compare(keys, solved, addresses, pubkeys):
    """Contagens de correspondencia; nao devolve nenhum segredo."""
    # Puzzles pequenos casam por acaso (#1 e sempre 1, #2 tem chance 1/2): a
    # contagem "nontrivial" (n >= 24, chance <= 2^-23 cada) e a que discrimina.
    r = {"solved_match": 0, "solved_total": len(solved),
         "address_match": 0, "address_total": len(addresses),
         "address_match_nontrivial": 0,
         "unsolved_address_match": [], "pubkey_match": 0, "pubkey_total": len(pubkeys)}
    for n, k in solved.items():
        r["solved_match"] += keys.get(n) == k
    for n, a in addresses.items():
        if n in keys and p2pkh(EC.ser_compressed(EC.mul_g(keys[n]))) == a:
            r["address_match"] += 1
            r["address_match_nontrivial"] += n >= 24
            if n not in solved:
                r["unsolved_address_match"].append(a)
    for n, pk in pubkeys.items():
        if n in keys:
            r["pubkey_match"] += EC.ser_compressed(EC.mul_g(keys[n])).hex() == pk
    r["full_match"] = (r["solved_match"] == r["solved_total"]
                       and r["address_match"] == r["address_total"]
                       and r["pubkey_match"] == r["pubkey_total"])
    return r


def derive(args, candidate):
    fam = S.build_family(args)
    imap = S.IndexMap(args.index_map, args.index_base, stride=args.index_stride)
    seed = S.ENCODERS[args.encoder](candidate)
    return seed, S.synthetic_keys(fam, seed, list(range(1, 257)), imap, args.mask)


def write_secret(path, payload):
    path = os.path.abspath(os.path.expanduser(path))
    if path.startswith(ROOT + os.sep):
        sys.exit("recusado: o arquivo de segredos nao pode ficar dentro do repositorio")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(payload, f, indent=1)
    return path


def self_test(args):
    """Controle positivo e negativo do proprio verificador, com dado sintetico."""
    args.family, args.path, args.encoder = "bip32", "m/0h/i", "raw4be"
    _, keys = derive(args, 424242)
    solved = {n: keys[n] for n in range(1, 70)}
    addresses = {n: p2pkh(EC.ser_compressed(EC.mul_g(keys[n]))) for n in range(1, 161)}
    pubkeys = {n: EC.ser_compressed(EC.mul_g(keys[n])).hex() for n in range(161, 257)}
    pos = compare(keys, solved, addresses, pubkeys)
    bad = dict(keys); bad[256] ^= 1
    neg_one_bit = compare(bad, solved, addresses, pubkeys)
    _, other = derive(args, 424243)
    neg_other = compare(other, solved, addresses, pubkeys)
    real = compare(keys, *load_public())
    checks = {"synthetic_full_match": pos["full_match"]
              and len(pos["unsolved_address_match"]) == 91,
              "one_bit_flip_rejected": not neg_one_bit["full_match"]
              and neg_one_bit["pubkey_match"] == 95,
              "neighbour_seed_rejected": neg_other["address_match_nontrivial"] == 0
              and neg_other["pubkey_match"] == 0,
              "synthetic_vs_real_data_no_match": real["address_match_nontrivial"] == 0
              and real["pubkey_match"] == 0}
    for k, v in checks.items():
        print("  %-34s %s" % (k, v))
    print("verificador ok: %s" % all(checks.values()))
    return 0 if all(checks.values()) else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--family", default="bip32", choices=["bip32", "hashseq", "hashchain", "electrum1", "armory"])
    ap.add_argument("--path", default="m/0/i")
    ap.add_argument("--hash", default="sha256")
    ap.add_argument("--index-enc", default="be4", choices=["be4", "le4", "str"])
    ap.add_argument("--branch", type=int, default=0)
    ap.add_argument("--armory-root", action="store_true")
    ap.add_argument("--encoder", default="mt256", choices=sorted(S.ENCODERS))
    ap.add_argument("--candidate", type=int)
    ap.add_argument("--mask", default="low", choices=sorted(S.MASKS))
    ap.add_argument("--index-map", default="consecutive", choices=["consecutive", "reverse", "rejection"])
    ap.add_argument("--index-base", type=int, default=0)
    ap.add_argument("--index-stride", type=int, default=1)
    ap.add_argument("--secret-out", default="~/puzzle-hit-%d.json" % int(time.time()),
                    help="arquivo 0600 FORA do repo para seed e chaves")
    args = ap.parse_args()
    if args.self_test:
        return self_test(args)
    if args.candidate is None:
        ap.error("--candidate e obrigatorio")

    seed, keys = derive(args, args.candidate)
    r = compare(keys, *load_public())
    print(json.dumps({k: v for k, v in r.items()}, indent=1))
    if not r["full_match"]:
        print("NAO CONFIRMADO: nenhum segredo gravado.")
        return 1
    path = write_secret(args.secret_out, {
        "params": {k: v for k, v in vars(args).items() if k not in ("secret_out", "self_test")},
        "seed_hex": seed.hex(), "keys_hex": {n: "%064x" % k for n, k in keys.items()}})
    print("CONFIRMADO. Segredos em %s (0600). NAO cole o conteudo na conversa." % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
