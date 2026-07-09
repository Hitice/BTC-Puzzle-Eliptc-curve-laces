"""
"E se eu estiver errado?" - teste de robustez das nossas conclusoes negativas.

Conclusao negativa so vale se tivermos PODER para detectar o efeito.
Aqui medimos exatamente isso:

  1. INSPECAO DIRETA das chaves iniciais (olho, nao estatistica agregada)
  2. CHANGE-POINT: os dados mudam de comportamento em algum puzzle? (sem impor corte)
  3. ANALISE DE PODER: injetar padroes de forca conhecida e medir taxa de deteccao.
     -> diz o EFEITO MINIMO DETECTAVEL: abaixo dele, estariamos cegos (e tudo bem
        admitir isso explicitamente).
"""
import json
import os
import math
import random
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

with open(os.path.join(DATA, "puzzles.json")) as f:
    PUZZLES = json.load(f)["puzzles"]

SOLVED = {p["puzzle"]: p["privkey_int"] for p in PUZZLES if p["status"] == "solved"}
POS = {p["puzzle"]: p["position_in_range"] for p in PUZZLES if p["status"] == "solved"}

def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def autocorr(series, lag):
    n = len(series)
    m = sum(series) / n
    v = sum((a - m) ** 2 for a in series)
    if v == 0:
        return 0
    return sum((series[i] - m) * (series[i + lag] - m) for i in range(n - lag)) / v

# ============================================================
# 1. INSPECAO DIRETA DAS CHAVES INICIAIS
# ============================================================
print("=" * 72)
print("1. INSPECAO DIRETA #1-25 (procurando padrao humano a olho)")
print("=" * 72)
print(f"\n  {'#':>3}  {'dec':>12}  {'hex':>14}  {'binario':>20}  {'pos%':>6}")
print(f"  {'-'*3}  {'-'*12}  {'-'*14}  {'-'*20}  {'-'*6}")
for n in range(1, 26):
    if n not in SOLVED:
        continue
    k = SOLVED[n]
    print(f"  {n:>3}  {k:>12}  {format(k,'x'):>14}  {format(k,'b'):>20}  {POS[n]*100:>5.1f}")

# checagens automaticas de padrao exato nos primeiros
print(f"\n  Checagens de relacoes exatas (#1-15):")
small = [SOLVED[n] for n in range(1, 16) if n in SOLVED]
# diferencas consecutivas
diffs = [small[i+1] - small[i] for i in range(len(small)-1)]
print(f"    diffs consecutivas: {diffs}")
print(f"    todas positivas (monotonico crescente)? {all(d > 0 for d in diffs)}")
# alguma chave = 2^k - 1 (all ones)?
allones = [n for n in range(1,16) if n in SOLVED and (SOLVED[n] & (SOLVED[n]+1)) == 0]
print(f"    chaves que sao 2^k-1 (so uns em binario): {allones}")
# alguma chave primo?
def is_prime(x):
    if x < 2: return False
    for i in range(2, int(x**0.5)+1):
        if x % i == 0: return False
    return True
primes = [n for n in range(1,16) if n in SOLVED and is_prime(SOLVED[n])]
print(f"    chaves que sao primos: {primes}")

# ============================================================
# 2. CHANGE-POINT DETECTION
# ============================================================
print(f"\n{'='*72}")
print("2. CHANGE-POINT: a geracao muda de comportamento em algum ponto?")
print("   (testa TODO corte possivel; os dados decidem, nao eu)")
print(f"{'='*72}")

seq = sorted(POS.keys())
pos_seq = [POS[n] * 100 for n in seq]
N = len(pos_seq)

# Para cada corte b, |media(antes) - media(depois)|, com p-value por permutacao
print(f"\n  Maior diferenca de media de posicao entre 'antes' e 'depois' do corte:")
random.seed(11)
N_PERM = 50_000

