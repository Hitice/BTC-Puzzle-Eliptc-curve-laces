> **HISTÓRICO — NÃO LEIA POR PADRÃO.** O ponto de entrada é [BRIEFING.md](../BRIEFING.md). Scrape de site; os fatos úteis estão no BRIEFING seção 4 e em `data/puzzles.json`.

🔥 ~1000 BTC Bitcoin Challenge
Status: PARTIALLY SOLVED
Prize: 988.498 BTC (total), 71.998 (won), 916.5 BTC (remaining)
Creator: saatoshi_rising
Start Date: 2015-01-15
Address:
1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU
 7.10152839
 7.10152839
 33
Description
In 2015, in order to show the hugeness of the private key space (or maybe just for fun), someone created a "puzzle" where he chose keys in a certain smaller space and sent increasing amounts to each of those keys like this:

20 ≤ random key < 21 — 0.001 BTC
21 ≤ random key < 22 — 0.002 BTC
23 ≤ random key < 23 — 0.003 BTC
...
2255 ≤ random key < 2256 — 0.256 BTC
(total 32.896 BTC)

Original puzzle description from the creator:

"A few words about the puzzle. There is no pattern. It is just consecutive keys from a deterministic wallet (masked with leading 000...0001 to set difficulty). It is simply a crude measuring instrument, of the cracking strength of the community."

 saatoshi_rising on BitcoinTalk
First #1–70 and #75, #80, #85, #90, #95, #100, #105, #110, #115, #120, #125, #130 private keys have already been cracked.

History
2015-01-15
A transaction was created containing a transfer transaction for 256 different Bitcoin addresses.
2017-07-11
Funds from addresses #161—256 were moved (tx) to the same number of addresses of the lower range – thus increasing the amount of funds on them.
2019-05-31
The creator of the "puzzles" creates outgoing transaction with the value of 1000 satoshi for addresses #65, #70, #75, #80, #85, #90, #95, #100, #105, #110, #115, #120, #125, #130, #135, #140, #145, #150, #155, #160 with the aim of probably comparing the difficulty of finding a private key for the address from which such a transaction was carried out, and one that there is no transaction.
2023-04-16
Somebody (maybe the owner) increased (tx) the unsolved puzzles prizes again by x10. Now the puzzle #66 prize is 6.6 BTC, #67 is 6.7 BTC and so on... puzzle #160 prize is 16 BTC.
2024-09-12
Puzzle #66 (6.6 BTC) was solved by 1Jvv4y (tx1) but the original spending transaction was replaced by bc1qpk (tx2) spending only 5.94 BTC. Finally, another address 15XVN6 took the rest of the prize: 0.66 BTC (tx3).
2025-02-21
Puzzle #67 (6.7 BTC) was solved by bc1qfk and the transaction was mined bypassing the public mempool to avoid interception as in the case of puzzle #66.
2025-04-06
Puzzle #68 (6.8 BTC) was solved by bc1qfw and the transaction was mined bypassing the public mempool to avoid interception as in the case of puzzle #66.
2025-04-30
Puzzle #69 (6.9 BTC) was solved by bc1qlp in less than one month, likely due to its position at the very beginning of the search range (0.72%). However, the original transaction (tx1) was publicly broadcast, leading to it being replaced multiple times (tx2, tx3). Ultimately, 15g7XH managed to steal the prize (tx4).
Solution
In order to solve the puzzle, you must iterate over the specific private key space and check each private key for balance. The narrower the key space, the greater the chance of finding the private key. Currently, it is better to focus on solving puzzle #71 (due to its narrower key space) or #135 (utilizing the Baby-step giant-step or Pollard's kangaroo algorithm because of the exposed public key).

To automate this process, you can utilize the following methods/tools:

