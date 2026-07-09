"""
A2 na secp256k1 REAL por amostragem — empurra a escala da janela até 2^40 (e além).

Enumerar a órbita é impossível em 2^40 (16 TB, cadeia sequencial). Em vez disso:
  - amostramos S chaves k numa janela [0, R), R = 2^w;
  - computamos P_k = k*G na secp256k1 real (mult. escalar Jacobiana, sem armazenar a órbita);
  - rodamos os detectores na AMOSTRA (resolução vem de S, não de R).

Testa A2 DIRETAMENTE na curva-alvo, em janelas largas, com controle positivo.
GPU não se aplica (256 bits exige CUDA multi-limb caseiro); roda em CPU, viável por amostragem.

Detectores (para um funcional g(P)):
  - fase: máx_m (corr_cos^2+corr_sin^2)*S  ~ chi2(2) sob nulo (m=1..M, harmônicos de k/R)
  - MI(bin(g); bit de k)
  - sep: |média(g|bit=1)-média(g|bit=0)|/std(g)
Controles positivos disparam por construção.

Python stdlib puro.
"""
import sys, math, random
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# secp256k1
P  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
Nn = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8

# ---- secp256k1 em coordenadas Jacobianas (sem inversões durante a mult.) ----
def jdouble(Pt):
    X1, Y1, Z1 = Pt
    if Y1 == 0 or Z1 == 0:
        return (0, 0, 0)
    A = (X1*X1) % P
    B = (Y1*Y1) % P
    C = (B*B) % P
    D = (2*(((X1+B)*(X1+B) - A - C) % P)) % P
    E = (3*A) % P
    F = (E*E) % P
    X3 = (F - 2*D) % P
    Y3 = (E*(D - X3) - 8*C) % P
    Z3 = (2*Y1*Z1) % P
    return (X3, Y3, Z3)

def jadd(Pt, Qt):
    X1, Y1, Z1 = Pt
    X2, Y2, Z2 = Qt
    if Z1 == 0: return Qt
    if Z2 == 0: return Pt
    Z1Z1 = (Z1*Z1) % P
    Z2Z2 = (Z2*Z2) % P
    U1 = (X1*Z2Z2) % P
    U2 = (X2*Z1Z1) % P
    S1 = (Y1*Z2*Z2Z2) % P
    S2 = (Y2*Z1*Z1Z1) % P
    if U1 == U2:
        if S1 != S2:
            return (0, 0, 0)
        return jdouble(Pt)
    H = (U2 - U1) % P
    I = ((2*H) % P)**2 % P
    J = (H*I) % P
    r = (2*(S2 - S1)) % P
    V = (U1*I) % P
    X3 = (r*r - J - 2*V) % P
    Y3 = (r*(V - X3) - 2*S1*J) % P
    Z3 = (((Z1+Z2)*(Z1+Z2) - Z1Z1 - Z2Z2) * H) % P
    return (X3, Y3, Z3)

Gj = (Gx, Gy, 1)

def scalar_mul(k):
    R = (0, 0, 0)
    Q = Gj
    while k > 0:
        if k & 1:
            R = jadd(R, Q)
        Q = jdouble(Q)
        k >>= 1
    return R

def batch_affine(points):
    """Converte lista de pontos Jacobianos para x,y afim com UMA inversão (Montgomery)."""
    n = len(points)
    zs = [pt[2] for pt in points]
    pref = [1]*(n+1)
    for i in range(n):
        pref[i+1] = (pref[i] * (zs[i] if zs[i] != 0 else 1)) % P
    inv_all = pow(pref[n], P-2, P)
    xs = [0]*n; ys = [0]*n
    for i in range(n-1, -1, -1):
        zi = zs[i] if zs[i] != 0 else 1
        zinv = (inv_all * pref[i]) % P
        inv_all = (inv_all * zi) % P
        z2 = (zinv*zinv) % P
        z3 = (z2*zinv) % P
        xs[i] = (points[i][0] * z2) % P
        ys[i] = (points[i][1] * z3) % P
    return xs, ys

