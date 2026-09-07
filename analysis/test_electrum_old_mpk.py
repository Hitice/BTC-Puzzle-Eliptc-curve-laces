"""Independent public vectors and exhaustive small-modulus reference checks."""
import random
import unittest

from electrum_old_mpk import (N, OFFICIAL_MPK, OFFICIAL_SEED, address, compatible,
                              mul, offset, parse_mpk, raw_point, refine, stretch)


class ElectrumOldTests(unittest.TestCase):
    def test_official_wallet_vector(self):
        master = stretch(OFFICIAL_SEED)
        mpk = parse_mpk(OFFICIAL_MPK)
        self.assertEqual(raw_point(mul(master)), mpk)
        for branch, expected in ((0, '1FJEEB8ihPMbzs2SkLmr37dHyRFzakqUmo'),
                                 (1, '1KRW8pH6HFHZh889VDq6fEKvmrsmApwNfe')):
            child = (master + offset(mpk, 0, branch)) % N
            self.assertEqual(address(mul(child)), expected)

    def test_interval_filter_against_exhaustive_reference(self):
        rng = random.Random(20260907)
        for _ in range(1000):
            modulus = rng.choice((7, 17, 31, 101))
            states = [(0, 1, 1, modulus-1)]
            expected = set(range(1, modulus))
            for _ in range(5):
                h, bits = rng.randrange(modulus), rng.randrange(0, 8)
                observed = rng.randrange(1 << bits)
                states = refine(states, h, bits, observed, modulus)
                expected = {m for m in expected if (m+h) % modulus != 0 and
                            ((m+h) % modulus) % (1 << bits) == observed}
                actual = {m for _, step, first, last in states for m in range(first, last+1, step)}
                self.assertEqual(actual, expected)

    def test_masked_controls_both_carries_and_all_mappings(self):
        for master in (1, N//2, N-1):
            mpk = raw_point(mul(master))
            for branch in (0, 1):
                for shift in (-1, 0):
                    known = {}
                    for i in (32, 50, 70, 100, 130):
                        child = (master+offset(mpk, i+shift, branch)) % N
                        known[i] = (1 << (i-1)) | (child % (1 << (i-1)))
                    result = compatible(mpk, known, branch, shift)
                    self.assertEqual(result['status'], 'arithmetic_compatible')
                    self.assertTrue(any(s['first'] <= master <= s['last'] and
                                        (master-s['residue']) % s['step'] == 0
                                        for s in result['master_progressions']))
                    known[130] ^= 1
                    self.assertEqual(compatible(mpk, known, branch, shift)['status'], 'incompatible')

    def test_invalid_mpk(self):
        for value in ('00', '00'*64, 'ff'*64):
            with self.assertRaises(ValueError):
                parse_mpk(value)


if __name__ == '__main__':
    unittest.main()