Use our GPU Cloud Search solution
Browse private keys directory of the puzzle #71 (not highly effective)
Generate random keys within the key space of the puzzle #71 (not highly effective)
Use Private Key Finder to scan the range of the puzzle #71 in the browser (slow)
Use KeyHunt for CPU search (example)
Use Kangaroo for GPU search puzzles with exposed public key (limited to a 125bit interval search) (example)
Use or BitCrack for GPU search (example)
Join one of the collective solving pools
Links
BitcoinTalk topic #1
BitcoinTalk topic #2
BitcoinTalk topic #3
Overview of key cracking tools for 32BTC puzzle
Related puzzles
Mini-puzzle for puzzle #120 SOLVED
80-bit private key puzzle SOLVED
Mini-puzzle for puzzle #125 SOLVED
Mini-puzzle for puzzle #130 SOLVED
Mini-puzzle #4 SOLVED
Mini-puzzle #5 SOLVED
Addresses & Private Keys  
All
Unsolved
Solved
Bitcoin Puzzle #71 UNSOLVED
  
Key Range (Bits):
270...271
Key Range (HEX):
400000000000000000:7fffffffffffffffff
Bitcoin Address:
C
1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU
 7.10152839
 7.10152839
 33
Bitcoin Puzzle #72 UNSOLVED
  
Key Range (Bits):
271...272
Key Range (HEX):
800000000000000000:ffffffffffffffffff
Bitcoin Address:
C
1JTK7s9YVYywfm5XUH7RNhHJH1LshCaRFR
 7.20014379
 7.20014379
 6
Bitcoin Puzzle #73 UNSOLVED
  
Key Range (Bits):
272...273
Key Range (HEX):
1000000000000000000:1ffffffffffffffffff
Bitcoin Address:
C
12VVRNPi4SJqUTsp6FmqDqY5sGosDtysn4
 7.30013849
 7.30013849
 6
Bitcoin Puzzle #74 UNSOLVED
  
Key Range (Bits):
273...274
Key Range (HEX):
2000000000000000000:3ffffffffffffffffff
Bitcoin Address:
C
1FWGcVDK3JGzCC3WtkYetULPszMaK2Jksv
 7.40004977
 7.40004977
 6
Bitcoin Puzzle #76 UNSOLVED
  
Key Range (Bits):
275...276
Key Range (HEX):
8000000000000000000:fffffffffffffffffff
Bitcoin Address:
C
1DJh2eHFYQfACPmrvpyWc8MSTYKh7w9eRF
 7.6
 7.6
 3
Bitcoin Puzzle #77 UNSOLVED
  
Key Range (Bits):
276...277
Key Range (HEX):
10000000000000000000:1fffffffffffffffffff
Bitcoin Address:
C
1Bxk4CQdqL9p22JEtDfdXMsng1XacifUtE
 7.70002426
 7.70002426
 5
Bitcoin Puzzle #78 UNSOLVED
  
Key Range (Bits):
277...278
Key Range (HEX):
20000000000000000000:3fffffffffffffffffff
Bitcoin Address:
C
15qF6X51huDjqTmF9BJgxXdt1xcj46Jmhb
 7.8
 7.8
 3
Bitcoin Puzzle #79 UNSOLVED
  
Key Range (Bits):
278...279
Key Range (HEX):
40000000000000000000:7fffffffffffffffffff
Bitcoin Address:
C
1ARk8HWJMn8js8tQmGUJeQHjSE7KRkn2t8
 7.9
 7.9
 3
Bitcoin Puzzle #81 UNSOLVED
  
Key Range (Bits):
280...281
Key Range (HEX):
100000000000000000000:1ffffffffffffffffffff
Bitcoin Address:
C
15qsCm78whspNQFydGJQk5rexzxTQopnHZ
 8.100015
 8.100015
 4
Bitcoin Puzzle #82 UNSOLVED
  
Key Range (Bits):
281...282
Key Range (HEX):
200000000000000000000:3ffffffffffffffffffff
Bitcoin Address:
C
13zYrYhhJxp6Ui1VV7pqa5WDhNWM45ARAC
 8.2
 8.2
 3
Bitcoin Puzzle #83 UNSOLVED
  
