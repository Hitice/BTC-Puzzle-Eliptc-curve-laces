import math
import random

SOLVED_PUZZLES = {
    1:  0x1, 2: 0x3, 3: 0x7, 4: 0x8, 5: 0x15,
    6:  0x31, 7: 0x4c, 8: 0xe0, 9: 0x1d3, 10: 0x202,
    11: 0x483, 12: 0xa7b, 13: 0x1460, 14: 0x2930, 15: 0x68f3,
    16: 0xc936, 17: 0x1764f, 18: 0x3080d, 19: 0x5749f, 20: 0xd2c55,
    21: 0x1ba534, 22: 0x2de40f, 23: 0x556e52, 24: 0xdc2a04, 25: 0x1fa5ee5,
    26: 0x340326e, 27: 0x6ac3875, 28: 0xd916ce8, 29: 0x17e2551e, 30: 0x3d94cd64,
    31: 0x7d4fe747, 32: 0xb862a62e, 33: 0x1a96ca8d8, 34: 0x34a65911d, 35: 0x4aed21170,
    36: 0x9de820a7c, 37: 0x1757756a93, 38: 0x22382facd0, 39: 0x4b5f8303e9, 40: 0xe9ae4933d6,
    41: 0x153869acc5b, 42: 0x2a221c58d8f, 43: 0x6bd3b27c591, 44: 0xe02b35a358f, 45: 0x122fca143c05,
    46: 0x2ec18388d544, 47: 0x6cd610b53cba, 48: 0xade6d7ce3b9b, 49: 0x174176b015f4d, 50: 0x22bd43c2e9354,
    51: 0x75070a1a009d4, 52: 0xefae164cb9e3c, 53: 0x180788e47e326c, 54: 0x236fb6d5ad1f43, 55: 0x6abe1f9b67e114,
    56: 0x9d18b63ac4ffdf, 57: 0x1eb25c90795d61c, 58: 0x2c675b852189a21, 59: 0x7496cbb87cab44f, 60: 0xfc07a1825367bbe,
    61: 0x13c96a3742f64906, 62: 0x363d541eb611abee, 63: 0x7cce5efdaccf6808, 64: 0xf7051f27b09112d4,
    65: 0x1a838b13505b26867, 66: 0x2832ed74f2b5e35ee, 67: 0x730fc235c1942c1ae, 68: 0xbebb3940cd0fc1491,
    69: 0x101d83275fb2bc7e0c, 70: 0x349b84b6431a6c4ef1,
}

def norm_pos(n, key):
    lo = 1 << (n - 1)
    hi = (1 << n) - 1
    if hi == lo:
        return 0.5
    return (key - lo) / (hi - lo)

seq_keys = sorted(k for k in SOLVED_PUZZLES if k <= 70)
seq_pos = [norm_pos(k, SOLVED_PUZZLES[k]) * 100 for k in seq_keys]
N = len(seq_pos)

# =====================================================================
#  ANOMALIA 1: PRIMEIRO NIBBLE ENVIESADO
# =====================================================================
print("=" * 70)
print("ANOMALIA 1: PRIMEIRO NIBBLE ENVIESADO")
print("=" * 70)

# Primeiro: entender POR QUE o primeiro nibble seria enviesado
print(f"\n  Contexto: cada chave esta no range [2^(n-1), 2^n - 1].")
print(f"  O MSB e sempre 1. O primeiro nibble hex depende de n mod 4:\n")
print(f"  {'n mod 4':>8}  {'Bits no 1o nibble':>18}  {'Nibbles possiveis':>20}  {'Puzzles'}")
print(f"  {'-'*8}  {'-'*18}  {'-'*20}  {'-'*30}")

mod_groups = {0: [], 1: [], 2: [], 3: []}
for k in seq_keys:
    mod_groups[k % 4].append(k)

