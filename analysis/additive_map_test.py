"""
Procura um HOMOMORFISMO aditivo barato: phi(P+Q) == phi(P) (+) phi(Q)?
Se algum phi bater 100% em pares aleatórios -> mapa aditivo -> ECDLP cai.
Testa na secp256k1 real. Python stdlib puro.
"""
import random, hashlib

P  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G  = (Gx, Gy)

def inv(a): return pow(a, P-2, P)
def add(A, B):
    if A is None: return B
    if B is None: return A
    x1,y1=A; x2,y2=B
    if x1==x2 and (y1+y2)%P==0: return None
    s=(3*x1*x1)*inv(2*y1)%P if A==B else (y2-y1)*inv((x2-x1)%P)%P
    x3=(s*s-x1-x2)%P
    return (x3,(s*(x1-x3)-y1)%P)
def mul(k,Q):
    R=None
    while k>0:
        if k&1: R=add(R,Q)
        Q=add(Q,Q); k>>=1
    return R

def legendre(a):
    a%=P
    return 0 if a==0 else (1 if pow(a,(P-1)//2,P)==1 else -1)

# candidatos phi (P=(x,y)) e a operação alvo (+)
CANDS = {
    "x mod 2":      (lambda P:(P[0]%2), 2, "add"),
    "x mod 3":      (lambda P:(P[0]%3), 3, "add"),
    "x mod 1000003":(lambda P:(P[0]%1000003), 1000003, "add"),
    "y mod 2":      (lambda P:(P[1]%2), 2, "add"),
    "(x+y) mod 7":  (lambda P:((P[0]+P[1])%7), 7, "add"),
    "(x*y) mod 7":  (lambda P:((P[0]*P[1])%7), 7, "add"),
    "x mod p (id)": (lambda P:(P[0]%P), P, "add"),
    "legendre(x)":  (lambda P:legendre(P[0]), 0, "mul"),  # testa multiplicatividade
}

def test(name, phi, m, op, npairs=2000, seed=1):
    rng=random.Random(seed)
    hits=0
    for _ in range(npairs):
        a=rng.randrange(1,1<<40); b=rng.randrange(1,1<<40)
        Pa=mul(a,G); Pb=mul(b,G); Pab=mul((a+b),G)
        if Pa is None or Pb is None or Pab is None: continue
        fa,fb,fab=phi(Pa),phi(Pb),phi(Pab)
        if op=="add":
            ok = (fab == (fa+fb)%m) if m else False
        else:  # mul
            ok = (fab == fa*fb)
        if ok: hits+=1
    chance = (1.0/m) if (op=="add" and m and m<10**6) else (1.0/3 if op=="mul" else 0.0)
    return hits, npairs, chance

if __name__=="__main__":
    print("Procurando phi com phi(P+Q)=phi(P)(+)phi(Q) na secp256k1\n")
    print(f"  {'candidato':>16} | {'acertos':>10} | {'acaso':>7} | veredito")
    print(f"  {'-'*16} | {'-'*10} | {'-'*7} | {'-'*8}")
    found=False
    for name,(phi,m,op) in CANDS.items():
        h,n,ch = test(name,phi,m,op,npairs=1500)
        rate=h/n
        verd = "HOMOMORFISMO!!!" if rate>0.99 else "não-aditivo"
        if rate>0.99: found=True
        chs = f"{ch:.3f}" if ch else "~0"
        print(f"  {name:>16} | {h:>5}/{n:<4} | {chs:>7} | {verd}")
    print()
    if found:
        print("  >>> ACHOU UM MAPA ADITIVO — verificar, seria um ataque real.")
    else:
        print("  Nenhum mapa barato é aditivo. Cada phi quebra a soma -> sem homomorfismo")
        print("  fácil -> a adição da curva não 'passa' por nenhuma função simples das coords.")