Key Range (Bits):
282...283
Key Range (HEX):
400000000000000000000:7ffffffffffffffffffff
Bitcoin Address:
C
14MdEb4eFcT3MVG5sPFG4jGLuHJSnt1Dk2
 8.30002046
 8.30002046
 5
Bitcoin Puzzle #84 UNSOLVED
  
Key Range (Bits):
283...284
Key Range (HEX):
800000000000000000000:fffffffffffffffffffff
Bitcoin Address:
C
1CMq3SvFcVEcpLMuuH8PUcNiqsK1oicG2D
 8.400015
 8.400015
 4
Bitcoin Puzzle #86 UNSOLVED
  
Key Range (Bits):
285...286
Key Range (HEX):
2000000000000000000000:3fffffffffffffffffffff
Bitcoin Address:
C
1K3x5L6G57Y494fDqBfrojD28UJv4s5JcK
 8.6
 8.6
 3
Bitcoin Puzzle #87 UNSOLVED
  
Key Range (Bits):
286...287
Key Range (HEX):
4000000000000000000000:7fffffffffffffffffffff
Bitcoin Address:
C
1PxH3K1Shdjb7gSEoTX7UPDZ6SH4qGPrvq
 8.7
 8.7
 3
Bitcoin Puzzle #88 UNSOLVED
  
Key Range (Bits):
287...288
Key Range (HEX):
8000000000000000000000:ffffffffffffffffffffff
Bitcoin Address:
C
16AbnZjZZipwHMkYKBSfswGWKDmXHjEpSf
 8.8
 8.8
 3
Bitcoin Puzzle #89 UNSOLVED
  
Key Range (Bits):
288...289
Key Range (HEX):
10000000000000000000000:1ffffffffffffffffffffff
Bitcoin Address:
C
19QciEHbGVNY4hrhfKXmcBBCrJSBZ6TaVt
 8.9
 8.9
 3
Bitcoin Puzzle #91 UNSOLVED
  
Key Range (Bits):
290...291
Key Range (HEX):
40000000000000000000000:7ffffffffffffffffffffff
Bitcoin Address:
C
1EzVHtmbN4fs4MiNk3ppEnKKhsmXYJ4s74
 9.1
 9.1
 3
Bitcoin Puzzle #92 UNSOLVED
  
Key Range (Bits):
291...292
Key Range (HEX):
80000000000000000000000:fffffffffffffffffffffff
Bitcoin Address:
C
1AE8NzzgKE7Yhz7BWtAcAAxiFMbPo82NB5
 9.2
 9.2
 3
Bitcoin Puzzle #93 UNSOLVED
  
Key Range (Bits):
292...293
Key Range (HEX):
100000000000000000000000:1fffffffffffffffffffffff
Bitcoin Address:
C
17Q7tuG2JwFFU9rXVj3uZqRtioH3mx2Jad
 9.3
 9.3
 3
Bitcoin Puzzle #94 UNSOLVED
  
Key Range (Bits):
293...294
Key Range (HEX):
200000000000000000000000:3fffffffffffffffffffffff
Bitcoin Address:
C
1K6xGMUbs6ZTXBnhw1pippqwK6wjBWtNpL
 9.4
 9.4
 3
Bitcoin Puzzle #96 UNSOLVED
  
Key Range (Bits):
295...296
Key Range (HEX):
800000000000000000000000:ffffffffffffffffffffffff
Bitcoin Address:
C
15ANYzzCp5BFHcCnVFzXqyibpzgPLWaD8b
 9.600006
 9.600006
 4
Bitcoin Puzzle #97 UNSOLVED
  
Key Range (Bits):
296...297
Key Range (HEX):
1000000000000000000000000:1ffffffffffffffffffffffff
Bitcoin Address:
C
18ywPwj39nGjqBrQJSzZVq2izR12MDpDr8
 9.70002613
 9.70002613
 4
Bitcoin Puzzle #98 UNSOLVED
  
Key Range (Bits):
297...298
Key Range (HEX):
2000000000000000000000000:3ffffffffffffffffffffffff
Bitcoin Address:
C
1CaBVPrwUxbQYYswu32w7Mj4HR4maNoJSX
 9.8
 9.8
 3