for mod in range(4):
    bits_in_first = ((mod) % 4)
    if bits_in_first == 0:
        bits_in_first = 4
    n_bits = (mod % 4) if (mod % 4) != 0 else 4

    if mod == 1:
        possible = "1 (forcado)"
        n_bits_str = "1 bit"
    elif mod == 2:
        possible = "2,3"
        n_bits_str = "2 bits"
    elif mod == 3:
        possible = "4,5,6,7"
        n_bits_str = "3 bits"
    else:
        possible = "8,9,A,B,C,D,E,F"
        n_bits_str = "4 bits"

    puzzles_str = f"{len(mod_groups[mod])} puzzles"
    print(f"  {mod:>8}  {n_bits_str:>18}  {possible:>20}  {puzzles_str}")

# Contar quantos puzzles tem n % 4 == 1 (primeiro nibble FORCADO a ser 1)
forced_1 = len(mod_groups[1])
print(f"\n  Puzzles com n mod 4 = 1 (nibble forcado '1'): {forced_1} de {N}")
print(f"  Isso sozinho ja explica {forced_1} dos primeiros nibbles '1'.")

# Calcular distribuicao ESPERADA do primeiro nibble dado a estrutura dos ranges
print(f"\n{'-'*70}")
print(f"  CALCULANDO DISTRIBUICAO ESPERADA vs OBSERVADA:")
print(f"{'-'*70}")

expected_first_nibble = [0.0] * 16
observed_first_nibble = [0] * 16

for k in seq_keys:
    key = SOLVED_PUZZLES[k]
    hex_str = format(key, 'x')
    first_nib = int(hex_str[0], 16)
    observed_first_nibble[first_nib] += 1

    # Qual o range de primeiros nibbles possiveis para este puzzle?
    lo = 1 << (k - 1)
    hi = (1 << k) - 1
    lo_hex = format(lo, 'x')
    hi_hex = format(hi, 'x')
    lo_first = int(lo_hex[0], 16)
    hi_first = int(hi_hex[0], 16)

    # Para uma chave uniforme no range, a probabilidade de cada primeiro nibble
    # depende de quantos valores comecam com esse nibble
    n_hex_digits = len(hi_hex)
    possible_nibs = list(range(lo_first, hi_first + 1))

    if len(possible_nibs) == 1:
        expected_first_nibble[possible_nibs[0]] += 1.0
    else:
        # Primeiro e ultimo nibble podem ter ranges parciais
        # Nibbles do meio tem range completo
        total_keys = hi - lo + 1
        for nib in possible_nibs:
            # Contar quantas chaves comecam com este nibble
            nib_lo = nib << ((n_hex_digits - 1) * 4)
            nib_hi = ((nib + 1) << ((n_hex_digits - 1) * 4)) - 1
            actual_lo = max(lo, nib_lo)
            actual_hi = min(hi, nib_hi)
            count = max(0, actual_hi - actual_lo + 1)
            expected_first_nibble[nib] += count / total_keys

print(f"\n  {'Nibble':>8}  {'Observado':>10}  {'Esperado':>10}  {'Diff':>8}  {'Status'}")
print(f"  {'-'*8}  {'-'*10}  {'-'*10}  {'-'*8}  {'-'*20}")

chi2 = 0
for i in range(16):
    obs = observed_first_nibble[i]
    exp = expected_first_nibble[i]
    diff = obs - exp
    if exp > 0:
        chi2 += (obs - exp) ** 2 / exp
        status = "<<<" if abs(diff) > 3 else ""
    else:
        status = "" if obs == 0 else "INESPERADO"
    print(f"  0x{i:X}:     {obs:8.0f}    {exp:8.2f}    {diff:+6.2f}  {status}")

# Graus de liberdade: categorias com esperado > 0 menos 1
df = sum(1 for e in expected_first_nibble if e > 0) - 1
chi2_crit_5 = {5: 11.07, 6: 12.59, 7: 14.07, 8: 15.51, 9: 16.92, 10: 18.31,
               11: 19.68, 12: 21.03, 13: 22.36, 14: 23.68, 15: 25.0}.get(df, 25.0)

