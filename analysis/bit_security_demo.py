"""
Demonstra POR QUE computar 'so alguns bits' da chave nao ajuda.

Argumento de deslocamento (shift): se existisse um oraculo barato que devolve
os bits ALTOS do log discreto, ele poderia ser chamado recursivamente para
recuperar a chave INTEIRA em ~log(W) passos. Como a chave inteira custa >= sqrt(W)
(parede de Shoup), o oraculo barato NAO PODE existir.

Aqui simulamos o oraculo 'trapaceando' (usamos k_true so para provar a logica
da reducao). O ponto: a reducao funciona -> entao bits parciais ~ chave inteira.
"""
import random, math

P  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G  = (Gx, Gy)

def inv(x): return pow(x, P - 2, P)
def padd(A, B):
    if A is None: return B
    if B is None: return A
    x1,y1=A; x2,y2=B
    if x1==x2 and (y1+y2)%P==0: return None
    s = (3*x1*x1)*inv(2*y1)%P if A==B else (y2-y1)*inv((x2-x1)%P)%P
    x3=(s*s-x1-x2)%P
    return (x3,(s*(x1-x3)-y1)%P)
def pmul(k,Pt):
    R=None
    while k>0:
        if k&1: R=padd(R,Pt)
        Pt=padd(Pt,Pt); k>>=1
    return R
def pneg(A): return None if A is None else (A[0],(-A[1])%P)

# ---- oraculo HIPOTETICO: devolve os 'bits_now' bits mais altos do residuo ----
# (trapaceia usando o residuo verdadeiro; serve so p/ demonstrar a logica da reducao.
#  Q seria a entrada real de um oraculo verdadeiro; aqui nao e usado pois trapaceamos.)
ORACLE_CALLS = 0
def oracle_top_bits(Q, residuo_true, m):
    global ORACLE_CALLS
    ORACLE_CALLS += 1
    return residuo_true >> m              # os bits altos acima da posicao m

def recover_via_shift(Q, exp, b, k_true):
    """Recupera k inteiro (em [0,2^exp)) usando so o oraculo de bits altos."""
    known = 0
    cur_Q = Q
    cur_k = k_true        # residuo verdadeiro (para o oraculo trapaceiro)
    e = exp
    while e > 0:
        bits_now = min(b, e)
        m = e - bits_now
        top = oracle_top_bits(cur_Q, cur_k, m)     # bits_now bits altos
        known = (known << bits_now) | top
        cur_Q = padd(cur_Q, pneg(pmul(top << m, G)))   # remove contribuicao
        cur_k &= (1 << m) - 1                            # residuo restante
        e = m
    return known

if __name__ == "__main__":
    print("=" * 64)
    print("DEMO: por que 'so alguns bits' nao ajuda (bit-security do DL)")
    print("=" * 64)
    random.seed(1)
    for bits in [40, 60, 80]:
        W = 1 << bits
        k_true = random.randrange(0, W)
        Q = pmul(k_true, G)
        b = 8   # oraculo devolve 8 bits altos por chamada
        ORACLE_CALLS = 0
        k_rec = recover_via_shift(Q, bits, b, k_true)
        ok = (k_rec == k_true)
        sqrtW = math.isqrt(W)
        print(f"\n  Intervalo 2^{bits}:")
        print(f"    chave recuperada corretamente: {ok}")
        print(f"    chamadas ao oraculo: {ORACLE_CALLS}  (~ {bits}/{b} = {bits//b})")
        print(f"    custo full DLP (Shoup): ~sqrt(W) = 2^{bits//2} = {sqrtW}")
        print(f"    => se cada chamada custasse < 2^{bits//2}, o DLP inteiro")
        print(f"       sairia em {ORACLE_CALLS} x custo << sqrt(W). PROIBIDO.")

    print(f"""
  CONCLUSAO:
    A reducao FUNCIONA: bits altos -> recursao -> chave inteira em ~bits/b passos.
    Logo, um oraculo BARATO de bits altos resolveria o DLP inteiro barato.
    Como isso e impossivel (Shoup, sqrt(W)), o oraculo barato NAO EXISTE.
    -> Computar 'o comeco' ou 'o fim' da chave e tao caro quanto a chave toda.

  Mesma logica vale para um PREDITOR PROBABILISTICO: um modelo que acertasse
  1 bit do DL com vantagem nao-desprezivel seria amplificavel num solver completo
  (auto-correcao do DL). Como o DL nao esta quebrado, tal preditor nao existe.
  -> Por isso ML treinado nas chaves resolvidas nao preve as nao resolvidas.

  O UNICO conhecimento parcial que ajuda e o intervalo (bits altos = zero),
  e ele JA esta 100% embutido no kangaroo (que paga so sqrt do intervalo).
""")