Bitcoin Puzzle #99 UNSOLVED
  
Key Range (Bits):
298...299
Key Range (HEX):
4000000000000000000000000:7ffffffffffffffffffffffff
Bitcoin Address:
C
1JWnE6p6UN7ZJBN7TtcbNDoRcjFtuDWoNL
 9.91257338
 9.91257338
 7
Bitcoin Puzzle #101 UNSOLVED
  
Key Range (Bits):
2100...2101
Key Range (HEX):
10000000000000000000000000:1fffffffffffffffffffffffff
Bitcoin Address:
C
1CKCVdbDJasYmhswB6HKZHEAnNaDpK7W4n
 10.1
 10.1
 3
Bitcoin Puzzle #102 UNSOLVED
  
Key Range (Bits):
2101...2102
Key Range (HEX):
20000000000000000000000000:3fffffffffffffffffffffffff
Bitcoin Address:
C
1PXv28YxmYMaB8zxrKeZBW8dt2HK7RkRPX
 10.2
 10.2
 3
Bitcoin Puzzle #103 UNSOLVED
  
Key Range (Bits):
2102...2103
Key Range (HEX):
40000000000000000000000000:7fffffffffffffffffffffffff
Bitcoin Address:
C
1AcAmB6jmtU6AiEcXkmiNE9TNVPsj9DULf
 10.3
 10.3
 3
Bitcoin Puzzle #104 UNSOLVED
  
Key Range (Bits):
2103...2104
Key Range (HEX):
80000000000000000000000000:ffffffffffffffffffffffffff
Bitcoin Address:
C
1EQJvpsmhazYCcKX5Au6AZmZKRnzarMVZu
 10.400016
 10.400016
 5
Bitcoin Puzzle #106 UNSOLVED
  
Key Range (Bits):
2105...2106
Key Range (HEX):
200000000000000000000000000:3ffffffffffffffffffffffffff
Bitcoin Address:
C
18KsfuHuzQaBTNLASyj15hy4LuqPUo1FNB
 10.6
 10.6
 3
Bitcoin Puzzle #107 UNSOLVED
  
Key Range (Bits):
2106...2107
Key Range (HEX):
400000000000000000000000000:7ffffffffffffffffffffffffff
Bitcoin Address:
C
15EJFC5ZTs9nhsdvSUeBXjLAuYq3SWaxTc
 10.7
 10.7
 3
Bitcoin Puzzle #108 UNSOLVED
  
Key Range (Bits):
2107...2108
Key Range (HEX):
800000000000000000000000000:fffffffffffffffffffffffffff
Bitcoin Address:
C
1HB1iKUqeffnVsvQsbpC6dNi1XKbyNuqao
 10.8
 10.8
 3
Bitcoin Puzzle #109 UNSOLVED
  
Key Range (Bits):
2108...2109
Key Range (HEX):
1000000000000000000000000000:1fffffffffffffffffffffffffff
Bitcoin Address:
C
1GvgAXVCbA8FBjXfWiAms4ytFeJcKsoyhL
 10.900105
 10.900105
 4
Bitcoin Puzzle #111 UNSOLVED
  
Key Range (Bits):
2110...2111
Key Range (HEX):
4000000000000000000000000000:7fffffffffffffffffffffffffff
Bitcoin Address:
C
1824ZJQ7nKJ9QFTRBqn7z7dHV5EGpzUpH3
 11.1001
 11.1001
 4
Bitcoin Puzzle #112 UNSOLVED
  
Key Range (Bits):
2111...2112
Key Range (HEX):
8000000000000000000000000000:ffffffffffffffffffffffffffff
Bitcoin Address:
C
18A7NA9FTsnJxWgkoFfPAFbQzuQxpRtCos
 11.2
 11.2
 3
Bitcoin Puzzle #113 UNSOLVED
  
Key Range (Bits):
2112...2113
Key Range (HEX):
10000000000000000000000000000:1ffffffffffffffffffffffffffff
Bitcoin Address:
C
1NeGn21dUDDeqFQ63xb2SpgUuXuBLA4WT4
 11.3
 11.3
 3