print(f"\n  Chi-quadrado: {chi2:.4f}")
print(f"  Graus de liberdade: {df}")
print(f"  Valor critico (5%): {chi2_crit_5:.2f}")
print(f"  {'REJEITA H0: distribuicao nao esperada' if chi2 > chi2_crit_5 else 'NAO REJEITA H0: distribuicao consistente com o esperado'}")

# Monte Carlo: simular chaves uniformes nos mesmos ranges
print(f"\n{'-'*70}")
print(f"  MONTE CARLO: 500.000 simulacoes de chaves uniformes")
print(f"{'-'*70}")

random.seed(42)
N_SIM = 500_000
sim_chi2s = []

for _ in range(N_SIM):
    sim_first = [0] * 16
    for k in seq_keys:
        lo = 1 << (k - 1)
        hi = (1 << k) - 1
        fake_key = random.randint(lo, hi)
        fake_nib = int(format(fake_key, 'x')[0], 16)
        sim_first[fake_nib] += 1

    sim_chi2 = 0
    for i in range(16):
        exp = expected_first_nibble[i]
        if exp > 0:
            sim_chi2 += (sim_first[i] - exp) ** 2 / exp
    sim_chi2s.append(sim_chi2)

p_mc = sum(1 for s in sim_chi2s if s >= chi2) / N_SIM
sim_chi2s.sort()
print(f"  Chi2 observado: {chi2:.4f}")
print(f"  Chi2 medio simulado: {sum(sim_chi2s)/len(sim_chi2s):.4f}")
print(f"  Chi2 mediano simulado: {sim_chi2s[len(sim_chi2s)//2]:.4f}")
print(f"  P-value Monte Carlo: {p_mc:.6f} ({p_mc*100:.3f}%)")
print(f"  {'SIGNIFICATIVO a 5%' if p_mc < 0.05 else 'NAO SIGNIFICATIVO a 5%'}")

# Conclusao anomalia 1
print(f"\n{'='*70}")
print(f"  VEREDITO ANOMALIA 1:")
if p_mc >= 0.05:
    print(f"  A predominancia do nibble '1' e um ARTEFATO MATEMATICO.")
    print(f"  Quando n mod 4 = 1, o primeiro nibble hex e FORCADO a ser '1'")
    print(f"  porque so ha 1 bit no primeiro nibble (que e sempre 1).")
    print(f"  A distribuicao observada e EXATAMENTE a esperada para chaves")
    print(f"  uniformemente aleatorias nos seus ranges. NAO e um padrao.")
else:
    print(f"  ANOMALIA REAL: a distribuicao difere do esperado (p={p_mc:.4f}).")
    print(f"  Investigar se o gerador tem bias no primeiro nibble.")
print(f"{'='*70}")


# =====================================================================
#  ANOMALIA 2: PERIODICIDADE NA FFT
# =====================================================================
print(f"\n\n{'='*70}")
print("ANOMALIA 2: PERIODICIDADE NA FFT")
print(f"{'='*70}")

