#!/usr/bin/env python3
"""Exact interval-membership formulation and cost audit on synthetic secp256k1.

For I=[L,L+W), define F_I(X)=product_{j in I}(X-x(jG)) mod p.
If the promised parent interval is below N/2, x is injective on it, so
F_half(x(Q))=0 decides which half contains the discrete logarithm.
For unrestricted Q the roots represent BOTH jG and -jG; verify the final point.

This implementation enumerates tiny synthetic intervals to build polynomials.
It is NOT a new efficient DLP solver. Horner evaluations across a binary descent
cost W-1 field multiplications, despite only log2(W) membership decisions.
No real puzzle search, unknown-key oracle, network access, or transactions.
"""
import hashlib
import json
from pathlib import Path

from electrum_old_mpk import G, N, P, add, mul


def product(a, b, counters):
    result = [0]*(len(a)+len(b)-1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            result[i+j] = (result[i+j]+x*y) % P
            counters['precompute_field_multiplications'] += 1
    return result


def tree(start, roots, counters):
    if len(roots) == 1:
        return {'start': start, 'width': 1, 'coefficients': [-roots[0] % P, 1]}
    half = len(roots)//2
    left, right = tree(start, roots[:half], counters), tree(start+half, roots[half:], counters)
    return {'start': start, 'width': len(roots), 'left': left, 'right': right,
            'coefficients': product(left['coefficients'], right['coefficients'], counters)}


def prepare(start, width):
    if width < 2 or width & (width-1) or not 1 <= start < start+width <= N//2:
        raise ValueError('Expected power-of-two interval inside [1,N/2)')
    counters = {'precompute_field_multiplications': 0,
                'precompute_base_scalar_multiplications': 1,
                'precompute_point_additions': width-1}
    point, roots = mul(start), []
    for i in range(width):
        roots.append(point[0])
        if i+1 < width:
            point = add(point, G)
    return tree(start, roots, counters), counters


def evaluate(coefficients, x):
    result = coefficients[-1]
    for coefficient in reversed(coefficients[:-1]):
        result = (result*x+coefficient) % P
    return result


def recover(public, node):
    if public is None:
        raise ValueError('Infinity is outside the declared interval')
    counts = {'membership_decisions': 0, 'query_field_multiplications': 0,
              'final_scalar_verifications': 1}
    while node['width'] > 1:
        left = node['left']
        counts['membership_decisions'] += 1
        counts['query_field_multiplications'] += len(left['coefficients'])-1
        node = left if evaluate(left['coefficients'], public[0]) == 0 else node['right']
    candidate = node['start']
    if mul(candidate) != public:
        raise ValueError('Candidate fails full public-key verification')
    return candidate, counts


def coefficients_stored(node):
    return len(node['coefficients']) + (coefficients_stored(node['left'])+
        coefficients_stored(node['right']) if node['width'] > 1 else 0)


def main():
    rows = []
    for bits in (4, 6, 8):
        width, start = 1 << bits, (1 << 139)+12345
        root, cost = prepare(start, width)
        # Large scalar start, small unknown interval, real 256-bit field.
        offsets = sorted({0, width-1, width//2-1, width//2} | {
            int.from_bytes(hashlib.sha256(f'interval-control:{bits}:{i}'.encode()).digest(), 'big') % width
            for i in range(12)})
        recovered = []
        for offset in offsets:
            secret = start+offset
            public = mul(secret)
            candidate, measured = recover(public, root)
            assert candidate == secret
            assert measured['membership_decisions'] == bits
            assert measured['query_field_multiplications'] == width-1
            recovered.append(offset)
        # Both signs have the same x. Demonstrate and reject the false positive.
        original = mul(start)
        negative = (original[0], -original[1] % P)
        assert evaluate(root['coefficients'], negative[0]) == 0
        for outside in (negative, mul(start+width), mul(start-1), None):
            try:
                recover(outside, root)
            except ValueError:
                pass
            else:
                raise AssertionError('Out-of-interval point accepted')
        rows.append({'bits': bits, 'width': width, 'interval_start_hex': hex(start),
                     'positive_controls': len(recovered), 'all_keys_recovered': True,
                     'out_of_interval_controls_rejected': 4,
                     'sign_ambiguity_demonstrated': True,
                     'coefficients_stored': coefficients_stored(root), **cost, **measured})
    report = {'formulation': 'F_I(X)=product_(j in I)(X-x(jG)) modulo p',
              'curve': 'secp256k1', 'controls': rows,
              'result': 'Exact membership and key recovery; no asymptotic improvement in this implementation.',
              'cost_identity': 'log2(W) decisions, but W/2+W/4+...+1=W-1 Horner field multiplications per query.',
              'degree_obstruction': 'For a half interval with W/2 distinct x-coordinates, any nonzero univariate polynomial vanishing on all of them has degree at least W/2. This constrains degree, not arithmetic-circuit size or every possible evaluation algorithm.',
              'limitations': [
                  'Preprocessing enumerates all W public points in the synthetic interval.',
                  'All preprocessing, polynomial coefficients and final point verification must be counted.',
                  'Field multiplications and curve operations are different units; counts are not timing comparisons.',
                  'This experiment does not rule out a different representation or evaluation algorithm.',
                  'No claim of literature novelty and no new puzzle key recovered.']}
    output = Path(__file__).with_name('interval-polynomial-results.json')
    output.write_text(json.dumps(report, indent=2)+'\n')
    for row in rows:
        print(json.dumps(row))
    print(output)


if __name__ == '__main__':
    main()