Bitcoin Puzzle #114 UNSOLVED
  
Key Range (Bits):
2113...2114
Key Range (HEX):
20000000000000000000000000000:3ffffffffffffffffffffffffffff
Bitcoin Address:
C
174SNxfqpdMGYy5YQcfLbSTK3MRNZEePoy
 11.4
 11.4
 3
Bitcoin Puzzle #116 UNSOLVED
  
Key Range (Bits):
2115...2116
Key Range (HEX):
80000000000000000000000000000:fffffffffffffffffffffffffffff
Bitcoin Address:
C
1MnJ6hdhvK37VLmqcdEwqC3iFxyWH2PHUV
 11.6000121
 11.6000121
 4
Bitcoin Puzzle #117 UNSOLVED
  
Key Range (Bits):
2116...2117
Key Range (HEX):
100000000000000000000000000000:1fffffffffffffffffffffffffffff
Bitcoin Address:
C
1KNRfGWw7Q9Rmwsc6NT5zsdvEb9M2Wkj5Z
 11.7
 11.7
 3
Bitcoin Puzzle #118 UNSOLVED
  
Key Range (Bits):
2117...2118
Key Range (HEX):
200000000000000000000000000000:3fffffffffffffffffffffffffffff
Bitcoin Address:
C
1PJZPzvGX19a7twf5HyD2VvNiPdHLzm9F6
 11.80000661
 11.80000661
 4
Bitcoin Puzzle #119 UNSOLVED
  
Key Range (Bits):
2118...2119
Key Range (HEX):
400000000000000000000000000000:7fffffffffffffffffffffffffffff
Bitcoin Address:
C
1GuBBhf61rnvRe4K8zu8vdQB3kHzwFqSy7
 11.9
 11.9
 3
Bitcoin Puzzle #121 UNSOLVED
  
Key Range (Bits):
2120...2121
Key Range (HEX):
1000000000000000000000000000000:1ffffffffffffffffffffffffffffff
Bitcoin Address:
C
1GDSuiThEV64c166LUFC9uDcVdGjqkxKyh
 12.1
 12.1
 3
Bitcoin Puzzle #122 UNSOLVED
  
Key Range (Bits):
2121...2122
Key Range (HEX):
2000000000000000000000000000000:3ffffffffffffffffffffffffffffff
Bitcoin Address:
C
1Me3ASYt5JCTAK2XaC32RMeH34PdprrfDx
 12.2
 12.2
 3
Bitcoin Puzzle #123 UNSOLVED
  
Key Range (Bits):
2122...2123
Key Range (HEX):
4000000000000000000000000000000:7ffffffffffffffffffffffffffffff
Bitcoin Address:
C
1CdufMQL892A69KXgv6UNBD17ywWqYpKut
 12.3
 12.3
 3
Bitcoin Puzzle #124 UNSOLVED
  
Key Range (Bits):
2123...2124
Key Range (HEX):
8000000000000000000000000000000:fffffffffffffffffffffffffffffff
Bitcoin Address:
C
1BkkGsX9ZM6iwL3zbqs7HWBV7SvosR6m8N
 12.4
 12.4
 3
Bitcoin Puzzle #126 UNSOLVED
  
Key Range (Bits):
2125...2126
Key Range (HEX):
20000000000000000000000000000000:3fffffffffffffffffffffffffffffff
Bitcoin Address:
C
1AWCLZAjKbV1P7AHvaPNCKiB7ZWVDMxFiz
 12.6
 12.6
 3
Bitcoin Puzzle #127 UNSOLVED
  
Key Range (Bits):
2126...2127
Key Range (HEX):
40000000000000000000000000000000:7fffffffffffffffffffffffffffffff
Bitcoin Address:
C
1G6EFyBRU86sThN3SSt3GrHu1sA7w7nzi4
 12.7
 12.7
 3
Bitcoin Puzzle #128 UNSOLVED
  
