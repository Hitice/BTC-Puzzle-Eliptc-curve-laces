"""
Scan de relacoes entre os 6 pubkeys expostos (#135,140,145,150,155,160).
Se existir relacao simples em espaco EC, seria ESTRUTURA real (nao-generica)
e furaria o limite de Shoup. Quase certamente negativo (derivacao e hash-based),
mas e o unico cheque barato e nao-explorado que resta.

Testa:
  A. multiplicativo: Q_j = m * Q_i  para |m| pequeno  (razao de chaves privadas pequena)
  B. aditivo:        Q_j = Q_i + t*G para |t| pequeno  (diferenca de chaves pequena)
  C. negacao/identidade e Q_i = t*G para t pequeno (sanidade)

secp256k1 em Python puro (sem dependencias).
"""
import os, json

# secp256k1
P  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G  = (Gx, Gy)

def inv(x): return pow(x, P - 2, P)

def add(Pa, Pb):
    if Pa is None: return Pb
    if Pb is None: return Pa
    x1, y1 = Pa; x2, y2 = Pb
    if x1 == x2 and (y1 + y2) % P == 0:
        return None
    if Pa == Pb:
        s = (3 * x1 * x1) * inv(2 * y1) % P
    else:
        s = (y2 - y1) * inv((x2 - x1) % P) % P
    x3 = (s * s - x1 - x2) % P
    y3 = (s * (x1 - x3) - y1) % P
    return (x3, y3)

def neg(Pa):
    if Pa is None: return None
    return (Pa[0], (-Pa[1]) % P)

def mul(k, Pt):
    R = None
    while k > 0:
        if k & 1: R = add(R, Pt)
        Pt = add(Pt, Pt)
        k >>= 1
    return R

def decompress(hexstr):
    b = bytes.fromhex(hexstr)
    prefix = b[0]
    x = int.from_bytes(b[1:], 'big')
    y2 = (pow(x, 3, P) + 7) % P
    y = pow(y2, (P + 1) // 4, P)
    if (y * y) % P != y2:
        raise ValueError("nao esta na curva")
    if (y & 1) != (prefix & 1):
        y = (P - y) % P
    return (x, y)

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "..", "data", "puzzles.json")) as f:
    PUZ = json.load(f)["puzzles"]

EXPOSED = {p["puzzle"]: p["pubkey"] for p in PUZ
           if p["status"] == "unsolved" and p["pubkey"]}

print("=" * 68)
print("SCAN DE RELACOES ENTRE PUBKEYS EXPOSTOS")
print("=" * 68)

Q = {}
print("\n  Descomprimindo e validando pubkeys na curva:")
for n in sorted(EXPOSED):
    pt = decompress(EXPOSED[n])
    Q[n] = pt
    # validar: y^2 == x^3+7
    ok = (pt[1] * pt[1] - (pow(pt[0], 3, P) + 7)) % P == 0
    print(f"    #{n}: x={hex(pt[0])[:20]}...  na curva: {ok}")

nums = sorted(Q)

# ============================================================
# C. sanidade: Q_i = t*G para t pequeno?
# ============================================================
print(f"\n  [C] Sanidade - algum pubkey e multiplo pequeno de G? (t < 2^20)")
MC = 1 << 20
small_mult = {}
R = None
for t in range(1, MC):
    R = add(R, G)
    small_mult[R[0]] = t   # x-coord -> t
hits_c = []
for n in nums:
    if Q[n][0] in small_mult:
        t = small_mult[Q[n][0]]
        # confirmar sinal
        if mul(t, G) == Q[n]:
            hits_c.append((n, t))
print(f"    {'NENHUM (esperado)' if not hits_c else hits_c}")

# ============================================================
# B. aditivo: Q_j - Q_i = t*G para t pequeno?
# ============================================================
print(f"\n  [B] Aditivo - Q_j - Q_i = t*G para |t| < 2^20?")
print(f"      (detecta diferenca PEQUENA entre chaves privadas)")
# small_mult ja tem t*G para t in [1,2^20). Inclui tambem negativos via checagem de -D.
hits_b = []
for i in nums:
    for j in nums:
        if i >= j: continue
        D = add(Q[j], neg(Q[i]))   # (k_j - k_i)*G
        if D is None:
            hits_b.append((i, j, 0)); continue
        if D[0] in small_mult:
            t = small_mult[D[0]]
            if mul(t, G) == D:
                hits_b.append((i, j, t))
            elif mul(t, G) == neg(D):
                hits_b.append((i, j, -t))
print(f"    {'NENHUMA relacao aditiva pequena (esperado)' if not hits_b else hits_b}")

# ============================================================
# A. multiplicativo: Q_j = m*Q_i para m pequeno?
# ============================================================
print(f"\n  [A] Multiplicativo - Q_j = m*Q_i para 2 <= m < 2^16?")
print(f"      (detecta razao inteira pequena entre chaves privadas)")
MA = 1 << 16
hits_a = []
for i in nums:
    target = {Q[j]: j for j in nums if j != i}
    R = Q[i]            # m=1
    for m in range(2, MA):
        R = add(R, Q[i])
        if R in target:
            hits_a.append((i, target[R], m))
print(f"    {'NENHUMA razao pequena (esperado)' if not hits_a else hits_a}")

# ============================================================
# Veredito
# ============================================================
print(f"\n{'='*68}")
print("VEREDITO")
print(f"{'='*68}")
any_hit = bool(hits_a or hits_b or hits_c)
if any_hit:
    print("  !!! RELACAO ENCONTRADA - investigar, pode ser estrutura explravel !!!")
    print(f"    mult: {hits_a}\n    add: {hits_b}\n    G: {hits_c}")
else:
    print("""  Nenhuma relacao simples entre os 6 pubkeys.
  Consistente com derivacao hash-based (BIP32-like) ja comprovada.
  Os pubkeys sao pontos EC independentes -> nenhuma estrutura nao-generica.
  -> A parede de Shoup (sqrt(N)) permanece intacta. Sem atalho barato aqui.

  NOTA sobre "intervalo < 1% da curva": a dificuldade depende do TAMANHO
  ABSOLUTO do intervalo (2^134 para #135), nao da fracao do grupo. A fracao
  pequena JA e o que torna o puzzle atacavel; nao ha desconto adicional.""")