def legendre(a):
    a %= P
    if a == 0: return 0
    return 1 if pow(a, (P-1)//2, P) == 1 else -1

# ---- detectores na amostra ----
def phase_max(g, ks, R, M):
    n = len(g)
    mg = sum(g)/n
    a = [v-mg for v in g]
    na2 = sum(v*v for v in a) or 1.0
    best, bm = 0.0, 0
    for m in range(1, M+1):
        w = 2*math.pi*m/R
        c = 0.0; s = 0.0
        for i in range(n):
            ang = w*ks[i]
            c += a[i]*math.cos(ang); s += a[i]*math.sin(ang)
        z = 2.0*(c*c+s*s)/na2
        if z > best: best, bm = z, m
    return best, bm

def mutual_info(g, bits, nbins=8):
    n = len(g)
    lo = min(g); hi = max(g)
    if hi == lo: return 0.0
    from collections import Counter
    width = (hi-lo)/nbins
    joint = Counter(); bg = Counter(); bb = Counter()
    for v, bit in zip(g, bits):
        gi = min(nbins-1, int((v-lo)/width))
        joint[(gi,bit)] += 1; bg[gi]+=1; bb[bit]+=1
    I = 0.0
    for (gi,bit), c in joint.items():
        pxy=c/n; px=bg[gi]/n; py=bb[bit]/n
        if pxy>0: I += pxy*math.log2(pxy/(px*py))
    return I

def separation(g, bits):
    n = len(g)
    n1 = sum(bits); n0 = n-n1
    if n1==0 or n0==0: return 0.0
    s1 = sum(g[i] for i in range(n) if bits[i])
    s0 = sum(g) - s1
    m1 = s1/n1; m0 = s0/n0
    mg = sum(g)/n
    sd = math.sqrt(sum((v-mg)**2 for v in g)/n) or 1.0
    return abs(m1-m0)/sd

def run_window(w, S, M, seed=1):
    R = 1 << w
    rng = random.Random(seed*1000+w)
    ks = [rng.randrange(0, R) for _ in range(S)]
    pts = [scalar_mul(k) for k in ks]
    xs, ys = batch_affine(pts)

    MASK = (1 << 52) - 1
    F = {
        "x(low52)":  [x & MASK for x in xs],
        "lsb(x)":    [x & 1 for x in xs],
        "leg(x)":    [legendre(x) for x in xs],
        "x*y(low52)":[((xs[i]*ys[i]) % P) & MASK for i in range(S)],
        "x(hi)":     [x >> 204 for x in xs],
    }
    lsb_k = [k & 1 for k in ks]
    msb_k = [1 if k >= R//2 else 0 for k in ks]

    cph = cmi = csp = 0.0
    for arr in F.values():
        ph,_ = phase_max([float(v) for v in arr], ks, R, M)
        mi = max(mutual_info(arr, lsb_k), mutual_info(arr, msb_k))
        sp = separation([float(v) for v in arr], lsb_k)
        cph=max(cph,ph); cmi=max(cmi,mi); csp=max(csp,sp)

    # controles positivos (na MESMA amostra)
    ramp = [float(k) for k in ks]                 # = k -> fase m=1
    lsbk = [k & 1 for k in ks]                     # = LSB(k) -> MI=1
    rph,_ = phase_max(ramp, ks, R, M)
    lmi = mutual_info(lsbk, lsb_k)
    return R, cph, cmi, csp, rph, lmi

if __name__ == "__main__":
    # validação rápida da aritmética
    x1,y1 = batch_affine([scalar_mul(1)]);
    assert x1[0]==Gx and y1[0]==Gy, "scalar_mul(1) != G"
    x2,_ = batch_affine([scalar_mul(2)])
    assert x2[0]==0xC6047F9441ED7D6D3045406E95C07CD85C778E4B8CEF3CA7ABAC09B95C709EE5, "2G x errado"
    print("  [ok] aritmética secp256k1 validada (1G e 2G conferem)")

    windows = [int(a) for a in sys.argv[1:]] or [20, 30, 40]
    S = 40000; M = 16
    print("=" * 90)
    print(f"A2 na secp256k1 REAL por amostragem | S={S} amostras/janela, M={M} harmônicos")
    print("=" * 90)
    print(f"\n  {'janela':>8} | {'CURVA: máx detectores':^28} | {'CONTROLES':^18}")
    print(f"  {'2^w':>8} | {'fase':>9} {'MI':>9} {'sep':>7} | {'fase':>9} {'MI':>7}")
    print(f"  {'-'*8} | {'-'*9} {'-'*9} {'-'*7} | {'-'*9} {'-'*7}")

    rows = []
    for w in windows:
        R, cph, cmi, csp, rph, lmi = run_window(w, S, M)
        rows.append((w, cph, cmi, csp, rph, lmi))
        print(f"  2^{w:<6} | {cph:>9.1f} {cmi:>9.4f} {csp:>7.4f} | {rph:>9.0f} {lmi:>7.4f}")

    print(f"\n{'='*90}")
    print("LEITURA")
    print(f"{'='*90}")
    noise = 2*math.log(M) + 8   # teto grosseiro p/ máx de M qui-quadrados(2)
    silent = all(r[1] < 40 and r[2] < 0.01 and r[3] < 0.05 for r in rows)
    ctrl_ok = all(r[4] > 1000 and r[5] > 0.5 for r in rows)
    print(f"  Curva silenciosa em TODAS as janelas (até 2^{max(windows)}): {'sim' if silent else 'NÃO'}")
    print(f"  Controles dispararam em TODAS as janelas: {'sim' if ctrl_ok else 'NÃO'}")
    if silent and ctrl_ok:
        print(f"""
  A2 corroborada na secp256k1 REAL, em janelas até 2^{max(windows)}, com amostra fixa S={S}.
  Resolução do teste = sqrt(S) ~ {math.sqrt(S):.0f}; nenhum funcional correlaciona com a fase
  de k acima do acaso, enquanto os controles (na mesma amostra) disparam ordens de grandeza
  acima. Largura da janela não cria sinal — exatamente o que A2 prevê.""")
    elif not ctrl_ok:
        print("\n  Controles não dispararam — revisar (teste inconclusivo).")
    else:
        print("\n  >>> ALGUM detector da curva disparou — investigar lead.")
