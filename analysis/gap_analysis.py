"""
Gap analysis - testa hipoteses que NAO foram cobertas pelos scripts anteriores.
Le a fonte de verdade (../data/puzzles.json) e ../data/signatures.json.

Foco:
  1. Deteccao de LCG (gerador linear congruente) nos bits baixos consecutivos
  2. Deteccao de Truncated-LCG / multiplicador via pares
  3. Bias modular (chaves mod primos pequenos)
  4. Bias por posicao de bit
  5. Teste binomial exato do MSB de r (ECDSA) - o sinal que ficou pendente
  6. Fingerprint de PRNG comum (passo constante / razao constante mod N)
"""
import json
import os
import math
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
N_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

with open(os.path.join(DATA, "puzzles.json")) as f:
    PUZZLES = json.load(f)["puzzles"]

SOLVED = {p["puzzle"]: p["privkey_int"] for p in PUZZLES if p["status"] == "solved"}

def unmask(n, key):
    """Bits baixos (n-1) da chave original da wallet."""
    return key - (1 << (n - 1))

def modinv(a, m):
    a %= m
    if math.gcd(a, m) != 1:
        return None
    return pow(a, -1, m)

print("=" * 72)
print("GAP ANALYSIS - hipoteses ainda nao testadas")
print("=" * 72)

# Sequencia consecutiva 1..70 (todos resolvidos)
seq = sorted(k for k in SOLVED if k <= 70)
unmasked = {n: unmask(n, SOLVED[n]) for n in seq}

# ============================================================
# 1. DETECCAO DE LCG (o teste que faltou)
# ============================================================
print(f"\n{'='*72}")
print("1. DETECCAO DE LCG: w_{i+1} = A*w_i + C mod 2^k")
print("   Se a wallet usou LCG, A e C devem ser CONSISTENTES entre triplas.")
print(f"{'='*72}")

# Para uma tripla (n, n+1, n+2), todos consecutivos, resolvemos A,C mod 2^(n-1)
# usando os bits baixos comuns e verificamos contra a proxima tripla.
print(f"\n  Resolvendo A,C por tripla e testando consistencia:\n")
print(f"  {'Tripla':>12}  {'width':>5}  {'A (hex)':>18}  {'C (hex)':>18}  {'predicao ok?'}")
print(f"  {'-'*12}  {'-'*5}  {'-'*18}  {'-'*18}  {'-'*12}")

solutions = []
triples = [(n, n+1, n+2) for n in seq if (n+1 in seq and n+2 in seq)]

for a_idx, b_idx, c_idx in triples:
    w = a_idx - 1  # bits comuns garantidos pelos 3
    if w < 8:
        continue
    mod = 1 << w
    u0 = unmasked[a_idx] % mod
    u1 = unmasked[b_idx] % mod
    u2 = unmasked[c_idx] % mod

    d1 = (u1 - u0) % mod
    d2 = (u2 - u1) % mod
    inv = modinv(d1, mod)
    if inv is None:
        continue
    A = (d2 * inv) % mod
    C = (u1 - A * u0) % mod

    # verificar contra a tripla seguinte (se existir) no mesmo modulo
    ok = "n/a"
    if c_idx + 1 in seq:
        u3 = unmasked[c_idx + 1] % mod
        pred = (A * u2 + C) % mod
        ok = "SIM" if pred == u3 else "nao"
    solutions.append((a_idx, A, C, mod, ok))
    print(f"  {a_idx:>2}-{b_idx}-{c_idx:<2}    {w:>5}  {format(A, 'x')[:18]:>18}  {format(C, 'x')[:18]:>18}  {ok}")

n_ok = sum(1 for _, _, _, _, ok in solutions if ok == "SIM")
n_test = sum(1 for _, _, _, _, ok in solutions if ok in ("SIM", "nao"))
print(f"\n  Predicoes corretas: {n_ok}/{n_test}")
if n_ok == n_test and n_test > 3:
    print("  >>> LCG DETECTADO! As chaves sao previsiveis! <<<")
elif n_ok > n_test * 0.5 and n_test > 3:
    print("  >>> Possivel LCG parcial - investigar mais <<<")
