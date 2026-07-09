"""
Existe heurística de progresso ("estou ficando mais quente"?) rumo ao alvo?
Sandbox: puzzle #30, k conhecido. Para candidatos g a distância real d=|g-k| do alvo,
mede se alguma função das coordenadas de g*G se aproxima de x(Q). Se houver gradiente,
dá pra descer até k. Expectativa honesta: nenhum sinal — um passo já embaralha tudo.
"""
import random

P  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G  = (Gx, Gy)
def inv(a): return pow(a,P-2,P)
def add(A,B):
    if A is None: return B
    if B is None: return A
    x1,y1=A;x2,y2=B
    if x1==x2 and (y1+y2)%P==0: return None
    s=(3*x1*x1)*inv(2*y1)%P if A==B else (y2-y1)*inv((x2-x1)%P)%P
    x3=(s*s-x1-x2)%P
    return (x3,(s*(x1-x3)-y1)%P)
def mul(k,Q=G):
    R=None
    while k>0:
        if k&1: R=add(R,Q)
        Q=add(Q,Q); k>>=1
    return R

k30 = 0x3d94cd64
Q = mul(k30)
xQ = Q[0]

def bitdist(x): return bin(x ^ xQ).count("1")      # bits diferentes de x(Q)
def absdiff(x): return abs(x - xQ)

print(f"#30: k={hex(k30)}  x(Q)={hex(xQ)[:18]}...\n")
print("  Quão 'quente' fica conforme me aproximo de k?")
print(f"  {'dist |g-k|':>12} | {'bits dif. médios (de 256)':>26}")
print(f"  {'-'*12} | {'-'*26}")

rng=random.Random(0)
for d in [1,2,5,10,100,1000,10**4,10**5,10**6]:
    ds=[]
    for _ in range(12):
        sign = 1 if rng.random()<0.5 else -1
        g = k30 + sign*d
        Pg = mul(g)
        if Pg is None: continue
        ds.append(bitdist(Pg[0]))
    print(f"  {d:>12} | {sum(ds)/len(ds):>26.1f}")

# correlação real entre distância e bit-dist, em candidatos aleatórios
xs=[]; ys=[]
for _ in range(400):
    g = rng.randrange(1<<29, 1<<30)
    Pg=mul(g)
    if Pg is None: continue
    xs.append(abs(g-k30)); ys.append(bitdist(Pg[0]))
mx=sum(xs)/len(xs); my=sum(ys)/len(ys)
cov=sum((a-mx)*(b-my) for a,b in zip(xs,ys))
vx=sum((a-mx)**2 for a in xs)**.5; vy=sum((b-my)**2 for b in ys)**.5
corr=cov/(vx*vy) if vx*vy else 0
print(f"\n  Correlação(distância real, bits-diferentes) = {corr:+.4f}")
print(f"  {'(esperado ~0: SEM gradiente — um passo do alvo já parece tão longe quanto 1 milhão)' }")
print(f"\n  Veredito: {'GRADIENTE!' if abs(corr)>0.2 else 'terreno plano — nenhuma heurística de progresso. Cubo vendado confirmado.'}")
