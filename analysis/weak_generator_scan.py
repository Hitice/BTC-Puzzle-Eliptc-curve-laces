"""
Caça a GERADOR FRACO: testa se as 82 chaves conhecidas satisfazem algum esquema
determinístico baseado em HASH ou compressão — coisa que as rodadas anteriores
(aritmética: LCG, linear, derivação) NÃO cobriram.

NÃO é bruteforce nem kangaroo. É falsificação direta contra dados reais:
  1. Index-hash:  chave_i  ?=  H(encoding(i))   (mascarado ao range)        [muitos H, muitas codificações]
  2. Seed-hash:   chave_i  ?=  H(seed || i)     para seeds adivinháveis
  3. Hash-chain:  low(chave_{i+1}) ?= low(H(chave_i))                        [poder limitado pela máscara]
  4. Compressão:  os bytes "aleatórios" das chaves comprimem? (proxy de K(x))

Máscara: chave do puzzle n vive em [2^(n-1), 2^n); os bits que conhecemos da "wallet"
são os baixos (n-1). Um candidato v vira:  pred = (v & (2^(n-1)-1)) | 2^(n-1).
Puzzles grandes (#100..#130) dão ~100-130 bits de poder de checagem -> um acerto seria
inconfundível.

Python stdlib puro.
"""
import json, os, hashlib, zlib, bz2, lzma

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "..", "data", "puzzles.json")) as f:
    PUZ = json.load(f)["puzzles"]
SOLVED = {p["puzzle"]: p["privkey_int"] for p in PUZ if p["status"] == "solved"}

def low_bits(n, key):
    return key & ((1 << (n - 1)) - 1)   # bits baixos da wallet (sem o bit de range)

def predict_from_candidate(n, v):
    """candidato v (int) -> chave de puzzle prevista para bits n."""
    return (v & ((1 << (n - 1)) - 1)) | (1 << (n - 1))

HASHES = {
    "sha256":  lambda b: hashlib.sha256(b).digest(),
    "sha256d": lambda b: hashlib.sha256(hashlib.sha256(b).digest()).digest(),
    "sha512":  lambda b: hashlib.sha512(b).digest(),
    "sha1":    lambda b: hashlib.sha1(b).digest(),
    "md5":     lambda b: hashlib.md5(b).digest(),
    "blake2b": lambda b: hashlib.blake2b(b).digest(),
    "keccak?": lambda b: hashlib.sha3_256(b).digest(),
}
try:
    hashlib.new("ripemd160")
    HASHES["ripemd160"] = lambda b: hashlib.new("ripemd160", b).digest()
except Exception:
    pass