Key Range (Bits):
2127...2128
Key Range (HEX):
80000000000000000000000000000000:ffffffffffffffffffffffffffffffff
Bitcoin Address:
C
1MZ2L1gFrCtkkn6DnTT2e4PFUTHw9gNwaj
 12.8
 12.8
 3
Bitcoin Puzzle #129 UNSOLVED
  
Key Range (Bits):
2128...2129
Key Range (HEX):
100000000000000000000000000000000:1ffffffffffffffffffffffffffffffff
Bitcoin Address:
C
1Hz3uv3nNZzBVMXLGadCucgjiCs5W9vaGz
 12.9
 12.9
 3
Bitcoin Puzzle #131 UNSOLVED
  
Key Range (Bits):
2130...2131
Key Range (HEX):
400000000000000000000000000000000:7ffffffffffffffffffffffffffffffff
Bitcoin Address:
C
16zRPnT8znwq42q7XeMkZUhb1bKqgRogyy
 13.1
 13.1
 3
Bitcoin Puzzle #132 UNSOLVED
  
Key Range (Bits):
2131...2132
Key Range (HEX):
800000000000000000000000000000000:fffffffffffffffffffffffffffffffff
Bitcoin Address:
C
1KrU4dHE5WrW8rhWDsTRjR21r8t3dsrS3R
 13.2
 13.2
 3
Bitcoin Puzzle #133 UNSOLVED
  
Key Range (Bits):
2132...2133
Key Range (HEX):
1000000000000000000000000000000000:1fffffffffffffffffffffffffffffffff
Bitcoin Address:
C
17uDfp5r4n441xkgLFmhNoSW1KWp6xVLD
 13.3
 13.3
 3
Bitcoin Puzzle #134 UNSOLVED
  
Key Range (Bits):
2133...2134
Key Range (HEX):
2000000000000000000000000000000000:3fffffffffffffffffffffffffffffffff
Bitcoin Address:
C
13A3JrvXmvg5w9XGvyyR4JEJqiLz8ZySY3
 13.4
 13.4
 3
Bitcoin Puzzle #135 UNSOLVED
  
Key Range (Bits):
2134...2135
Key Range (HEX):
4000000000000000000000000000000000:7fffffffffffffffffffffffffffffffff
Bitcoin Address:
C
16RGFo6hjq9ym6Pj7N5H7L1NR1rVPJyw2v
 13.50003408
 13.50004408
 8
Public Key:
 02145d2611c823a396ef6712ce0f712f09b9b4f3135e3e0aa3230fb9b6d08d1e16
Bitcoin Puzzle #136 UNSOLVED
  
Key Range (Bits):
2135...2136
Key Range (HEX):
8000000000000000000000000000000000:ffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
1UDHPdovvR985NrWSkdWQDEQ1xuRiTALq
 13.6
 13.6
 3
Bitcoin Puzzle #137 UNSOLVED
  
Key Range (Bits):
2136...2137
Key Range (HEX):
10000000000000000000000000000000000:1ffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
15nf31J46iLuK1ZkTnqHo7WgN5cARFK3RA
 13.7
 13.7
 3
Bitcoin Puzzle #138 UNSOLVED
  
Key Range (Bits):
2137...2138
Key Range (HEX):
20000000000000000000000000000000000:3ffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
1Ab4vzG6wEQBDNQM1B2bvUz4fqXXdFk2WT
 13.8
 13.8
 3
Bitcoin Puzzle #139 UNSOLVED
  
Key Range (Bits):
2138...2139
Key Range (HEX):
40000000000000000000000000000000000:7ffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
1Fz63c775VV9fNyj25d9Xfw3YHE6sKCxbt
 13.9
 13.9
 3
Bitcoin Puzzle #140 UNSOLVED
  
Key Range (Bits):
2139...2140
Key Range (HEX):
80000000000000000000000000000000000:fffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
1QKBaU6WAeycb3DbKbLBkX7vJiaS8r42Xo
 14.000016
 14.000026
 7