# Calcular DFT do sinal real
def compute_dft_magnitudes(series):
    n = len(series)
    mags = []
    for k in range(1, n // 2):
        re = sum(series[i] * math.cos(2 * math.pi * k * i / n) for i in range(n))
        im = sum(series[i] * math.sin(2 * math.pi * k * i / n) for i in range(n))
        mag = math.sqrt(re**2 + im**2) / n
        mags.append((k, mag, n / k))
    return mags

observed_mags = compute_dft_magnitudes(seq_pos)
observed_mags.sort(key=lambda x: x[1], reverse=True)
top_freq = observed_mags[0][0]
top_mag = observed_mags[0][1]
top_period = observed_mags[0][2]
max_mag = top_mag

print(f"\n  Frequencia dominante observada:")
print(f"    freq = {top_freq}, periodo = {top_period:.1f}, magnitude = {top_mag:.4f}")
print(f"\n  Top 5 frequencias:")
for k, mag, period in observed_mags[:5]:
    print(f"    freq={k:3d}  periodo={period:5.1f}  mag={mag:.4f}")

# Teste de Fisher: a maior magnitude e significativa?
print(f"\n{'-'*70}")
print(f"  TESTE DE FISHER (g-statistic) para periodicidade")
print(f"{'-'*70}")

all_mag_sq = [m[1]**2 for m in observed_mags]
g_stat = max(all_mag_sq) / sum(all_mag_sq)
n_freqs = len(all_mag_sq)

# P-value para g-statistic (Bonferroni upper bound)
p_fisher = n_freqs * math.exp(-n_freqs * g_stat) if n_freqs * g_stat < 700 else 0.0
# Better approximation
p_fisher_exact = 0
for j in range(1, n_freqs + 1):
    term = (1 - j * g_stat)
    if term <= 0:
        break
    sign = (-1) ** (j + 1)
    binom = 1
    for i in range(j):
        binom *= (n_freqs - i) / (i + 1)
    p_fisher_exact += sign * binom * (term ** (n_freqs - 1))

print(f"  g = max(|F_k|^2) / sum(|F_k|^2) = {g_stat:.6f}")
print(f"  Numero de frequencias testadas: {n_freqs}")
print(f"  P-value (Fisher exact): {max(0, p_fisher_exact):.6f}")
print(f"  {'SIGNIFICATIVO a 5%' if p_fisher_exact < 0.05 else 'NAO SIGNIFICATIVO a 5%'}")

# Monte Carlo para a maior magnitude
print(f"\n{'-'*70}")
print(f"  MONTE CARLO: 200.000 simulacoes")
print(f"{'-'*70}")

random.seed(123)
N_SIM_FFT = 200_000
count_exceed_max = 0
count_exceed_top3 = 0
sim_max_mags = []

# Pre-compute trig tables
cos_table = [[math.cos(2 * math.pi * k * i / N) for i in range(N)] for k in range(1, N // 2)]
sin_table = [[math.sin(2 * math.pi * k * i / N) for i in range(N)] for k in range(1, N // 2)]
n_freqs_check = N // 2 - 1

for sim in range(N_SIM_FFT):
    fake = [random.uniform(0, 100) for _ in range(N)]
    sim_max_mag = 0
    for kidx in range(n_freqs_check):
        re = sum(fake[i] * cos_table[kidx][i] for i in range(N))
        im = sum(fake[i] * sin_table[kidx][i] for i in range(N))
        mag = math.sqrt(re**2 + im**2) / N
        if mag > sim_max_mag:
            sim_max_mag = mag
    sim_max_mags.append(sim_max_mag)
    if sim_max_mag >= top_mag:
        count_exceed_max += 1
    if sim % 50000 == 0 and sim > 0:
        print(f"    ... {sim}/{N_SIM_FFT} simulacoes")

p_mc_fft = count_exceed_max / N_SIM_FFT
sim_max_mags.sort()
pct_95 = sim_max_mags[int(N_SIM_FFT * 0.95)]
pct_99 = sim_max_mags[int(N_SIM_FFT * 0.99)]

print(f"\n  Magnitude maxima observada: {top_mag:.4f}")
print(f"  Distribuicao simulada da magnitude maxima:")
print(f"    Media:     {sum(sim_max_mags)/len(sim_max_mags):.4f}")
print(f"    Percentil 95%: {pct_95:.4f}")
print(f"    Percentil 99%: {pct_99:.4f}")
print(f"  P-value: {p_mc_fft:.6f} ({p_mc_fft*100:.3f}%)")
print(f"  {'SIGNIFICATIVO a 5%' if p_mc_fft < 0.05 else 'NAO SIGNIFICATIVO a 5%'}")

# Teste para cada uma das top 3 frequencias individualmente
print(f"\n{'-'*70}")
print(f"  TESTE INDIVIDUAL das top 3 frequencias (com Bonferroni)")
print(f"{'-'*70}")

random.seed(456)
N_SIM_IND = 300_000
for rank, (freq, mag, period) in enumerate(observed_mags[:3]):
    kidx = freq - 1
    count = 0
    for _ in range(N_SIM_IND):
        fake = [random.uniform(0, 100) for _ in range(N)]
        re = sum(fake[i] * cos_table[kidx][i] for i in range(N))
        im = sum(fake[i] * sin_table[kidx][i] for i in range(N))
        sim_mag = math.sqrt(re**2 + im**2) / N
        if sim_mag >= mag:
            count += 1
    p_ind = count / N_SIM_IND
    p_bonf = min(1.0, p_ind * n_freqs)
    print(f"\n  Freq {freq} (periodo {period:.1f}, mag {mag:.4f}):")
    print(f"    P-value individual:  {p_ind:.6f} ({p_ind*100:.3f}%)")
    print(f"    P-value Bonferroni:  {p_bonf:.6f} ({p_bonf*100:.3f}%)")
    print(f"    {'SIGNIFICATIVO' if p_bonf < 0.05 else 'NAO SIGNIFICATIVO'} apos correcao")

# Teste de permutacao para FFT
print(f"\n{'-'*70}")
print(f"  TESTE DE PERMUTACAO para magnitude maxima FFT")
print(f"{'-'*70}")

random.seed(789)
N_PERM = 200_000
count_perm = 0

for _ in range(N_PERM):
    shuffled = seq_pos[:]
    random.shuffle(shuffled)
    perm_max = 0
    for kidx in range(n_freqs_check):
        re = sum(shuffled[i] * cos_table[kidx][i] for i in range(N))
        im = sum(shuffled[i] * sin_table[kidx][i] for i in range(N))
        mag = math.sqrt(re**2 + im**2) / N
        if mag > perm_max:
            perm_max = mag
    if perm_max >= top_mag:
        count_perm += 1

p_perm_fft = count_perm / N_PERM
print(f"  Magnitude maxima observada: {top_mag:.4f}")
print(f"  P-value permutacao: {p_perm_fft:.6f} ({p_perm_fft*100:.3f}%)")
print(f"  {'SIGNIFICATIVO a 5%' if p_perm_fft < 0.05 else 'NAO SIGNIFICATIVO a 5%'}")

# =====================================================================
#  VEREDITO FINAL
# =====================================================================
print(f"\n\n{'='*70}")
print("VEREDITO FINAL - AMBAS AS ANOMALIAS")
print(f"{'='*70}")

print(f"\n  ANOMALIA 1 - Primeiro nibble enviesado:")
print(f"    Chi2 p-value:       {p_mc:.6f}")
if p_mc >= 0.05:
    print(f"    RESULTADO: ARTEFATO MATEMATICO (nao e anomalia)")
    print(f"    O primeiro nibble '1' domina porque em 25% dos puzzles")
    print(f"    (n mod 4 = 1), o nibble e FORCADO a ser 1.")
else:
    print(f"    RESULTADO: ANOMALIA REAL")

print(f"\n  ANOMALIA 2 - Periodicidade FFT:")
print(f"    Fisher p-value:     {max(0, p_fisher_exact):.6f}")
print(f"    Monte Carlo p-value: {p_mc_fft:.6f}")
print(f"    Permutacao p-value:  {p_perm_fft:.6f}")
if p_mc_fft >= 0.05 and p_perm_fft >= 0.05:
    print(f"    RESULTADO: RUIDO ESTATISTICO (nao e anomalia)")
    print(f"    As frequencias dominantes sao compativeis com dados aleatorios.")
else:
    print(f"    RESULTADO: PERIODICIDADE REAL DETECTADA")

all_noise = (p_mc >= 0.05) and (p_mc_fft >= 0.05) and (p_perm_fft >= 0.05)
print(f"\n  {'='*50}")
if all_noise:
    print(f"  CONCLUSAO GERAL: TODAS as anomalias sao RUIDO.")
    print(f"  Nenhum padrao exploravel nos dados de geracao.")
    print(f"  As chaves sao estatisticamente indistinguiveis")
    print(f"  de valores uniformemente aleatorios nos seus ranges.")
else:
    print(f"  CONCLUSAO GERAL: Ha sinais que merecem investigacao.")
print(f"  {'='*50}")
print()
