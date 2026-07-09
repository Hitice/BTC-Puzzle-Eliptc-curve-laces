"""
EXPERIMENTO DE INCOMPRESSIBILIDADE DA ÓRBITA
(operacionaliza A2: "a fase de k é uma sombra computável das coordenadas de P?")

Reformulação (não é mais "log discreto"): a órbita {kG} é incompressível sob uma
classe ampla de observáveis computáveis? Se alguma rachadura existir, aparece PRIMEIRO
como compressibilidade estatística — correlação de algum funcional g(P) com a fase de k.

A2 vira FALSIFICÁVEL em três formas mensuráveis, para um funcional g: E(F_p) -> R:
  (i)   corr(g(P_k), e^{2πi m k/N}) desprezível para todo harmônico m pequeno
  (ii)  I(g(P_k); bit de k) = o(1)
  (iii) Pr[g prevê um bit de k] <= 1/2 + ε
+ um detector dinâmico (sugestão do revisor): a distribuição de Δ_k = g(P_{k+1}) - g(P_k).

Curva: y^2 = x^3 + 7 (forma secp256k1) sobre F_p pequeno, ORDEM PRIMA (computo k de tudo).
CONTROLE POSITIVO: sequências com estrutura conhecida — os detectores DEVEM disparar nelas,
senão um nulo na curva não significa nada.

Python stdlib puro.
"""
import math
import sys
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---------- aritmética de curva (toy) ----------
def legendre(a, p):
    a %= p
    if a == 0: return 0
    return 1 if pow(a, (p - 1) // 2, p) == 1 else -1

def count_order(p):
    # #E(F_p) para y^2 = x^3 + 7
    s = 0
    for x in range(p):
        s += legendre((x * x * x + 7) % p, p)
    return p + 1 + s

def is_prime(n):
    if n < 2: return False
    for q in (2,3,5,7,11,13,17,19,23,29,31,37):
        if n % q == 0: return n == q
    d = n - 1; r = 0
    while d % 2 == 0: d //= 2; r += 1
    for a in (2,3,5,7,11,13,17,19,23,29,31,37):
        x = pow(a, d, n)
        if x in (1, n-1): continue
        for _ in range(r-1):
            x = x*x % n
            if x == n-1: break
        else:
            return False
    return True

def find_prime_curve(p_start, p_end):
    p = p_start | 1
    while p < p_end:
        if is_prime(p) and p not in (3, 7):
            N = count_order(p)
            if is_prime(N):
                return p, N
        p += 2
    raise RuntimeError("nenhuma curva de ordem prima no intervalo")

def inv(a, p): return pow(a, p - 2, p)

def padd(A, B, p):
    if A is None: return B
    if B is None: return A
    x1, y1 = A; x2, y2 = B
    if x1 == x2 and (y1 + y2) % p == 0: return None
    if A == B:
        s = (3 * x1 * x1) * inv(2 * y1, p) % p
    else:
        s = (y2 - y1) * inv((x2 - x1) % p, p) % p
    x3 = (s * s - x1 - x2) % p
    return (x3, (s * (x1 - x3) - y1) % p)

def sqrt_mod(a, p):
    """Raiz quadrada modular (Tonelli-Shanks), geral para p ímpar primo."""
    a %= p
    if a == 0: return 0
    if pow(a, (p - 1) // 2, p) != 1: return None
    if p % 4 == 3: return pow(a, (p + 1) // 4, p)
    q = p - 1; s = 0
    while q % 2 == 0: q //= 2; s += 1
    z = 2
    while pow(z, (p - 1) // 2, p) != p - 1: z += 1
    m = s; c = pow(z, q, p); t = pow(a, q, p); r = pow(a, (q + 1) // 2, p)
    while t != 1:
        i = 0; tt = t
        while tt != 1:
            tt = tt * tt % p; i += 1
        b = pow(c, 1 << (m - i - 1), p)
        m = i; c = b * b % p; t = t * c % p; r = r * b % p
    return r

def find_generator(p):
    for x in range(1, p):
        rhs = (x*x*x + 7) % p
        if legendre(rhs, p) == 1:
            y = sqrt_mod(rhs, p)
            if y is not None and (y*y) % p == rhs:
                return (x, y)
    raise RuntimeError("sem gerador")

# ---------- detectores (estatística rápida, calibrada) ----------
def center(a):
    m = sum(a) / len(a)
    return [v - m for v in a], m

def norm(a):
    return math.sqrt(sum(v*v for v in a)) or 1.0

def phase_power(arr, N, M):
    """Maior 'potência' nos harmônicos m=1..M (combinação cos/sin).
    Sob nulo (sem estrutura), potência ~ chi2(2)/2; reportamos o máximo z-like."""
    a, _ = center([float(v) for v in arr])
    na = norm(a)
    if na == 0: return 0.0, 0
    best, bestm = 0.0, 0
    for m in range(1, M + 1):
        c = 0.0; s = 0.0
        w = 2 * math.pi * m / N
        for k in range(N):
            ang = w * k
            c += a[k] * math.cos(ang)
            s += a[k] * math.sin(ang)
        # corr_cos = c/(na*sqrt(N/2)); potência = (corr_cos^2+corr_sin^2)*(N/2)... ~ chi2(2)
        power = 2.0 * (c*c + s*s) / (na*na * N)   # ~ corr^2 somado, escala [0..1]
        z = power * N  # vira ~ qui-quadrado(2): E=2 sob nulo; grande = sinal
        if z > best: best, bestm = z, m
    return best, bestm

def mutual_info_bit(arr, bits, nbins=8):
    """I(bin(g); bit) em bits. Null ~ 0; calculamos excesso."""
    a = [float(v) for v in arr]
    lo, hi = min(a), max(a)
    if hi == lo: return 0.0
    width = (hi - lo) / nbins
    def b(v):
        i = int((v - lo) / width)
        return nbins - 1 if i >= nbins else i
    N = len(a)
    joint = Counter(); bg = Counter(); bb = Counter()
    for v, bit in zip(a, bits):
        gi = b(v)
        joint[(gi, bit)] += 1; bg[gi] += 1; bb[bit] += 1
    I = 0.0
    for (gi, bit), c in joint.items():
        pxy = c / N; px = bg[gi] / N; py = bb[bit] / N
        if pxy > 0:
            I += pxy * math.log2(pxy / (px * py))
    return I  # bits

def bit_pred_adv(arr, bits):
    """Melhor acurácia prevendo 'bit' por um único limiar em g, menos 0.5.
    Varre o ponto de corte; testa as duas polaridades."""
    pairs = sorted(zip([float(v) for v in arr], bits), key=lambda t: t[0])
    n = len(pairs)
    total_ones = sum(bits)
    best = max(total_ones, n - total_ones) / n   # baseline: prever a maioria
    ones_below = 0
    for i in range(n):
        ones_below += pairs[i][1]
        # só avalia em FRONTEIRA entre valores distintos de g (empates não são separáveis)
        if i == n - 1 or pairs[i][0] != pairs[i + 1][0]:
            below = i + 1
            zeros_below = below - ones_below
            ones_above = total_ones - ones_below
            zeros_above = (n - below) - ones_above
            accA = (zeros_below + ones_above) / n   # prediz 0 abaixo, 1 acima
            accB = (ones_below + zeros_above) / n   # prediz 1 abaixo, 0 acima
            if accA > best: best = accA
            if accB > best: best = accB
    return best - 0.5

def delta_smoothness(arr, N):
    """var(Δ_k) / (2 var(g)). ~1 se aleatório; <<1 se há suavidade na sucessão."""
    a = [float(v) for v in arr]
    m = sum(a)/N
    var = sum((v-m)**2 for v in a)/N
    if var == 0: return 1.0
    d = [a[(k+1) % N] - a[k] for k in range(N)]
    vard = sum(x*x for x in d)/N  # média de Δ ~0
    return vard / (2*var)

# ---------- bateria de funcionais ----------
def build_functionals(X, Y, p, N):
    F = {}
    F["x"] = X
    F["y"] = Y
    F["x+y"] = [(X[k] + Y[k]) % p for k in range(N)]
    F["x*y"] = [(X[k] * Y[k]) % p for k in range(N)]
    F["x^2+y^2"] = [(X[k]*X[k] + Y[k]*Y[k]) % p for k in range(N)]
    F["legendre(x)"] = [legendre(X[k], p) for k in range(N)]
    F["legendre(y)"] = [legendre(Y[k], p) for k in range(N)]
    F["lsb(x)"] = [X[k] & 1 for k in range(N)]
    F["lsb(y)"] = [Y[k] & 1 for k in range(N)]
    # caminhadas pequenas: x(mP_k) = X[(m k) mod N]
    for m in (2, 3, 5, 7):
        F[f"x({m}P)"] = [X[(m*k) % N] for k in range(N)]
    return F

def run_detectors(name, arr, N, lsb_k, msb_k, M):
    pw, pm = phase_power(arr, N, M)
    mi_lsb = mutual_info_bit(arr, lsb_k)
    mi_msb = mutual_info_bit(arr, msb_k)
    adv = bit_pred_adv(arr, lsb_k)
    dsm = delta_smoothness(arr, N)
    # flags (limiares conservadores p/ Bonferroni com ~15 funcionais x M harmônicos)
    fires = (pw > 40) or (mi_lsb > 0.01) or (mi_msb > 0.01) or (adv > 0.05) or (dsm < 0.7)
    return dict(name=name, phase=pw, pm=pm, mi_lsb=mi_lsb, mi_msb=mi_msb,
                adv=adv, delta=dsm, fires=fires)

def fmt(r):
    flag = "  <<< DISPARA" if r["fires"] else ""
    return (f"  {r['name']:>12} | fase z={r['phase']:7.1f}(m={r['pm']:>2}) | "
            f"MI_lsb={r['mi_lsb']:.4f} MI_msb={r['mi_msb']:.4f} | "
            f"adv={r['adv']:+.4f} | Δ={r['delta']:.3f}{flag}")

if __name__ == "__main__":
    print("=" * 78)
    print("INCOMPRESSIBILIDADE DA ÓRBITA — A2 como hipótese mensurável")
    print("=" * 78)

    print("\n  Procurando curva y^2=x^3+7 de ordem prima...")
    p, N = find_prime_curve(20011, 80000)
    G = find_generator(p)
    print(f"    p = {p} | N = #E = {N} (primo) | G = {G}")

    # construir órbita P_k = kG, k=0..N-1
    print("  Construindo a órbita inteira (k -> kG)...")
    X = [0]*N; Y = [0]*N
    P = None
    for k in range(N):
        if k == 0:
            X[0], Y[0] = 0, 0     # identidade (sentinela)
        else:
            P = padd(P, G, p) if P is not None else G
            X[k], Y[k] = P
    # remove k=0 (infinito) das análises: trabalhamos k=1..N-1
    Xa = X[1:]; Ya = Y[1:]; Na = N - 1
    lsb_k = [k & 1 for k in range(1, N)]
    msb_k = [1 if k >= N//2 else 0 for k in range(1, N)]
    M = 24

    # ---------- CONTROLE POSITIVO: detectores DEVEM disparar ----------
    print(f"\n  [CONTROLE POSITIVO] sequências com estrutura conhecida (k=1..{Na}):")
    pc = {}
    pc["LSB(k) puro"]   = [k & 1 for k in range(1, N)]
    pc["rampa k/N"]     = [k for k in range(1, N)]
    pc["3k mod N"]      = [(3*k) % N for k in range(1, N)]
    pc["cos(2π·4k/N)"]  = [int(1000*math.cos(2*math.pi*4*k/N)) for k in range(1, N)]
    for nm, seq in pc.items():
        print(fmt(run_detectors(nm, seq, Na, lsb_k, msb_k, M)))

    # ---------- CURVA REAL: A2 prevê SILÊNCIO ----------
    print(f"\n  [CURVA y^2=x^3+7] funcionais sobre os pontos públicos (k=1..{Na}):")
    F = build_functionals(Xa, Ya, p, Na)
    results = []
    for nm, arr in F.items():
        r = run_detectors(nm, arr, Na, lsb_k, msb_k, M)
        results.append(r)
        print(fmt(r))

    n_fire = sum(1 for r in results if r["fires"])
    pc_fire = sum(1 for nm, seq in pc.items()
                  if run_detectors(nm, seq, Na, lsb_k, msb_k, M)["fires"])

    print(f"\n{'='*78}")
    print("VEREDITO")
    print(f"{'='*78}")
    print(f"  Controles positivos que dispararam: {pc_fire}/{len(pc)} "
          f"({'OK — detectores funcionam' if pc_fire >= 3 else 'FALHA — detectores cegos'})")
    print(f"  Funcionais da curva que dispararam: {n_fire}/{len(results)}")
    if n_fire == 0 and pc_fire >= 3:
        print("""
  RESULTADO: evidência QUANTITATIVA de incompressibilidade.
  Nenhum funcional da classe testada correlaciona com a fase de k acima do acaso,
  ENQUANTO os controles positivos disparam — logo o silêncio é informativo, não cegueira.
  Isto substitui "ninguém achou" (sociológico) por "testamos N funcionais x M harmônicos
  + MI + predição de bit + suavidade-Δ, todos compatíveis com o acaso" (experimental).
  A2 sobrevive como hipótese AGORA mensurável e corroborada nesta escala.""")
    elif n_fire > 0:
        print("""
  RESULTADO: ALGUM funcional disparou na curva. Investigar — pode ser artefato de
  tamanho pequeno (checar se persiste ao crescer N) ou um lead real de compressibilidade.""")
    else:
        print("\n  Detectores não validados (controles não dispararam). Revisar limiares.")
