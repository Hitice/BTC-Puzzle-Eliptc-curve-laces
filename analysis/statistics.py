import math
from collections import Counter

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
    75: 0x4c5ce114686a1336e07, 80: 0xea1a5c66dcc11b5ad180,
    85: 0x11720c4f018d51b8cebba8, 90: 0x2ce00bb2136a445c71e85bf,
    95: 0x527a792b183c7f64a0e8b1f4, 100: 0xaf55fc59c335c8ec67ed24826,
    105: 0x16f14fc2054cd87ee6396b33df3, 110: 0x35c0d7234df7deb0f20cf7062444,
    115: 0x60f4d11574f5deee49961d9609ac6, 120: 0xb10f22572c497a836ea187f2e1fc23,
    125: 0x1c533b6bb7f0804e09960225e44877ac, 130: 0x33e7665705359f04f28b88cf897c603c9,
}

def norm_pos(n, key):
    lo = 1 << (n - 1)
    hi = (1 << n) - 1
    if hi == lo:
        return 0.5
    return (key - lo) / (hi - lo)

def hamming_ratio(key):
    return bin(key).count('1') / max(1, key.bit_length())

def byte_entropy(key):
    b = key.to_bytes(max(1, (key.bit_length() + 7) // 8), 'big')
    counts = Counter(b)
    total = len(b)
    return -sum((c/total) * math.log2(c/total) for c in counts.values())

def nibbles(key):
    return [int(c, 16) for c in format(key, 'x')]

print("=" * 80)
print("ANALISE COMPLETA DOS PUZZLES BITCOIN RESOLVIDOS")
print("=" * 80)

# --- POSICAO NO RANGE ---
positions = {}
for n in sorted(SOLVED_PUZZLES):
    positions[n] = norm_pos(n, SOLVED_PUZZLES[n]) * 100

pos_vals = list(positions.values())
avg_pos = sum(pos_vals) / len(pos_vals)
std_pos = (sum((p - avg_pos)**2 for p in pos_vals) / len(pos_vals)) ** 0.5
median_pos = sorted(pos_vals)[len(pos_vals) // 2]

print(f"\n{'='*60}")
print("1. POSICAO NORMALIZADA NO RANGE")
print(f"{'='*60}")
print(f"   Media:         {avg_pos:.2f}%  (esperado ~50% se uniforme)")
print(f"   Mediana:       {median_pos:.2f}%")
print(f"   Desvio Padrao: {std_pos:.2f}%  (esperado ~28.87% se uniforme)")
print(f"   Minimo:        {min(pos_vals):.2f}% (Puzzle #{min(positions, key=positions.get)})")
print(f"   Maximo:        {max(pos_vals):.2f}% (Puzzle #{max(positions, key=positions.get)})")

below_25 = sum(1 for p in pos_vals if p < 25)
q2 = sum(1 for p in pos_vals if 25 <= p < 50)
q3 = sum(1 for p in pos_vals if 50 <= p < 75)
above_75 = sum(1 for p in pos_vals if p >= 75)
n = len(pos_vals)
print(f"\n   Distribuicao por quartil:")
print(f"     Q1 (0-25%):    {below_25:2d} puzzles ({below_25/n*100:.1f}%)  [esperado 25%]")
print(f"     Q2 (25-50%):   {q2:2d} puzzles ({q2/n*100:.1f}%)  [esperado 25%]")
print(f"     Q3 (50-75%):   {q3:2d} puzzles ({q3/n*100:.1f}%)  [esperado 25%]")
print(f"     Q4 (75-100%):  {above_75:2d} puzzles ({above_75/n*100:.1f}%)  [esperado 25%]")

# --- AUTOCORRELACAO ---
print(f"\n{'='*60}")
print("2. AUTOCORRELACAO (lag 1 a 5)")
print(f"{'='*60}")

seq_keys = sorted(k for k in SOLVED_PUZZLES if k <= 70)
seq_pos = [positions[k] for k in seq_keys]
seq_avg = sum(seq_pos) / len(seq_pos)
seq_var = sum((p - seq_avg)**2 for p in seq_pos)

for lag in range(1, 6):
    if seq_var == 0:
        break
    corr = sum((seq_pos[i] - seq_avg) * (seq_pos[i+lag] - seq_avg) for i in range(len(seq_pos) - lag))
    corr /= seq_var
    sig = "***" if abs(corr) > 0.3 else "**" if abs(corr) > 0.2 else "*" if abs(corr) > 0.1 else ""
    print(f"   Lag {lag}: {corr:+.4f}  {sig}")

print(f"\n   (*** > 0.3 forte | ** > 0.2 moderada | * > 0.1 fraca)")

# --- RUNS TEST ---
print(f"\n{'='*60}")
print("3. TESTE DE RUNS (sequencias acima/abaixo da mediana)")
print(f"{'='*60}")

med = sorted(seq_pos)[len(seq_pos) // 2]
signs = ['A' if p >= med else 'B' for p in seq_pos]
runs_count = 1
for i in range(1, len(signs)):
    if signs[i] != signs[i-1]:
        runs_count += 1

n_a = signs.count('A')
n_b = signs.count('B')
expected_runs = 1 + 2 * n_a * n_b / (n_a + n_b)
std_runs = math.sqrt(2 * n_a * n_b * (2 * n_a * n_b - n_a - n_b) / ((n_a + n_b)**2 * (n_a + n_b - 1))) if (n_a + n_b) > 1 else 1
z_runs = (runs_count - expected_runs) / std_runs if std_runs > 0 else 0

print(f"   Runs observados:  {runs_count}")
print(f"   Runs esperados:   {expected_runs:.1f}")
print(f"   Z-score:          {z_runs:+.3f}")
print(f"   {'ALEATORIO (nao rejeita H0)' if abs(z_runs) < 1.96 else 'NAO ALEATORIO (rejeita H0 a 5%)'}")

# --- HAMMING WEIGHT ---
print(f"\n{'='*60}")
print("4. HAMMING WEIGHT (proporcao de bits 1)")
print(f"{'='*60}")

hw_vals = []
for n_key in sorted(SOLVED_PUZZLES):
    hw = hamming_ratio(SOLVED_PUZZLES[n_key]) * 100
    hw_vals.append(hw)

avg_hw = sum(hw_vals) / len(hw_vals)
std_hw = (sum((h - avg_hw)**2 for h in hw_vals) / len(hw_vals)) ** 0.5
print(f"   Media:         {avg_hw:.2f}%  (esperado ~50%)")
print(f"   Desvio Padrao: {std_hw:.2f}%")
print(f"   {'NORMAL' if abs(avg_hw - 50) < 5 else 'ANOMALIA DETECTADA'}")

# --- NIBBLE ANALYSIS ---
print(f"\n{'='*60}")
print("5. ANALISE DE NIBBLES (hex digits)")
print(f"{'='*60}")

all_nibs = []
last_nibs = []
first_nibs = []
for n_key in sorted(SOLVED_PUZZLES):
    nibs = nibbles(SOLVED_PUZZLES[n_key])
    all_nibs.extend(nibs)
    last_nibs.append(nibs[-1])
    first_nibs.append(nibs[0])

print(f"\n   Distribuicao de TODOS os nibbles:")
nib_count = Counter(all_nibs)
total_nibs = len(all_nibs)
expected_pct = 100 / 16
for i in range(16):
    c = nib_count.get(i, 0)
    pct = c / total_nibs * 100
    bar = "#" * int(pct * 2)
    deviation = pct - expected_pct
    flag = " <<<" if abs(deviation) > 3 else ""
    print(f"     0x{i:X}: {c:4d} ({pct:5.1f}%) {bar}{flag}")

print(f"\n   Distribuicao do ULTIMO nibble:")
last_count = Counter(last_nibs)
for i in range(16):
    c = last_count.get(i, 0)
    pct = c / len(last_nibs) * 100
    flag = " <<<" if abs(pct - expected_pct) > 8 else ""
    print(f"     0x{i:X}: {c:2d} ({pct:5.1f}%){flag}")

print(f"\n   Distribuicao do PRIMEIRO nibble (apos o bit de range):")
first_count = Counter(first_nibs)
for i in range(16):
    c = first_count.get(i, 0)
    pct = c / len(first_nibs) * 100
    flag = " <<<" if abs(pct - expected_pct) > 8 else ""
    print(f"     0x{i:X}: {c:2d} ({pct:5.1f}%){flag}")

# --- BYTE ENTROPY ---
print(f"\n{'='*60}")
print("6. ENTROPIA POR BYTE")
print(f"{'='*60}")

ent_vals = []
for n_key in sorted(SOLVED_PUZZLES):
    if n_key < 8:
        continue
    ent = byte_entropy(SOLVED_PUZZLES[n_key])
    ent_vals.append((n_key, ent))

avg_ent = sum(e for _, e in ent_vals) / len(ent_vals)
max_possible = math.log2(256)
print(f"   Media:          {avg_ent:.4f} bits (maximo possivel: {max_possible:.4f})")
print(f"   Ratio:          {avg_ent/max_possible*100:.1f}% do maximo")

low_ent = [(n_key, e) for n_key, e in ent_vals if e < avg_ent * 0.7]
if low_ent:
    print(f"\n   Puzzles com entropia anomalamente baixa:")
    for n_key, e in low_ent:
        print(f"     #{n_key}: {e:.4f} bits")

# --- DELTA PATTERN ---
print(f"\n{'='*60}")
print("7. PADROES DE DELTA (diferenca entre posicoes consecutivas)")
print(f"{'='*60}")

deltas = []
for i in range(1, len(seq_keys)):
    delta = seq_pos[i] - seq_pos[i-1]
    deltas.append(delta)

pos_deltas = sum(1 for d in deltas if d > 0)
neg_deltas = sum(1 for d in deltas if d < 0)
avg_abs_delta = sum(abs(d) for d in deltas) / len(deltas)

print(f"   Deltas positivos: {pos_deltas} ({pos_deltas/len(deltas)*100:.1f}%)")
print(f"   Deltas negativos: {neg_deltas} ({neg_deltas/len(deltas)*100:.1f}%)")
print(f"   Media |delta|:    {avg_abs_delta:.2f}%")
print(f"   {'BALANCEADO' if abs(pos_deltas - neg_deltas) < len(deltas) * 0.2 else 'DESBALANCEADO'}")

big_jumps = [(seq_keys[i+1], d) for i, d in enumerate(deltas) if abs(d) > 60]
if big_jumps:
    print(f"\n   Saltos grandes (|delta| > 60%):")
    for puzzle, d in big_jumps:
        print(f"     Puzzle #{puzzle}: {d:+.2f}%")

# --- BIP32 DERIVATION CHECK ---
print(f"\n{'='*60}")
print("8. TESTE DE DERIVACAO DETERMINISTICA")
print(f"{'='*60}")

# Check if keys could be sequential HMAC-derived
# In BIP32, child keys = parent_key + HMAC(chain_code, data)
# If deterministic, differences between consecutive keys should show patterns
key_diffs = []
for i in range(1, len(seq_keys)):
    if seq_keys[i] - seq_keys[i-1] == 1:
        k1 = SOLVED_PUZZLES[seq_keys[i-1]]
        k2 = SOLVED_PUZZLES[seq_keys[i]]
        # Normalize both to same bit range for comparison
        pos1 = norm_pos(seq_keys[i-1], k1)
        pos2 = norm_pos(seq_keys[i], k2)
        key_diffs.append((seq_keys[i], pos2 - pos1))

# Check for modular relationship
print("   Diferenca de posicao normalizada entre puzzles consecutivos:")
print("   (se deterministica, pode haver padrao modular)")
print()
for puzzle, diff in key_diffs[-20:]:
    bar_pos = int((diff + 1) * 25)
    bar = " " * max(0, bar_pos) + "|"
    print(f"     #{puzzle:3d}: {diff:+.4f}  {bar}")

# --- PERIODIC PATTERNS ---
print(f"\n{'='*60}")
print("9. BUSCA DE PERIODICIDADE (FFT simplificada)")
print(f"{'='*60}")

# DFT on positions to find dominant frequencies
N = len(seq_pos)
magnitudes = []
for k in range(1, N // 2):
    re = sum(seq_pos[n_i] * math.cos(2 * math.pi * k * n_i / N) for n_i in range(N))
    im = sum(seq_pos[n_i] * math.sin(2 * math.pi * k * n_i / N) for n_i in range(N))
    mag = math.sqrt(re**2 + im**2) / N
    period = N / k
    magnitudes.append((k, mag, period))

magnitudes.sort(key=lambda x: x[1], reverse=True)
print("   Top 10 frequencias dominantes:")
for k, mag, period in magnitudes[:10]:
    bar = "#" * int(mag / 2)
    print(f"     freq={k:3d}  periodo={period:6.1f}  magnitude={mag:7.2f}  {bar}")

# --- SUMMARY ---
print(f"\n{'='*80}")
print("RESUMO FINAL")
print(f"{'='*80}")

anomalies = []
if abs(avg_pos - 50) > 5:
    anomalies.append(f"Media de posicao ({avg_pos:.1f}%) desvia de 50%")
if abs(z_runs) > 1.96:
    anomalies.append(f"Teste de runs rejeita aleatoriedade (Z={z_runs:.2f})")
if abs(avg_hw - 50) > 5:
    anomalies.append(f"Hamming weight medio ({avg_hw:.1f}%) desvia de 50%")
for k, mag, period in magnitudes[:3]:
    if mag > max(m for _, m, _ in magnitudes) * 0.8:
        anomalies.append(f"Frequencia dominante com periodo {period:.1f}")

if anomalies:
    print("\n   ANOMALIAS ENCONTRADAS:")
    for a in anomalies:
        print(f"   [!] {a}")
else:
    print("\n   Nenhuma anomalia estatistica significativa detectada.")
    print("   As chaves se comportam como valores pseudo-aleatorios")
    print("   dentro de seus respectivos ranges.")

print(f"\n   CONCLUSAO SOBRE PADROES DE GERACAO:")
print(f"   - Posicao media: {avg_pos:.1f}% ({'centrada' if abs(avg_pos-50) < 5 else 'desviada'})")
print(f"   - Autocorrelacao lag-1: {corr:.4f} ({'fraca' if abs(corr) < 0.1 else 'presente'})")
print(f"   - Distribuicao: {'uniforme' if abs(z_runs) < 1.96 else 'nao uniforme'}")
print(f"   - Os dados sao {'consistentes' if len(anomalies) == 0 else 'parcialmente consistentes'}")
print(f"     com geracao via wallet HD (BIP32) mascarada por bit range.")
print()