best = []
for b in range(5, N - 5):
    before = pos_seq[:b]
    after = pos_seq[b:]
    stat = abs(sum(before)/len(before) - sum(after)/len(after))
    best.append((stat, b, seq[b]))

best.sort(reverse=True)
top_stat, top_b, top_puzzle = best[0]

# p-value do MAIOR salto, corrigido por ter testado todos os cortes (max-stat permutation)
exceed = 0
for _ in range(N_PERM):
    perm = pos_seq[:]
    random.shuffle(perm)
    maxstat = 0
    for b in range(5, N - 5):
        bef = perm[:b]; aft = perm[b:]
        s = abs(sum(bef)/len(bef) - sum(aft)/len(aft))
        if s > maxstat:
            maxstat = s
    if maxstat >= top_stat:
        exceed += 1
p_cp = exceed / N_PERM

print(f"    Maior salto: corte no puzzle #{top_puzzle} (indice {top_b})")
print(f"    Diferenca de media: {top_stat:.2f}%")
print(f"    P-value (corrigido p/ multiplos cortes): {p_cp:.4f}")
print(f"    {'MUDANCA REAL detectada!' if p_cp < 0.05 else 'Nenhuma mudanca de regime. Geracao homogenea.'}")

# ============================================================
# 3. ANALISE DE PODER - o coracao da resposta
# ============================================================
print(f"\n{'='*72}")
print("3. ANALISE DE PODER: se houvesse padrao, teriamos visto?")
print(f"{'='*72}")

# --- 3a. Poder para autocorrelacao (AR1) ---
print(f"\n  [3a] AUTOCORRELACAO - quao forte precisa ser p/ detectarmos 80% das vezes?")
threshold = 1.96 / math.sqrt(N)  # limite de Bartlett
print(f"       (N={N}, limiar de deteccao |r|>{threshold:.3f})")
random.seed(1)
N_PW = 20_000
print(f"       {'rho real':>9}  {'taxa de deteccao':>16}")
mde_ac = None
for rho in [0.1, 0.2, 0.25, 0.3, 0.4, 0.5]:
    s = math.sqrt(1 - rho*rho)
    detect = 0
    for _ in range(N_PW):
        x = random.gauss(0, 1)
        ser = []
        for _ in range(N):
            x = rho * x + s * random.gauss(0, 1)
            ser.append(norm_cdf(x))
        if abs(autocorr(ser, 1)) > threshold:
            detect += 1
    rate = detect / N_PW
    if mde_ac is None and rate >= 0.80:
        mde_ac = rho
    print(f"       {rho:>9.2f}  {rate:>15.1%}")
print(f"       -> Efeito minimo detectavel (80% poder): rho ~ {mde_ac if mde_ac else '>0.5'}")
print(f"       -> ABAIXO disso, uma autocorrelacao real passaria despercebida.")

# --- 3b. Poder para bias modular ---
print(f"\n  [3b] BIAS MODULAR - quantas chaves 'viciadas' p/ detectarmos? (mod 23)")
ranges = [(1 << (n-1), (1 << n) - 1) for n in SOLVED if n >= 30]
n_big = len(ranges)
forbidden = set(range(12, 23))  # gerador que evita metade dos residuos
alpha_bonf = 0.05 / 14
# chi2 critico aproximado para df=22 a alpha_bonf (~0.0036): ~ 45
def chi2_mod(keys, p):
    counts = Counter(k % p for k in keys)
    exp = len(keys) / p
    return sum((counts.get(r,0)-exp)**2/exp for r in range(p))
