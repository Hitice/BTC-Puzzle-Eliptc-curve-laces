#!/usr/bin/env python3
"""Exact 2D lattice tests for a known key interval and two weak nonce models.

Offline, public-puzzle research. Python >=3.9 and cryptography required.
No claim of general ECDSA recovery: a strong nonce restriction is essential.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import time

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141


def dot(a, b):
    return a[0]*b[0] + a[1]*b[1]


def gauss_reduce(b1, b2):
    """Unimodular basis reduction with exact integer arithmetic."""
    for _ in range(10000):
        if dot(b2, b2) < dot(b1, b1):
            b1, b2 = b2, b1
        norm = dot(b1, b1)
        mu = (2*dot(b1, b2) + norm) // (2*norm)
        if mu == 0:
            return b1, b2
        b2 = (b2[0]-mu*b1[0], b2[1]-mu*b1[1])
    raise RuntimeError('Gauss iteration limit')


def ceil_fraction(f):
    return -((-f.numerator)//f.denominator)


def floor_fraction(f):
    return f.numerator//f.denominator


def bounded_congruence(a, b, D, K, modulus=N, max_cells=200000):
    """Enumerate ALL (x,u): x=a*u+b mod modulus, 0<=x<D, 1<=u<K.

    Lattice vectors are (K*(modulus*t+a*u), D*u). The allowed rectangle
    is transformed exactly into a bounding box of integer basis coefficients.
    If its resource cap is exceeded, raise; never report a negative result.
    """
    a, b = a % modulus, b % modulus
    b1, b2 = gauss_reduce((modulus*K, 0), (a*K, D))
    det = b1[0]*b2[1]-b1[1]*b2[0]
    corners = [(K*(x-b), D*u) for x in (0, D-1) for u in (1, K-1)]
    coordinates = [(Fraction(X*b2[1]-Y*b2[0], det),
                    Fraction(b1[0]*Y-b1[1]*X, det)) for X,Y in corners]
    lower = [ceil_fraction(min(v[i] for v in coordinates)) for i in (0,1)]
    upper = [floor_fraction(max(v[i] for v in coordinates)) for i in (0,1)]
    cells = max(0,upper[0]-lower[0]+1)*max(0,upper[1]-lower[1]+1)
    if cells > max_cells:
        raise RuntimeError(f'Coefficient box has {cells} points; cap is {max_cells}')
    candidates = []
    for c1 in range(lower[0], upper[0]+1):
        for c2 in range(lower[1], upper[1]+1):
            X,Y = c1*b1[0]+c2*b2[0], c1*b1[1]+c2*b2[1]
            assert X % K == 0 and Y % D == 0
            x,u = X//K+b, Y//D
            if 0 <= x < D and 1 <= u < K:
                assert (x-a*u-b) % modulus == 0
                candidates.append((x,u))
    return candidates, cells


def pubkey(d):
    return ec.derive_private_key(d,ec.SECP256K1()).public_key().public_bytes(
        serialization.Encoding.X962,serialization.PublicFormat.CompressedPoint)


def validate_signature(row):
    r,s,z = (int(row[k],16) for k in ('r','s','z'))
    q = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(),bytes.fromhex(row['pubkey']))
    q.verify(utils.encode_dss_signature(r,s),z.to_bytes(32,'big'),
             ec.ECDSA(utils.Prehashed(hashes.SHA256())))
    return r,s,z


def scan(row, nonce_bits, model, max_cells=200000):
    r,s,z = validate_signature(row)
    number = row['puzzle']
    A = D = 1 << (number-1)
    K = 1 << nonce_bits
    # Model 1: k=u. Model 2: k=2^(256-nonce_bits)*u. Both test 1<=u<K.
    factor = 1 if model == 'small_nonce' else 1 << (256-nonce_bits)
    rinv = pow(r,-1,N)
    b = (-z*rinv-A) % N
    target = bytes.fromhex(row['pubkey'])
    total_candidates, total_cells, ec_checks, matches = 0,0,0,[]
    for sign in (1,-1):
        ss = sign*s % N
        a = ss*rinv*factor % N
        candidates,cells = bounded_congruence(a,b,D,K,max_cells=max_cells)
        total_cells += cells
        total_candidates += len(candidates)
        for x,u in candidates:
            k,d = factor*u,A+x
            if not 1 <= k < N:
                continue
            ec_checks += 1
            if pubkey(d) == target:
                # Full independent elliptic-curve check, beyond the linear relation.
                kr = ec.derive_private_key(k,ec.SECP256K1()).public_key().public_numbers().x % N
                assert kr == r and (ss*k-z-r*d) % N == 0
                matches.append({'private_key_hex':f'{d:064x}','nonce_hex':f'{k:064x}',
                                's_sign':sign})
    return {'puzzle':number,'model':model,'nonce_variable_bits':nonce_bits,
            'zero_low_bits':256-nonce_bits if model == 'zero_low_bits' else 0,
            'key_interval_unknown_bits':number-1,'status':'complete',
            'coefficient_box_points':total_cells,'congruence_candidates':total_candidates,
            'public_key_checks':ec_checks,'matches':matches}


def synthetic_signature(number,d,k,label):
    z = int.from_bytes(hashlib.sha256(label).digest(),'big')
    r = ec.derive_private_key(k,ec.SECP256K1()).public_key().public_numbers().x % N
    s = (z+r*d)*pow(k,-1,N) % N
    s = min(s,N-s)
    return {'puzzle':number,'pubkey':pubkey(d).hex(),'r':f'{r:064x}',
            's':f'{s:064x}','z':f'{z:064x}'}


def self_test():
    # Exhaustive reference on a small modulus checks completeness of the box scan.
    for a in range(101):
        result,_ = bounded_congruence(a,37,7,9,modulus=101)
        expected={(x,u) for x in range(7) for u in range(1,9) if (x-a*u-37)%101==0}
        assert set(result)==expected
    D=1<<139
    d=D+(int.from_bytes(hashlib.sha256(b'synthetic d, not a puzzle key').digest(),'big')%D)
    u=1+(int.from_bytes(hashlib.sha256(b'synthetic short nonce').digest(),'big')%((1<<110)-1))
    controls=[]
    for model,k in [('small_nonce',u),('zero_low_bits',u*(1<<144))]:
        row=synthetic_signature(140,d,k,b'positive control '+model.encode())
        result=scan(row,112,model)
        assert any(int(m['private_key_hex'],16)==d for m in result['matches'])
        controls.append({'model':model,'private_key_recovered':True,
                         'signature_count':1,'coefficient_box_points':result['coefficient_box_points'],
                         'public_key_checks':result['public_key_checks']})
    full_nonce=(1<<255)+int.from_bytes(hashlib.sha256(b'negative control').digest(),'big')%(1<<254)
    row=synthetic_signature(140,d,full_nonce,b'outside both tested nonce models')
    for model in ('small_nonce','zero_low_bits'):
        result=scan(row,112,model)
        assert result['matches']==[]
    return {'exact_enumeration_control':'101 coefficient values checked against exhaustive reference',
            'positive_controls':controls,'negative_controls':'both models correctly reject outside-model nonce'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=Path(__file__).resolve().parent/'target-signatures.json')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--self-test',action='store_true')
    parser.add_argument('--work-bits',type=int,default=10)
    args=parser.parse_args()
    if not 0<=args.work_bits<=12:
        parser.error('--work-bits must be between 0 and 12')
    started=time.monotonic()
    controls=self_test()
    if args.self_test:
        print(json.dumps(controls,indent=2));return
    rows=json.loads(args.input.read_text())
    results=[]
    for row in rows:
        nonce_bits=256-(row['puzzle']-1)+args.work_bits
        if not 1<=nonce_bits<=255:
            raise ValueError('Unsupported nonce bit count')
        for model in ('small_nonce','zero_low_bits'):
            result=scan(row,nonce_bits,model)
            results.append(result)
            print(f"#{row['puzzle']} {model}: {result['public_key_checks']} EC checks, "
                  f"{len(result['matches'])} matches",flush=True)
    report={'purpose':'New bounded tests of explicit nonce weaknesses, not a general ECDSA solver',
            'curve':'secp256k1','self_tests':controls,'work_bits':args.work_bits,
            'signatures_validated':len(rows),'results':results,
            'elapsed_seconds':time.monotonic()-started,
            'coverage':'Both s signs; all lattice points in each specified rectangle. Resource overflow raises an error.',
            'limitations':['Only two nonce families are tested.','Negative results do not prove full nonce security.',
                           'A synthetic recovery is not a recovered Bitcoin puzzle key.']}
    text=json.dumps(report,indent=2)+'\n'
    if args.output: args.output.write_text(text)
    else: print(text)


if __name__=='__main__':
    main()
