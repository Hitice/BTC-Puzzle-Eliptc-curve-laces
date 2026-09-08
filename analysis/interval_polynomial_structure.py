#!/usr/bin/env python3
"""H7 follow-up: can F_I be built or evaluated without enumerating its factors?

Two independent experiments on secp256k1, answering the question left open by
interval_polynomial_lab.py.

(1) BUILD WITHOUT ENUMERATION. Semaev's third summation polynomial S3 gives an
    exact identity that produces F_{A+s}*F_{A-s} from the COEFFICIENTS of F_A
    and the single value x(sG), with no scalar multiplication over A:

        Res_u(F_A(u), S3(u, x(sG), X)) = F_A(x(sG))^2 * F_{A+s}(X) * F_{A-s}(X)

    So structure exists and the answer is yes. It does not help: the output has
    degree 2|A|, so each shift-and-double step costs at least |A| again and the
    total stays linear in the interval width.

(2) CONTRAST: high degree alone is not the obstruction. The division polynomial
    psi_n has degree ~n^2/2 yet is evaluated at a point in O(log n) field
    operations via the elliptic divisibility recurrence. Its root set is the
    n-torsion, a SUBGROUP; the group law is what supplies the recurrence.
    An interval [L,L+W) is not closed under the group law, so no analogue is
    available for F_I. This is the X^(2^100) analogue, and it exists only for
    the subgroup case.

Controls: S3 checked against real point sums; the shift identity checked against
brute-force products; the psi ladder checked against the naive O(n) recurrence
for n=1..400 and against nQ=O membership. No puzzle key search, no network.
"""
import json
import random
from pathlib import Path

from electrum_old_mpk import G, N, P, mul

A_CURVE, B_CURVE = 0, 7          # secp256k1: y^2 = x^3 + 7
INTERVAL_START = (1 << 139) + 12345
SHIFT = 10**9 + 7
LADDER_POINT_SCALAR = 31337


# --------------------------------------------------------------------------- #
# polynomials over F_p, coefficients low -> high
# --------------------------------------------------------------------------- #
def trim(a):
    while a and a[-1] == 0:
        a.pop()
    return a


def polymul(a, b, counters=None):
    r = [0]*(len(a)+len(b)-1)
    for i, x in enumerate(a):
        if x:
            for j, y in enumerate(b):
                r[i+j] = (r[i+j]+x*y) % P
                if counters is not None:
                    counters['field_multiplications'] += 1
    return trim(r)


def horner(c, x):
    r = 0
    for coefficient in reversed(c):
        r = (r*x+coefficient) % P
    return r


def resultant(f, g, counters=None):
    """Res_u(f, g) over F_p by the Euclidean algorithm."""
    f, g = trim(list(f)), trim(list(g))
    if not f or not g:
        return 0
    res = 1
    while len(g) > 1:
        df, dg = len(f)-1, len(g)-1
        r, inv = list(f), pow(g[-1], -1, P)
        while trim(r) and len(r)-1 >= dg:
            d, c = len(r)-1-dg, r[-1]*inv % P
            for i, gc in enumerate(g):
                r[i+d] = (r[i+d]-c*gc) % P
                if counters is not None:
                    counters['field_multiplications'] += 1
            trim(r)
        if not r:
            return 0
        if (df*dg) & 1:
            res = (-res) % P
        res = res*pow(g[-1], df-(len(r)-1), P) % P
        f, g = g, r
    return res*pow(g[0], len(f)-1, P) % P


def s3_in_u(t, v):
    """Semaev S3(u, v, t) collected as a quadratic in u, for y^2 = x^3 + b."""
    b = B_CURVE
    return [(t*t*v*v - 4*b*t - 4*b*v) % P,
            (-2*t*t*v - 2*t*v*v - 4*b) % P,
            (t-v)**2 % P]


def build_F(scalars, counters=None):
    poly = [1]
    for k in scalars:
        poly = polymul(poly, [(-mul(k)[0]) % P, 1], counters)
    return poly


def interpolate(xs, ys):
    coefficients = [0]*len(xs)
    for i, xi in enumerate(xs):
        num, den = [1], 1
        for j, xj in enumerate(xs):
            if i != j:
                num = polymul(num, [(-xj) % P, 1])
                den = den*(xi-xj) % P
        scale = ys[i]*pow(den, -1, P) % P
        for k, c in enumerate(num):
            coefficients[k] = (coefficients[k]+c*scale) % P
    return trim(coefficients)