# calibrar limiar por MC sob nulo
random.seed(3)
null = sorted(chi2_mod([random.randint(lo,hi) for lo,hi in ranges], 23) for _ in range(20000))
crit = null[int(0.20000*20000)] if False else null[int((1-alpha_bonf)*20000)]
print(f"       (n={n_big} chaves grandes, limiar chi2>{crit:.1f} p/ Bonferroni)")
print(f"       {'% viciado':>9}  {'taxa de deteccao':>16}")
mde_mod = None
for frac in [0.1, 0.2, 0.3, 0.5, 0.7]:
    detect = 0
    for _ in range(5000):
        keys = []
        for lo, hi in ranges:
            k = random.randint(lo, hi)
            if random.random() < frac:
                # forcar residuo permitido (gerador viciado)
                while k % 23 in forbidden:
                    k = random.randint(lo, hi)
            keys.append(k)
        if chi2_mod(keys, 23) > crit:
            detect += 1
    rate = detect / 5000
    if mde_mod is None and rate >= 0.80:
        mde_mod = frac
    print(f"       {frac:>8.0%}  {rate:>15.1%}")
print(f"       -> Minimo detectavel (80%): ~{int(mde_mod*100) if mde_mod else '>70'}% das chaves viciadas")

# --- 3c. Poder para subconjunto com padrao (ponto do usuario) ---
print(f"\n  [3c] SUBCONJUNTO com geracao diferente - quantos p/ detectarmos?")
print(f"       (m chaves forcadas ao terco inferior do range, resto aleatorio)")
random.seed(5)
base_mean = 50.0
# limiar: desvio da media de posicao detectavel via z (1 amostra de N)
print(f"       {'m chaves':>9}  {'taxa de deteccao':>16}")
mde_sub = None
for m in [3, 5, 8, 12, 20]:
    detect = 0
    for _ in range(10000):
        pos = []
        for i in range(N):
            if i < m:
                pos.append(random.uniform(0, 1/3) * 100)  # terco inferior
            else:
                pos.append(random.uniform(0, 1) * 100)
        mean = sum(pos)/N
        se = (sum((p-mean)**2 for p in pos)/N)**0.5 / math.sqrt(N)
        z = (mean - 50) / se if se > 0 else 0
        if abs(z) > 1.96:
            detect += 1
    rate = detect/10000
    if mde_sub is None and rate >= 0.80:
        mde_sub = m
    print(f"       {m:>9}  {rate:>15.1%}")
print(f"       -> Minimo detectavel (80%): ~{mde_sub if mde_sub else '>20'} de {N} chaves")

# ============================================================
# VEREDITO HONESTO
# ============================================================
print(f"\n{'='*72}")
print("VEREDITO HONESTO - os limites do que afirmamos")
print(f"{'='*72}")
print(f"""
  O que PODEMOS afirmar com confianca (temos poder p/ detectar):
    - Autocorrelacao com rho >~ {mde_ac if mde_ac else 0.3}: NAO existe.
    - Bias modular afetando >~{int(mde_mod*100) if mde_mod else 50}% das chaves: NAO existe.
    - Subconjunto de >~{mde_sub if mde_sub else 12} chaves com geracao diferente: NAO existe.
    - Change-point / mudanca de regime: {'detectado' if p_cp < 0.05 else 'NAO existe'}.
    - LCG, passo linear, bias de bit: descartados (rodadas anteriores).

  O que NAO podemos descartar (zona cega - voce PODE estar certo aqui):
    - Padroes sutis abaixo dos efeitos minimos acima.
    - Padrao complexo nao-linear que nenhum teste especifico cobriu.
    - Estrutura visivel so com a SEED original (ex: BIP32 c/ chaincode).
    - Geracao humana nos primeiros ~3-4 (#1=1,#2=3,#3=7) - plausivel,
      mas IRRELEVANTE: resolvidos e nao preditivos dos grandes.

  Conclusao: nossas negativas sao fortes para padroes FORTES e MEDIOS.
  Um padrao FRACO o suficiente para sobreviver teria de afetar poucas
  chaves ou ser sutil demais para reduzir o espaco de #71 (2^70) a algo
  factivel. Ou seja: mesmo se voce estiver certo, o ganho pratico seria
  pequeno demais para resolver os alvos - a menos que seja a seed/chaincode.
""")