def encodings(i):
    """Várias codificações plausíveis do índice i."""
    out = {}
    out["int_min_be"] = i.to_bytes(max(1, (i.bit_length()+7)//8), "big")
    out["int4_be"]    = i.to_bytes(4, "big")
    out["int8_be"]    = i.to_bytes(8, "big")
    out["int4_le"]    = i.to_bytes(4, "little")
    out["str"]        = str(i).encode()
    out["hex"]        = ("%x" % i).encode()
    out["str0pad"]    = ("%03d" % i).encode()
    return out

def to_int(digest):
    return int.from_bytes(digest, "big")

def scan_index_hash():
    print("=" * 74)
    print("1+2. INDEX-HASH e SEED-HASH:  chave_i ?= H([seed||] encoding(i))")
    print("=" * 74)
    seeds = [b"", b"satoshi", b"bitcoin", b"puzzle", b"saatoshi_rising",
             b"\x00", bytes([1])]
    nums = sorted(SOLVED)
    best = None
    total_tests = 0
    for hname, hfn in HASHES.items():
        for ename in ("int_min_be","int4_be","int8_be","int4_le","str","hex","str0pad"):
            for seed in seeds:
                total_tests += 1
                matches = []
                for n in nums:
                    enc = encodings(n)[ename]
                    cand = to_int(hfn(seed + enc))
                    if predict_from_candidate(n, cand) == SOLVED[n]:
                        matches.append(n)
                if matches:
                    # ponderar por poder: acerto em puzzle grande vale muito
                    power = max(matches)
                    if best is None or len(matches) > best[0] or power > best[1]:
                        best = (len(matches), power, hname, ename, seed, matches)
    # veredito honesto: só é REAL se bater em algum puzzle com poder (n>=30 bits).
    # acertos confinados a ranges pequenos (<30 bits) são esperados por acaso.
    if best and best[1] >= 30:
        print(f"  !!! ACERTO REAL: {best[2]} / enc={best[3]} / seed={best[4]!r}")
        print(f"      bate em {best[0]} puzzles incluindo #{best[1]} (>=30 bits): {best[5]}")
        print(f"      >>> GERADOR ENCONTRADO. Verificar imediatamente!")
    elif best:
        print(f"  Melhor 'acerto' confinado a ranges pequenos (máx #{best[1]} bits): {best[5]}")
        print(f"      {best[2]}/enc={best[3]}/seed={best[4]!r} — bate só em puzzles minúsculos,")
        print(f"      NENHUM com >=30 bits. Artefato de comparação múltipla (esperado).")
        print(f"      -> Index/seed-hash REJEITADO.")
    else:
        # quantos acertos espúrios isolados (esperado ~ poucos em puzzles minúsculos)
        print(f"  Testes feitos: {total_tests} (hash x codificação x seed)")
        print(f"  Nenhum esquema bate em >=2 puzzles. (acertos isolados em #1-#4 são")
        print(f"  esperados por acaso: range minúsculo, poucos valores possíveis.)")
        print(f"  -> Index/seed-hash REJEITADO.")

def scan_hash_chain():
    print("\n" + "=" * 74)
    print("3. HASH-CHAIN:  low(chave_{i+1}) ?= low(H(chave_i))   (consecutivos #1-70)")
    print("=" * 74)
    nums = [k for k in sorted(SOLVED) if k <= 70]
    hits = {h: 0 for h in HASHES}
    tested = 0
    for idx in range(len(nums) - 1):
        a, b = nums[idx], nums[idx + 1]
        if b - a != 1:
            continue
        tested += 1
        wb = b - 1   # bits conhecidos da wallet em b
        target = low_bits(b, SOLVED[b])
        ka_bytes = SOLVED[a].to_bytes(32, "big")
        for hname, hfn in HASHES.items():
            cand = to_int(hfn(ka_bytes)) & ((1 << wb) - 1)
            if cand == target:
                hits[hname] += 1
    print(f"  Pares testados: {tested}")
    any_hit = False
    for h, c in hits.items():
        if c > 0:
            print(f"  {h}: {c} acertos  <<<"); any_hit = True
    if not any_hit:
        print("  Nenhum acerto em nenhum hash. -> Hash-chain REJEITADO.")
        print("  (poder limitado p/ i pequeno pela máscara; forte p/ i grande.)")

def scan_compression():
    print("\n" + "=" * 74)
    print("4. COMPRESSÃO dos bytes 'aleatórios' das chaves (proxy de incompressibilidade)")
    print("=" * 74)
    # bytes baixos (8) de cada chave grande -> deveria ser incompressível
    big = [SOLVED[n] for n in sorted(SOLVED) if n >= 40]
    raw = b"".join((k & ((1 << 64) - 1)).to_bytes(8, "big") for k in big)
    print(f"  Amostra: {len(big)} chaves (n>=40), {len(raw)} bytes (8 baixos de cada)")
    for name, comp in (("zlib", zlib.compress), ("bz2", bz2.compress),
                       ("lzma", lzma.compress)):
        c = comp(raw)
        ratio = len(c) / len(raw)
        flag = "  <<< COMPRIME (estrutura!)" if ratio < 0.90 else ""
        print(f"  {name:>5}: {len(c)} bytes  ratio={ratio:.3f}{flag}")
    # baseline: dados realmente aleatórios
    rnd = os.urandom(len(raw))
    print(f"  baseline aleatório (lzma): ratio={len(lzma.compress(rnd))/len(rnd):.3f}")
    print("  (ratios ~>1.0 = incompressível = sem estrutura, como esperado p/ chaves boas.)")

if __name__ == "__main__":
    print(f"Chaves resolvidas carregadas: {len(SOLVED)}\n")
    scan_index_hash()
    scan_hash_chain()
    scan_compression()
    print("\n" + "=" * 74)
    print("Resumo: se tudo acima REJEITOU/incompressível, fecha-se a porta de 'gerador")
    print("fraco baseado em hash/índice' contra os dados reais — sem bruteforce/kangaroo.")
    print("=" * 74)