# --------------------------------------------------------------------------- #
# experiment 1: shift identity
# --------------------------------------------------------------------------- #
def control_s3():
    """S3(x(P), x(Q), x(R)) vanishes exactly when P +- Q +- R = O."""
    rows = []
    for k1, k2 in ((12345, 67890), (2, 3), (1 << 100, (1 << 90)+5)):
        u, v = mul(k1)[0], mul(k2)[0]
        def at(t):
            c = s3_in_u(t, v)
            return (c[2]*u*u + c[1]*u + c[0]) % P
        rows.append({'k1': k1, 'k2': k2,
                     'vanishes_on_sum': at(mul(k1+k2)[0]) == 0,
                     'vanishes_on_difference': at(mul(k1-k2)[0]) == 0,
                     'nonzero_on_unrelated': at(mul(k1+k2+1)[0]) != 0})
    return rows


def shift_identity(width, trials=6):
    """Check the identity pointwise at random X, against brute-force products."""
    A = list(range(INTERVAL_START, INTERVAL_START+width))
    FA, v = build_F(A), mul(SHIFT)[0]
    left_square = horner(FA, v)**2 % P
    matches = 0
    for _ in range(trials):
        t = random.randrange(P)
        expected = left_square
        for a in A:
            expected = expected*(t-mul(a+SHIFT)[0]) % P*(t-mul(a-SHIFT)[0]) % P
        matches += resultant(FA, s3_in_u(t, v)) == expected
    return {'width': width, 'random_evaluations': trials, 'identity_matches': matches}


def rebuild_coefficients(width):
    """Recover the coefficients of F_{A+s}*F_{A-s} from F_A's coefficients alone."""
    A = list(range(INTERVAL_START, INTERVAL_START+width))
    counters = {'field_multiplications': 0}
    FA, v = build_F(A), mul(SHIFT)[0]
    points = list(range(1, 2*width+3))
    values = [resultant(FA, s3_in_u(t, v), counters) for t in points]
    inv = pow(horner(FA, v)**2 % P, -1, P)
    got = [c*inv % P for c in interpolate(points, values)]
    want = polymul(build_F([a+SHIFT for a in A]), build_F([a-SHIFT for a in A]))
    return {'width': width, 'input_degree': width, 'output_degree': len(got)-1,
            'coefficients_match_brute_force': got == want,
            'scalar_multiplications_over_the_interval': 0,
            'resultant_field_multiplications': counters['field_multiplications']}


# --------------------------------------------------------------------------- #
# experiment 2: division polynomial, high degree with O(log n) evaluation
# --------------------------------------------------------------------------- #
def psi_seed(x, y):
    a, b = A_CURVE, B_CURVE
    return {0: 0, 1: 1, 2: 2*y % P,
            3: (3*x**4 + 6*a*x*x + 12*b*x - a*a) % P,
            4: 4*y*(x**6 + 5*a*x**4 + 20*b*x**3 - 5*a*a*x*x
                    - 4*a*b*x - 8*b*b - a**3) % P}


def psi_naive(n, x, y):
    """Reference O(n) sequence, used only as the positive control."""
    v, inv2y = psi_seed(x, y), pow(2*y % P, -1, P)
    for j in range(5, n+1):
        k = j >> 1
        if j & 1:
            v[j] = (v[k+2]*pow(v[k], 3, P) - v[k-1]*pow(v[k+1], 3, P)) % P
        else:
            v[j] = v[k]*(v[k+2]*v[k-1]**2 - v[k-2]*v[k+1]**2) % P*inv2y % P
    return v


def psi_fast(n, x, y, counters):
    """psi_n at (x,y) in O(log n) field operations, via an 8-term block ladder."""
    if n == 0:
        return 0
    seed, inv2y = psi_naive(5, x, y), pow(2*y % P, -1, P)
    value = {i: (-seed[-i]) % P if i < 0 else seed[i] for i in range(-2, 6)}
    m = 1
    block = {i-1: value[i] for i in range(-2, 6)}       # offsets -3..4
    for bit in bin(n)[3:]:
        target, new = 2*m+int(bit), {}
        for j in range(target-3, target+5):
            k = j >> 1
            if j & 1:
                new[j-target] = (block[k+2-m]*pow(block[k-m], 3, P)
                                 - block[k-1-m]*pow(block[k+1-m], 3, P)) % P
            else:
                new[j-target] = block[k-m]*(block[k+2-m]*block[k-1-m]**2
                                            - block[k-2-m]*block[k+1-m]**2) % P*inv2y % P
            counters['field_multiplications'] += 6
        m, block = target, new
    return block[0]