Public Key:
 031f6a332d3c5c4f2de2378c012f429cd109ba07d69690c6c701b6bb87860d6640
Bitcoin Puzzle #141 UNSOLVED
  
Key Range (Bits):
2140...2141
Key Range (HEX):
100000000000000000000000000000000000:1fffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
1CD91Vm97mLQvXhrnoMChhJx4TP9MaQkJo
 14.10014846
 14.10014846
 5
Bitcoin Puzzle #142 UNSOLVED
  
Key Range (Bits):
2141...2142
Key Range (HEX):
200000000000000000000000000000000000:3fffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
15MnK2jXPqTMURX4xC3h4mAZxyCcaWWEDD
 14.2
 14.2
 3
Bitcoin Puzzle #143 UNSOLVED
  
Key Range (Bits):
2142...2143
Key Range (HEX):
400000000000000000000000000000000000:7fffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
13N66gCzWWHEZBxhVxG18P8wyjEWF9Yoi1
 14.3
 14.3
 3
Bitcoin Puzzle #144 UNSOLVED
  
Key Range (Bits):
2143...2144
Key Range (HEX):
800000000000000000000000000000000000:ffffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
1NevxKDYuDcCh1ZMMi6ftmWwGrZKC6j7Ux
 14.4
 14.4
 3
Bitcoin Puzzle #145 UNSOLVED
  
Key Range (Bits):
2144...2145
Key Range (HEX):
1000000000000000000000000000000000000:1ffffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
19GpszRNUej5yYqxXoLnbZWKew3KdVLkXg
 14.500006
 14.500016
 6
Public Key:
 03afdda497369e219a2c1c369954a930e4d3740968e5e4352475bcffce3140dae5
Bitcoin Puzzle #146 UNSOLVED
  
Key Range (Bits):
2145...2146
Key Range (HEX):
2000000000000000000000000000000000000:3ffffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
1M7ipcdYHey2Y5RZM34MBbpugghmjaV89P
 14.6
 14.6
 3
Bitcoin Puzzle #147 UNSOLVED
  
Key Range (Bits):
2146...2147
Key Range (HEX):
4000000000000000000000000000000000000:7ffffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
18aNhurEAJsw6BAgtANpexk5ob1aGTwSeL
 14.7
 14.7
 3
Bitcoin Puzzle #148 UNSOLVED
  
Key Range (Bits):
2147...2148
Key Range (HEX):
8000000000000000000000000000000000000:fffffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
1FwZXt6EpRT7Fkndzv6K4b4DFoT4trbMrV
 14.8
 14.8
 3
Bitcoin Puzzle #149 UNSOLVED
  
Key Range (Bits):
2148...2149
Key Range (HEX):
10000000000000000000000000000000000000:1fffffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
1CXvTzR6qv8wJ7eprzUKeWxyGcHwDYP1i2
 14.90001
 14.90001
 4
Bitcoin Puzzle #150 UNSOLVED
  
Key Range (Bits):
2149...2150
Key Range (HEX):
20000000000000000000000000000000000000:3fffffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
1MUJSJYtGPVGkBCTqGspnxyHahpt5Te8jy
 15.000016
 15.000026
 7
Public Key:
 03137807790ea7dc6e97901c2bc87411f45ed74a5629315c4e4b03a0a102250c49
Bitcoin Puzzle #151 UNSOLVED
  
Key Range (Bits):
2150...2151
Key Range (HEX):
40000000000000000000000000000000000000:7fffffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
13Q84TNNvgcL3HJiqQPvyBb9m4hxjS3jkV
 15.10001
 15.10001
 4
Bitcoin Puzzle #152 UNSOLVED
  
Key Range (Bits):
2151...2152
Key Range (HEX):
80000000000000000000000000000000000000:ffffffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
1LuUHyrQr8PKSvbcY1v1PiuGuqFjWpDumN
 15.20001
 15.20001
 4
Bitcoin Puzzle #153 UNSOLVED
  
Key Range (Bits):
2152...2153
Key Range (HEX):
100000000000000000000000000000000000000:1ffffffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
18192XpzzdDi2K11QVHR7td2HcPS6Qs5vg
 15.30001
 15.30001
 4