else:
    print("  >>> NAO e LCG. Cada A,C e diferente (esperado p/ hash-based). <<<")

# ============================================================
# 2. RAZAO / PASSO CONSTANTE mod N (multiplicativo e aditivo)
# ============================================================
print(f"\n{'='*72}")
print("2. PASSO/RAZAO CONSTANTE mod N (chaves COMPLETAS, nao mascaradas)")
print("   ATENCAO: so vale se as chaves do puzzle = chaves da wallet (sem mascara alta)")
print(f"{'='*72}")

# Usar as chaves completas dos resolvidos consecutivos
diffs_full = []
ratios_full = []
for i in range(len(seq) - 1):
    n, m = seq[i], seq[i+1]
    if m - n != 1:
        continue
    kn, km = SOLVED[n], SOLVED[m]
    diffs_full.append((km - kn) % N_ORDER)
    inv = modinv(kn, N_ORDER)
    if inv:
        ratios_full.append((km * inv) % N_ORDER)

print(f"\n  Diferencas consecutivas (mod N) identicas? {len(set(diffs_full)) == 1}")
print(f"  Razoes consecutivas (mod N) identicas?     {len(set(ratios_full)) == 1}")
print("  (qualquer 'SIM' acima = estrutura aritmetica explrloravel)")
print("  -> Esperado 'False' pois as chaves estao mascaradas em ranges distintos.")

# ============================================================
# 3. BIAS MODULAR (chaves mod primos pequenos)
# ============================================================
print(f"\n{'='*72}")
print("3. BIAS MODULAR: distribuicao das chaves mod primos pequenos")
print("   Gerador fraco -> residuos enviesados.")
print(f"{'='*72}")

all_keys = list(SOLVED.values())
primes = [3, 5, 7, 11, 13, 17, 19, 23]
print(f"\n  {'p':>4}  {'chi2':>8}  {'df':>3}  {'critico(5%)':>11}  {'veredito'}")
print(f"  {'-'*4}  {'-'*8}  {'-'*3}  {'-'*11}  {'-'*20}")

chi2_crit = {2: 5.99, 4: 9.49, 6: 12.59, 10: 18.31, 12: 21.03, 16: 26.30,
             18: 28.87, 22: 33.92}

for p in primes:
    residues = [k % p for k in all_keys]
    counts = Counter(residues)
    expected = len(all_keys) / p
    chi2 = sum((counts.get(r, 0) - expected) ** 2 / expected for r in range(p))
    df = p - 1
    crit = chi2_crit.get(df, df + 2 * math.sqrt(2 * df))
    verdict = "ENVIESADO!" if chi2 > crit else "uniforme"
    print(f"  {p:>4}  {chi2:>8.2f}  {df:>3}  {crit:>11.2f}  {verdict}")

# ============================================================
# 4. BIAS POR POSICAO DE BIT
# ============================================================
print(f"\n{'='*72}")
print("4. BIAS POR POSICAO DE BIT (cada bit 'livre' deve ser 1 em ~50%)")
print(f"{'='*72}")

# Para cada posicao de bit j, contar quantas chaves tem bit j = 1
# considerando apenas chaves onde j e um bit 'livre' (j < n-1)
bit_stats = {}  # j -> [count_1, total]
for n, key in SOLVED.items():
    free_bits = n - 1
    for j in range(free_bits):
        if j not in bit_stats:
            bit_stats[j] = [0, 0]
        bit_stats[j][1] += 1
        if (key >> j) & 1:
            bit_stats[j][0] += 1

print(f"\n  Bits com desvio significativo de 50% (|z| > 2.5):")
anomalous_bits = []
for j in sorted(bit_stats):
    ones, total = bit_stats[j]
    if total < 10:
        continue
    p_hat = ones / total
    se = math.sqrt(0.25 / total)
    z = (p_hat - 0.5) / se
    if abs(z) > 2.5:
        anomalous_bits.append((j, p_hat, total, z))
        print(f"    bit {j:>2}: {p_hat:.1%} de 1s (n={total}, z={z:+.2f})")

if not anomalous_bits:
    print("    Nenhum. Todos os bits ~50% (sem bias posicional).")

