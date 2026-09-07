/* Standalone arithmetic reference for V8 3.14.5's documented recurrence.
 * Source: https://raw.githubusercontent.com/v8/v8/3.14.5/src/v8.cc
 * This does not embed or run the V8 engine.
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static int allowed_byte(uint32_t a, unsigned byte) {
    unsigned high = (a >> 10) & 255u;
    return high == byte || ((a & 1023u) >= 1009u && ((high+1u) & 255u) == byte);
}

static int scan_projection(const char *hex) {
    unsigned observed[16];
    if (strlen(hex) != 32) return 2;
    for (int i = 0; i < 16; ++i)
        if (sscanf(hex+2*i, "%2x", &observed[i]) != 1) return 2;
    const uint32_t maximum = 18273u*65535u + 65535u;
    uint64_t checked = 0, survivors = 0;
    uint32_t witness = 0;
    /* Enumerate all possible a AFTER the first observed call. The actual
     * recurrence guarantees a <= maximum, for every uint32 predecessor.
     * Each allowed first byte fixes bits 10..17, apart from optional carry.
     */
    for (unsigned carry = 0; carry <= 1; ++carry) {
        unsigned middle = (observed[0]+256u-carry) & 255u;
        for (uint32_t top = 0; top <= (maximum >> 18); ++top) {
            for (unsigned low = carry ? 1009u : 0u; low < 1024u; ++low) {
                uint32_t first = (top << 18) | (middle << 10) | low;
                if (first > maximum) continue;
                ++checked;
                uint32_t a = first;
                int valid = 1;
                for (int j = 1; j < 16; ++j) {
                    a = 18273u*(a & 65535u) + (a >> 16);
                    if (!allowed_byte(a, observed[j])) { valid = 0; break; }
                }
                if (valid) { ++survivors; witness = first; }
            }
        }
    }
    printf("%llu,%llu,%u\n", (unsigned long long)checked,
           (unsigned long long)survivors, witness);
    return 0;
}

int main(int argc, char **argv) {
    if (argc == 2) return scan_projection(argv[1]);
    const uint32_t starts[][2] = {{1, 2}, {0x12345678, 0x87654321}, {0xffffffff, 0xffffffff}};
    for (int s = 0; s < 3; ++s) {
        uint32_t a = starts[s][0], b = starts[s][1];
        for (int i = 0; i < 100; ++i) {
            a = 18273u * (a & 65535u) + (a >> 16);
            b = 36969u * (b & 65535u) + (b >> 16);
            uint32_t output = (a << 14) + (b & 262143u);
            uint64_t encoded = UINT64_C(0x4130000000000000) | output;
            double value;
            memcpy(&value, &encoded, sizeof(value));
            value -= 1048576.0;
            printf("%d,%d,%u,%u\n", s, i, output, (uint32_t)(value * 4294967296.0));
        }
    }
    return 0;
}