def division_polynomial_experiment():
    x, y = mul(LADDER_POINT_SCALAR)
    reference = psi_naive(400, x, y)
    ladder_agrees = all(psi_fast(n, x, y, {'field_multiplications': 0}) == reference[n]
                        for n in range(1, 401))
    rows = []
    for label, n in (('N', N), ('N-1', N-1), ('N+1', N+1), ('2N', 2*N), ('3N', 3*N),
                     ('2^200', 1 << 200), ('random', random.randrange(2, N))):
        counters = {'field_multiplications': 0}
        vanishes = psi_fast(n, x, y, counters) == 0
        degree = (n*n-1)//2 if n & 1 else (n*n-4)//2
        rows.append({'n': label, 'n_bits': n.bit_length(),
                     'psi_degree_bits': degree.bit_length(),
                     'vanishes': vanishes, 'expected_vanishes': n % N == 0,
                     'field_multiplications': counters['field_multiplications']})
    universal = all(psi_fast(N, *mul(k), {'field_multiplications': 0}) == 0
                    for k in (1, 2, 3, 999, 10**12, random.randrange(2, N)))
    return {'ladder_matches_naive_recurrence_n_1_to_400': ladder_agrees,
            'membership_decisions_all_correct': all(r['vanishes'] == r['expected_vanishes']
                                                    for r in rows),
            'psi_N_vanishes_at_every_tested_point': universal,
            'evaluations': rows}


def main():
    random.seed(7)
    report = {
        'question': 'Can F_I(X)=product_(j in I)(X-x(jG)) be built or evaluated '
                    'without constructing all |I| factors?',
        'curve': 'secp256k1',
        'experiment_1_build_without_enumeration': {
            'identity': 'Res_u(F_A(u), S3(u, x(sG), X)) '
                        '= F_A(x(sG))^2 * F_{A+s}(X) * F_{A-s}(X)',
            's3_controls': control_s3(),
            'pointwise_checks': [shift_identity(w) for w in (8, 16, 32)],
            'coefficient_rebuilds': [rebuild_coefficients(w) for w in (8, 16)],
            'answer': 'Yes for construction. F_{A+s}*F_{A-s} is obtained from the '
                      'coefficients of F_A and the single value x(sG), with zero scalar '
                      'multiplications over A. It gives no speedup: the output degree is '
                      '2|A|, so writing the result down already costs 2|A| coefficients '
                      'and a shift-and-double chain to width W costs Omega(W).',
            'literature': 'S3 is Semaev third summation polynomial (ePrint 2004/031); '
                          'the resultant elimination step is the standard index-calculus '
                          'machinery of Gaudry and Diem. Not new.'},
        'experiment_2_high_degree_with_fast_evaluation': {
            'object': 'division polynomial psi_n, degree ~n^2/2, evaluated in O(log n)',
            'result': division_polynomial_experiment(),
            'answer': 'High degree is not the obstruction, confirming the lab note. '
                      'psi_N has degree about 2^510 and is evaluated exactly in ~12k field '
                      'multiplications, deciding membership in the n-torsion. The recurrence '
                      'exists because the root set is a SUBGROUP, closed under the group law. '
                      'An interval [L,L+W) has no such closure, so this construction does not '
                      'transfer to F_I.'},
        'conclusion': [
            'The formulation in interval_polynomial_lab.py is correct and its cost audit is '
            'correct; the search is inside the evaluation, as reported there.',
            'Building F_I without enumerating points is possible and known; it does not '
            'reduce cost because degree equals |I| and the coefficient list is the output.',
            'A small arithmetic circuit for X -> F_I(X) would give interval-ECDLP in '
            'O(circuit_size * log W) field operations. Generic-group lower bounds are '
            'Omega(sqrt(W)) and the best known interval algorithm is Pollard kangaroo at '
            '~2*sqrt(W) group operations. Such a circuit is therefore not a step toward '
            'breaking ECDLP: it IS breaking ECDLP.',
            'Generic lower bounds do not formally exclude it, because F_I is evaluated on the '
            'field representation of x, outside the generic group model. That gap is exactly '
            'what summation-polynomial index calculus targets, and over prime fields such as '
            'secp256k1 those attacks have produced no improvement over sqrt(W).'],
        'limitations': [
            'Small widths (8, 16, 32) for the identity; it is an algebraic identity, not a '
            'statistical claim, and brute force is the reference.',
            'Field-multiplication counts are not timing comparisons.',
            'No impossibility proof for an arbitrary evaluation algorithm is claimed here.',
            'No literature novelty claimed and no puzzle key recovered.']}
    output = Path(__file__).with_name('interval-polynomial-structure-results.json')
    output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report['experiment_1_build_without_enumeration']['coefficient_rebuilds'],
                     indent=2))
    print(json.dumps(report['experiment_2_high_degree_with_fast_evaluation']['result'], indent=2))
    print(output)


if __name__ == '__main__':
    main()
