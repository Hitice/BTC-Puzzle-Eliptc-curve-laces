"""
Verificador em lote: kG == Q ? (com inversao em batch - Montgomery's trick)

Modos:
  python batch_verify.py                 -> valida TODOS os puzzles resolvidos (puzzles.json)
  python batch_verify.py pares.txt       -> valida pares do arquivo, 1 por linha:
                                            <privkey_hex> <pubkey_hex>
                                            (pubkey comprimida 02/03.. ou 04..)
Imprime MATCH / NAO por linha. Use pra checar qualquer "FOUND": so e real se MATCH.
"""
import sys, os, json

P  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G  = (Gx, Gy)

# --- EC em Jacobiano (sem inversao por ponto durante a mult.) ---
def j_dbl(Pt):
    X1,Y1,Z1 = Pt
    if Y1 == 0 or Z1 == 0: return (0,0,0)
    A=(X1*X1)%P; B=(Y1*Y1)%P; C=(B*B)%P
    D=(2*(((X1+B)*(X1+B)-A-C)%P))%P
    E=(3*A)%P; F=(E*E)%P
    X3=(F-2*D)%P; Y3=(E*(D-X3)-8*C)%P; Z3=(2*Y1*Z1)%P
    return (X3,Y3,Z3)
def j_add(Pt,Qt):
    X1,Y1,Z1=Pt; X2,Y2,Z2=Qt
    if Z1==0: return Qt
    if Z2==0: return Pt
    Z1Z1=(Z1*Z1)%P; Z2Z2=(Z2*Z2)%P
    U1=(X1*Z2Z2)%P; U2=(X2*Z1Z1)%P
    S1=(Y1*Z2*Z2Z2)%P; S2=(Y2*Z1*Z1Z1)%P
    if U1==U2:
        if S1!=S2: return (0,0,0)
        return j_dbl(Pt)
    H=(U2-U1)%P; I=((2*H)%P)**2%P; J=(H*I)%P
    r=(2*(S2-S1))%P; V=(U1*I)%P
    X3=(r*r-J-2*V)%P; Y3=(r*(V-X3)-2*S1*J)%P; Z3=(((Z1+Z2)*(Z1+Z2)-Z1Z1-Z2Z2)*H)%P
    return (X3,Y3,Z3)
def j_mul(k):
    R=(0,0,0); Q=(Gx,Gy,1)
    while k>0:
        if k&1: R=j_add(R,Q)
        Q=j_dbl(Q); k>>=1
    return R

def batch_affine(jpts):
    """Converte N pontos Jacobianos -> (x,y) afim com UMA inversao (Montgomery)."""
    n=len(jpts); zs=[p[2] for p in jpts]
    pref=[1]*(n+1)
    for i in range(n): pref[i+1]=(pref[i]*(zs[i] if zs[i] else 1))%P
    inv=pow(pref[n],P-2,P)
    xs=[0]*n; ys=[0]*n
    for i in range(n-1,-1,-1):
        zi=zs[i] if zs[i] else 1
        zinv=(inv*pref[i])%P; inv=(inv*zi)%P
        z2=(zinv*zinv)%P; z3=(z2*zinv)%P
        xs[i]=(jpts[i][0]*z2)%P; ys[i]=(jpts[i][1]*z3)%P
    return xs,ys

def parse_pub(pk):
    pk="".join(c for c in pk if c in "0123456789abcdefABCDEF")
    b=bytes.fromhex(pk)
    if b[0]==4: return (int.from_bytes(b[1:33],'big'), int.from_bytes(b[33:65],'big'), None)
    x=int.from_bytes(b[1:],'big'); return (x, None, b[0])  # comprimida: guarda paridade

def verify(pairs):
    # pairs: lista de (label, k, (x, y_or_None, parity_or_None))
    jpts=[j_mul(k) for _,k,_ in pairs]
    xs,ys=batch_affine(jpts)
    out=[]
    for i,(label,k,(qx,qy,par)) in enumerate(pairs):
        ok=(xs[i]==qx)
        if ok and qy is not None: ok=(ys[i]==qy)
        if ok and par is not None: ok=((ys[i]&1)==(par&1))
        out.append((label,ok,k))
    return out

def main():
    if len(sys.argv)>1:
        pairs=[]
        for ln in open(sys.argv[1]):
            ln=ln.strip()
            if not ln or ln.startswith("#"): continue
            a=ln.split()
            k=int(a[0],16); pub=parse_pub(a[1])
            pairs.append((a[0][:12]+"...", k, pub))
    else:
        HERE=os.path.dirname(os.path.abspath(__file__))
        PJ=json.load(open(os.path.join(HERE,"..","data","puzzles.json")))["puzzles"]
        pairs=[(f"#{p['puzzle']}", p["privkey_int"], parse_pub(p["pubkey"]))
               for p in PJ if p["status"]=="solved" and p.get("pubkey")]

    res=verify(pairs)
    ok=sum(1 for _,b,_ in res if b)
    for label,b,k in res:
        print(f"  {label:>8}  {'MATCH' if b else 'NAO  <<<'}")
    print(f"\n  {ok}/{len(res)} validados (kG==Q).")
    if ok==len(res): print("  Todos batem.")

if __name__=="__main__":
    main()