Bitcoin Puzzle #154 UNSOLVED
  
Key Range (Bits):
2153...2154
Key Range (HEX):
200000000000000000000000000000000000000:3ffffffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
1NgVmsCCJaKLzGyKLFJfVequnFW9ZvnMLN
 15.40001
 15.40001
 4
Bitcoin Puzzle #155 UNSOLVED
  
Key Range (Bits):
2154...2155
Key Range (HEX):
400000000000000000000000000000000000000:7ffffffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
1AoeP37TmHdFh8uN72fu9AqgtLrUwcv2wJ
 15.500116
 15.500126
 8
Public Key:
 035cd1854cae45391ca4ec428cc7e6c7d9984424b954209a8eea197b9e364c05f6
Bitcoin Puzzle #156 UNSOLVED
  
Key Range (Bits):
2155...2156
Key Range (HEX):
800000000000000000000000000000000000000:fffffffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
1FTpAbQa4h8trvhQXjXnmNhqdiGBd1oraE
 15.60001
 15.60001
 4
Bitcoin Puzzle #157 UNSOLVED
  
Key Range (Bits):
2156...2157
Key Range (HEX):
1000000000000000000000000000000000000000:1fffffffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
14JHoRAdmJg3XR4RjMDh6Wed6ft6hzbQe9
 15.70001
 15.70001
 4
Bitcoin Puzzle #158 UNSOLVED
  
Key Range (Bits):
2157...2158
Key Range (HEX):
2000000000000000000000000000000000000000:3fffffffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
19z6waranEf8CcP8FqNgdwUe1QRxvUNKBG
 15.80001
 15.80001
 4
Bitcoin Puzzle #159 UNSOLVED
  
Key Range (Bits):
2158...2159
Key Range (HEX):
4000000000000000000000000000000000000000:7fffffffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
14u4nA5sugaswb6SZgn5av2vuChdMnD9E5
 15.900026
 15.900026
 6
Bitcoin Puzzle #160 UNSOLVED
  
Key Range (Bits):
2159...2160
Key Range (HEX):
8000000000000000000000000000000000000000:ffffffffffffffffffffffffffffffffffffffff
Bitcoin Address:
C
1NBC8uXJy1GiJ6drkiZa1WuKn51ps7EPTv
 16.00119082
 16.00120082
 14
Public Key:
 02e0a8b039282faf6fe0fd769cfbc4b6b4cf8758ba68220eac420e32b91ddfa673
Top Solvers
Solver's Address	# of Solved Puzzles	Total Value
3Emiwzxme7Mrj4d89uqohXNncnRM15YESs	3	 26.7
bc1qlp0z45ctphhz0kywpmw3x2kjy7umhyfawxctah	1	 6.9
bc1qfwpccz2udt3efk7y2wt9l44h34cs5yevjc80lk	1	 6.8
bc1qfk357t8n045f8mwx672rx2re4pftm5gmjzdwq7	1	 6.7
1Jvv4yWkE9MhbuwGUoqFYzDjRVQHaLWuJd	1	 6.6
1AqEgLuT4V2XL2yQ3cCzjMtu1mXtJLVvww	3	 1.68
bc1q6ekza9sv2lngnlazg9pte9rrdf2wkt4xamh83p	1	 1.15
bc1qxwc699tvjxrvn9pprt7haup8vms036mxnxkwmr	1	 1.1
14Dmrxv7cvSFXF7DwrnSspV86DsqzyiUzw	1	 1.05
125CWto9maJWb8eg7HGFrSGQRxFH7rR7PD	1	 1
Bitcoin Challenge Odds Calculator
Puzzle (bits)
71
Total Keys
1180591620717411303424
Search Speed
100
Prefix
GKeys/s (10^9)
The odds of finding a private key within:
Day
136642,549
Week
19520,364
Month
4483,023
Year
374,107
 Premium
☕️ Donate
 Telegram Group
 Privacy Policy
 Contact