# ============================================================
# 5. ECDSA: TESTE BINOMIAL EXATO DO MSB DE r
# ============================================================
print(f"\n{'='*72}")
print("5. ECDSA - MSB de r: teste binomial exato (sinal pendente)")
print(f"{'='*72}")

sig_path = os.path.join(DATA, "signatures.json")
if os.path.exists(sig_path):
    with open(sig_path) as f:
        sigs_data = json.load(f)

    all_r = []
    for pnum, sigs in sigs_data.items():
        for s in sigs:
            all_r.append(int(s["r"], 16))

    msb_high = sum(1 for r in all_r if (r >> 255) & 1 or r.to_bytes(32, 'big')[0] >= 0x80)
    # contagem correta do byte mais significativo
    msb_high = sum(1 for r in all_r if r.to_bytes(32, 'big')[0] >= 0x80)
    n_sig = len(all_r)
    msb_low = n_sig - msb_high

    def binom_two_tailed(k, n, p=0.5):
        def C(n, r):
            return math.comb(n, r)
        obs = abs(k - n * p)
        total = 0.0
        for i in range(n + 1):
            if abs(i - n * p) >= obs - 1e-9:
                total += C(n, i) * (p ** i) * ((1 - p) ** (n - i))
        return min(1.0, total)

    p_val = binom_two_tailed(msb_high, n_sig)
    z = (msb_high - n_sig * 0.5) / math.sqrt(n_sig * 0.25)
    print(f"\n  Total assinaturas: {n_sig}")
    print(f"  MSB(r) >= 0x80: {msb_high}  |  MSB(r) < 0x80: {msb_low}")
    print(f"  Esperado: {n_sig/2:.1f} / {n_sig/2:.1f}")
    print(f"  Z-score: {z:+.3f}")
    print(f"  P-value binomial exato (bicaudal): {p_val:.4f}")
    if p_val < 0.05:
        print("  >>> SIGNIFICATIVO. Mas: r e coordenada publica, nao revela k diretamente.")
        print("      Util SO se houver multiplas sigs/chave com nonce enviesado.")
        # quantas chaves tem >1 sig?
        multi = {p: len(s) for p, s in sigs_data.items() if len(s) > 1}
        print(f"      Chaves com >1 assinatura: {multi}")
        print("      (todas resolvidas; os ALVOS 135-160 tem 1 sig cada -> nao explrloravel)")
    else:
        print("  >>> NAO significativo. Sinal era ruido amostral. Fechado.")
else:
    print("  signatures.json nao encontrado.")

# ============================================================
# 6. SOMA DE VERIFICACAO: posicao vs indice (tendencia oculta)
# ============================================================
print(f"\n{'='*72}")
print("6. TENDENCIA position_in_range vs numero do puzzle (regressao linear)")
print(f"{'='*72}")

pts = [(p["puzzle"], p["position_in_range"]) for p in PUZZLES if p["status"] == "solved"]
xs = [x for x, _ in pts]
ys = [y for _, y in pts]
npts = len(xs)
mx = sum(xs) / npts
my = sum(ys) / npts
cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
vx = sum((x - mx) ** 2 for x in xs)
slope = cov / vx
r_corr = cov / math.sqrt(vx * sum((y - my) ** 2 for y in ys))
print(f"\n  Inclinacao: {slope:+.6f} por puzzle")
print(f"  Correlacao r: {r_corr:+.4f}")
print(f"  {'TENDENCIA DETECTADA' if abs(r_corr) > 0.3 else 'sem tendencia (posicao independe do indice)'}")

# ============================================================
print(f"\n{'='*72}")
print("RESUMO GAP ANALYSIS")
print(f"{'='*72}")
print(f"""
  1. LCG detection:        {'PREVISIVEL!' if (n_test>3 and n_ok==n_test) else 'negativo (hash-based)'}
  2. Passo/razao mod N:    {'estrutura!' if (len(set(diffs_full))==1 or len(set(ratios_full))==1) else 'negativo'}
  3. Bias modular:         ver tabela acima
  4. Bias por bit:         {len(anomalous_bits)} bits anomalos
  5. ECDSA MSB(r):         {'ver p-value' }
  6. Tendencia posicional: {'sim' if abs(r_corr) > 0.3 else 'nao'}
""")
