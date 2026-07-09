import hashlib
import struct
import json
import math
import os

SOLVED_PUZZLES = {
    1:  (0x1, 100.0),
    2:  (0x3, 50.0),
    3:  (0x7, 75.0),
    4:  (0x8, 0.0),
    5:  (0x15, 31.25),
    6:  (0x31, 53.13),
    7:  (0x4c, 18.75),
    8:  (0xe0, 75.0),
    9:  (0x1d3, 82.42),
    10: (0x202, 0.39),
    11: (0x483, 12.79),
    12: (0xa7b, 31.01),
    13: (0x1460, 27.34),
    14: (0x2930, 28.71),
    15: (0x68f3, 63.98),
    16: (0xc936, 57.2),
    17: (0x1764f, 46.21),
    18: (0x3080d, 51.57),
    19: (0x5749f, 36.39),
    20: (0xd2c55, 64.66),
    21: (0x1ba534, 72.78),
    22: (0x2de40f, 43.41),
    23: (0x556e52, 33.49),
    24: (0xdc2a04, 72.0),
    25: (0x1fa5ee5, 97.8),
    26: (0x340326e, 62.54),
    27: (0x6ac3875, 66.82),
    28: (0xd916ce8, 69.6),
    29: (0x17e2551e, 49.28),
    30: (0x3d94cd64, 92.44),
    31: (0x7d4fe747, 95.8),
    32: (0xb862a62e, 44.05),
    33: (0x1a96ca8d8, 66.18),
    34: (0x34a65911d, 64.53),
    35: (0x4aed21170, 17.07),
    36: (0x9de820a7c, 23.36),
    37: (0x1757756a93, 45.89),
    38: (0x22382facd0, 6.94),
    39: (0x4b5f8303e9, 17.77),
    40: (0xe9ae4933d6, 82.56),
    41: (0x153869acc5b, 32.63),
    42: (0x2a221c58d8f, 31.67),
    43: (0x6bd3b27c591, 68.48),
    44: (0xe02b35a358f, 75.13),
    45: (0x122fca143c05, 13.67),
    46: (0x2ec18388d544, 46.11),
    47: (0x6cd610b53cba, 70.06),
    48: (0xade6d7ce3b9b, 35.86),
    49: (0x174176b015f4d, 45.35),
    50: (0x22bd43c2e9354, 8.56),
    51: (0x75070a1a009d4, 82.86),
    52: (0xefae164cb9e3c, 87.25),
    53: (0x180788e47e326c, 50.18),
    54: (0x236fb6d5ad1f43, 10.74),
    55: (0x6abe1f9b67e114, 66.79),
    56: (0x9d18b63ac4ffdf, 22.73),
    57: (0x1eb25c90795d61c, 91.85),
    58: (0x2c675b852189a21, 38.76),
    59: (0x7496cbb87cab44f, 82.17),
    60: (0xfc07a1825367bbe, 96.9),
    61: (0x13c96a3742f64906, 23.67),
    62: (0x363d541eb611abee, 69.5),
    63: (0x7cce5efdaccf6808, 95.01),
    64: (0xf7051f27b09112d4, 92.98),
    65: (0x1a838b13505b26867, 65.71),
    66: (0x2832ed74f2b5e35ee, 25.62),
    67: (0x730fc235c1942c1ae, 79.78),
    68: (0xbebb3940cd0fc1491, 49.01),
    69: (0x101d83275fb2bc7e0c, 0.72),
    70: (0x349b84b6431a6c4ef1, 64.4),
    75: (0x4c5ce114686a1336e07, 19.32),
    80: (0xea1a5c66dcc11b5ad180, 82.89),
    85: (0x11720c4f018d51b8cebba8, 9.03),
    90: (0x2ce00bb2136a445c71e85bf, 40.23),
    95: (0x527a792b183c7f64a0e8b1f4, 28.87),
    100:(0xaf55fc59c335c8ec67ed24826, 36.98),
    105:(0x16f14fc2054cd87ee6396b33df3, 43.39),
    110:(0x35c0d7234df7deb0f20cf7062444, 67.98),
    115:(0x60f4d11574f5deee49961d9609ac6, 51.49),
    120:(0xb10f22572c497a836ea187f2e1fc23, 38.33),
    125:(0x1c533b6bb7f0804e09960225e44877ac, 77.03),
    130:(0x33e7665705359f04f28b88cf897c603c9, 62.2),
}

def normalized_position(puzzle_num, key):
    low = 1 << (puzzle_num - 1)
    high = (1 << puzzle_num) - 1
    if high == low:
        return 0.5
    return (key - low) / (high - low)

def extract_byte_entropy(key, n_bytes=4):
    key_bytes = key.to_bytes(max(1, (key.bit_length() + 7) // 8), 'big')
    if len(key_bytes) == 0:
        return 0
    counts = [0] * 256
    for b in key_bytes:
        counts[b] += 1
    total = len(key_bytes)
    entropy = 0
    for c in counts:
        if c > 0:
            p = c / total
            entropy -= p * math.log2(p)
    return entropy

def hamming_weight_ratio(key):
    bits = bin(key).count('1')
    total = key.bit_length()
    if total == 0:
        return 0
    return bits / total

def consecutive_delta(positions):
    deltas = []
    sorted_nums = sorted(positions.keys())
    for i in range(1, len(sorted_nums)):
        curr = sorted_nums[i]
        prev = sorted_nums[i-1]
        if curr - prev == 1:
            deltas.append((curr, positions[curr] - positions[prev]))
        else:
            deltas.append((curr, None))
    return deltas

def nibble_pattern(key, puzzle_num):
    hex_str = format(key, 'x')
    nibbles = [int(c, 16) for c in hex_str]
    return nibbles

def generate_html():
    puzzle_nums = []
    norm_positions = []
    entropies = []
    hamming_ratios = []
    keys_hex = []
    range_pcts = []
    nibble_means = []
    nibble_stds = []
    low_nibble_vals = []

    for num in sorted(SOLVED_PUZZLES.keys()):
        key, pct = SOLVED_PUZZLES[num]
        pos = normalized_position(num, key)
        ent = extract_byte_entropy(key)
        hw = hamming_weight_ratio(key)
        nibs = nibble_pattern(key, num)
        nib_mean = sum(nibs) / len(nibs) if nibs else 0
        nib_std = (sum((n - nib_mean)**2 for n in nibs) / len(nibs))**0.5 if nibs else 0

        puzzle_nums.append(num)
        norm_positions.append(round(pos * 100, 2))
        entropies.append(round(ent, 4))
        hamming_ratios.append(round(hw * 100, 2))
        keys_hex.append(format(key, 'x'))
        range_pcts.append(pct)
        nibble_means.append(round(nib_mean, 2))
        nibble_stds.append(round(nib_std, 2))
        low_nibble_vals.append(key & 0xF)

    deltas = []
    for i in range(len(puzzle_nums)):
        if i == 0:
            deltas.append(0)
        else:
            deltas.append(round(norm_positions[i] - norm_positions[i-1], 2))

    colors_solved_seq = []
    for n in puzzle_nums:
        if n <= 70:
            colors_solved_seq.append(0)
        else:
            colors_solved_seq.append(1)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Bitcoin Puzzle - Mapa 3D secp256k1</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ background: #0a0a0f; color: #e0e0e0; font-family: 'Courier New', monospace; }}
        .header {{ text-align: center; padding: 20px; background: linear-gradient(135deg, #1a1a2e, #16213e); border-bottom: 2px solid #f7931a; }}
        .header h1 {{ color: #f7931a; font-size: 24px; }}
        .header p {{ color: #888; font-size: 12px; margin-top: 5px; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; padding: 10px; }}
        .full {{ grid-column: 1 / -1; }}
        .chart-box {{ background: #111; border: 1px solid #333; border-radius: 8px; padding: 10px; }}
        .chart-box h2 {{ color: #f7931a; font-size: 14px; margin-bottom: 5px; text-align: center; }}
        .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; padding: 10px; }}
        .stat {{ background: #111; border: 1px solid #333; border-radius: 8px; padding: 15px; text-align: center; }}
        .stat .val {{ color: #f7931a; font-size: 24px; font-weight: bold; }}
        .stat .label {{ color: #888; font-size: 11px; margin-top: 5px; }}
        .analysis {{ background: #111; border: 1px solid #333; border-radius: 8px; padding: 15px; margin: 10px; }}
        .analysis h2 {{ color: #f7931a; font-size: 16px; margin-bottom: 10px; }}
        .analysis pre {{ color: #aaa; font-size: 11px; line-height: 1.6; white-space: pre-wrap; }}
        .highlight {{ color: #00ff88; }}
        .warn {{ color: #ff6b6b; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>BITCOIN PUZZLE - ANALISE 3D secp256k1</h1>
        <p>Mapeamento de {len(puzzle_nums)} puzzles resolvidos | Busca por padroes de geracao</p>
    </div>

    <div class="stats">
        <div class="stat">
            <div class="val">{len(puzzle_nums)}</div>
            <div class="label">PUZZLES RESOLVIDOS</div>
        </div>
        <div class="stat">
            <div class="val">{round(sum(norm_positions)/len(norm_positions), 1)}%</div>
            <div class="label">POSICAO MEDIA NO RANGE</div>
        </div>
        <div class="stat">
            <div class="val">{round(sum(hamming_ratios)/len(hamming_ratios), 1)}%</div>
            <div class="label">HAMMING WEIGHT MEDIO</div>
        </div>
        <div class="stat">
            <div class="val">{round(sum(entropies)/len(entropies), 2)}</div>
            <div class="label">ENTROPIA MEDIA (bytes)</div>
        </div>
    </div>

    <div class="grid">
        <div class="chart-box full">
            <h2>MAPA 3D: Puzzle # x Posicao no Range x Hamming Weight</h2>
            <div id="chart3d" style="height:600px;"></div>
        </div>

        <div class="chart-box full">
            <h2>MAPA 3D: Puzzle # x Entropia x Media dos Nibbles</h2>
            <div id="chart3d_2" style="height:600px;"></div>
        </div>

        <div class="chart-box">
            <h2>Posicao Normalizada no Range (%)</h2>
            <div id="chartPos" style="height:400px;"></div>
        </div>

        <div class="chart-box">
            <h2>Hamming Weight Ratio (%)</h2>
            <div id="chartHamming" style="height:400px;"></div>
        </div>

        <div class="chart-box">
            <h2>Delta entre Posicoes Consecutivas</h2>
            <div id="chartDelta" style="height:400px;"></div>
        </div>

        <div class="chart-box">
            <h2>Entropia por Byte da Chave</h2>
            <div id="chartEntropy" style="height:400px;"></div>
        </div>

        <div class="chart-box">
            <h2>Ultimo Nibble (4 bits) da Chave</h2>
            <div id="chartNibble" style="height:400px;"></div>
        </div>

        <div class="chart-box">
            <h2>Distribuicao da Posicao no Range</h2>
            <div id="chartHist" style="height:400px;"></div>
        </div>

        <div class="chart-box full">
            <h2>Heatmap: Nibbles de cada Chave Resolvida</h2>
            <div id="chartHeatmap" style="height:500px;"></div>
        </div>
    </div>

    <div class="analysis">
        <h2>ANALISE DE PADROES</h2>
        <div id="analysisText"></div>
    </div>

    <script>
    const puzzleNums = {json.dumps(puzzle_nums)};
    const normPositions = {json.dumps(norm_positions)};
    const entropies = {json.dumps(entropies)};
    const hammingRatios = {json.dumps(hamming_ratios)};
    const keysHex = {json.dumps(keys_hex)};
    const deltas = {json.dumps(deltas)};
    const nibbleMeans = {json.dumps(nibble_means)};
    const nibbleStds = {json.dumps(nibble_stds)};
    const lowNibbles = {json.dumps(low_nibble_vals)};

    const layout3d = {{
        paper_bgcolor: '#111',
        plot_bgcolor: '#111',
        font: {{ color: '#ccc', family: 'Courier New' }},
        margin: {{ l: 0, r: 0, t: 30, b: 0 }},
        scene: {{
            xaxis: {{ title: 'Puzzle #', color: '#888', gridcolor: '#222' }},
            yaxis: {{ title: 'Posicao no Range (%)', color: '#888', gridcolor: '#222' }},
            zaxis: {{ title: 'Hamming Weight (%)', color: '#888', gridcolor: '#222' }},
            bgcolor: '#0a0a0f'
        }}
    }};

    const layout2d = {{
        paper_bgcolor: '#111',
        plot_bgcolor: '#111',
        font: {{ color: '#ccc', family: 'Courier New', size: 10 }},
        margin: {{ l: 50, r: 20, t: 10, b: 40 }},
        xaxis: {{ title: 'Puzzle #', color: '#888', gridcolor: '#222' }},
        yaxis: {{ color: '#888', gridcolor: '#222' }}
    }};

    // === 3D MAP 1 ===
    Plotly.newPlot('chart3d', [{{
        type: 'scatter3d',
        mode: 'markers+text',
        x: puzzleNums,
        y: normPositions,
        z: hammingRatios,
        text: puzzleNums.map((n,i) => '#' + n),
        textposition: 'top center',
        textfont: {{ size: 8, color: '#888' }},
        marker: {{
            size: 6,
            color: normPositions,
            colorscale: [[0,'#1a1aff'],[0.25,'#00ccff'],[0.5,'#00ff88'],[0.75,'#ffaa00'],[1,'#ff3333']],
            colorbar: {{ title: 'Pos %', thickness: 15 }},
            opacity: 0.9
        }},
        hovertemplate: 'Puzzle #%{{x}}<br>Posicao: %{{y}}%<br>Hamming: %{{z}}%<br>Key: %{{customdata}}<extra></extra>',
        customdata: keysHex
    }},
    {{
        type: 'scatter3d',
        mode: 'lines',
        x: puzzleNums,
        y: normPositions,
        z: hammingRatios,
        line: {{ color: '#f7931a', width: 1, dash: 'dot' }},
        opacity: 0.3,
        showlegend: false,
        hoverinfo: 'skip'
    }}], layout3d);

    // === 3D MAP 2 ===
    const layout3d_2 = JSON.parse(JSON.stringify(layout3d));
    layout3d_2.scene.yaxis.title = 'Entropia (bytes)';
    layout3d_2.scene.zaxis.title = 'Media Nibbles';

    Plotly.newPlot('chart3d_2', [{{
        type: 'scatter3d',
        mode: 'markers',
        x: puzzleNums,
        y: entropies,
        z: nibbleMeans,
        marker: {{
            size: 5,
            color: puzzleNums,
            colorscale: 'Viridis',
            colorbar: {{ title: 'Puzzle #', thickness: 15 }},
            opacity: 0.9
        }},
        hovertemplate: 'Puzzle #%{{x}}<br>Entropia: %{{y}}<br>Nibble Mean: %{{z}}<extra></extra>'
    }}], layout3d_2);

    // === POSICAO ===
    Plotly.newPlot('chartPos', [{{
        type: 'scatter',
        mode: 'markers+lines',
        x: puzzleNums,
        y: normPositions,
        marker: {{ color: '#f7931a', size: 5 }},
        line: {{ color: '#f7931a', width: 1 }}
    }},
    {{
        type: 'scatter',
        mode: 'lines',
        x: [puzzleNums[0], puzzleNums[puzzleNums.length-1]],
        y: [50, 50],
        line: {{ color: '#ff3333', dash: 'dash', width: 1 }},
        name: 'Centro (50%)'
    }}], {{...layout2d, showlegend: false}});

    // === HAMMING ===
    Plotly.newPlot('chartHamming', [{{
        type: 'scatter',
        mode: 'markers+lines',
        x: puzzleNums,
        y: hammingRatios,
        marker: {{ color: '#00ff88', size: 5 }},
        line: {{ color: '#00ff88', width: 1 }}
    }},
    {{
        type: 'scatter',
        mode: 'lines',
        x: [puzzleNums[0], puzzleNums[puzzleNums.length-1]],
        y: [50, 50],
        line: {{ color: '#ff3333', dash: 'dash', width: 1 }},
        name: 'Esperado (50%)'
    }}], {{...layout2d, showlegend: false}});

    // === DELTA ===
    const deltaColors = deltas.map(d => d >= 0 ? '#00ff88' : '#ff6b6b');
    Plotly.newPlot('chartDelta', [{{
        type: 'bar',
        x: puzzleNums,
        y: deltas,
        marker: {{ color: deltaColors }}
    }}], {{...layout2d, showlegend: false}});

    // === ENTROPY ===
    Plotly.newPlot('chartEntropy', [{{
        type: 'scatter',
        mode: 'markers+lines',
        x: puzzleNums,
        y: entropies,
        marker: {{ color: '#aa88ff', size: 5 }},
        line: {{ color: '#aa88ff', width: 1 }}
    }}], {{...layout2d, showlegend: false}});

    // === LOW NIBBLE ===
    const nibbleCounts = Array(16).fill(0);
    lowNibbles.forEach(n => nibbleCounts[n]++);
    Plotly.newPlot('chartNibble', [{{
        type: 'bar',
        x: Array.from({{length:16}}, (_,i) => '0x'+i.toString(16).toUpperCase()),
        y: nibbleCounts,
        marker: {{ color: nibbleCounts.map(c => c > nibbleCounts.reduce((a,b)=>a+b,0)/16 ? '#f7931a' : '#555') }}
    }}], {{...layout2d, showlegend: false}});

    // === HISTOGRAM ===
    Plotly.newPlot('chartHist', [{{
        type: 'histogram',
        x: normPositions,
        nbinsx: 20,
        marker: {{ color: '#f7931a', line: {{ color: '#000', width: 1 }} }}
    }}], {{...layout2d, xaxis: {{...layout2d.xaxis, title: 'Posicao no Range (%)'}}, yaxis: {{...layout2d.yaxis, title: 'Frequencia'}}, showlegend: false}});

    // === HEATMAP ===
    const heatmapData = [];
    const heatmapLabels = [];
    const maxNibbles = 34;
    for (let i = 0; i < keysHex.length; i++) {{
        const nibs = keysHex[i].split('').map(c => parseInt(c, 16));
        while (nibs.length < maxNibbles) nibs.unshift(-1);
        heatmapData.push(nibs.slice(-maxNibbles));
        heatmapLabels.push('#' + puzzleNums[i]);
    }}

    Plotly.newPlot('chartHeatmap', [{{
        type: 'heatmap',
        z: heatmapData,
        y: heatmapLabels,
        colorscale: [[0,'#0a0a0f'],[0.0625,'#1a1a3e'],[0.125,'#1a2a5e'],[0.25,'#0066aa'],[0.5,'#00aa66'],[0.75,'#aaaa00'],[1,'#ff3333']],
        zmin: 0,
        zmax: 15,
        colorbar: {{ title: 'Nibble', thickness: 15 }}
    }}], {{
        ...layout2d,
        margin: {{ l: 60, r: 20, t: 10, b: 40 }},
        xaxis: {{ title: 'Nibble Position (MSB -> LSB)', color: '#888', gridcolor: '#222' }},
        yaxis: {{ color: '#888', gridcolor: '#222', autorange: 'reversed' }}
    }});

    // === ANALYSIS ===
    const avgPos = normPositions.reduce((a,b)=>a+b,0) / normPositions.length;
    const stdPos = Math.sqrt(normPositions.map(p => (p-avgPos)**2).reduce((a,b)=>a+b,0) / normPositions.length);
    const avgHW = hammingRatios.reduce((a,b)=>a+b,0) / hammingRatios.length;

    const posBelow30 = normPositions.filter(p => p < 30).length;
    const posAbove70 = normPositions.filter(p => p > 70).length;
    const posMid = normPositions.filter(p => p >= 30 && p <= 70).length;

    const runs = [];
    let currentRun = {{ dir: normPositions[1] > normPositions[0] ? 'up' : 'down', len: 1 }};
    for (let i = 2; i < normPositions.length; i++) {{
        const dir = normPositions[i] > normPositions[i-1] ? 'up' : 'down';
        if (dir === currentRun.dir) currentRun.len++;
        else {{ runs.push(currentRun); currentRun = {{ dir, len: 1 }}; }}
    }}
    runs.push(currentRun);
    const maxRun = Math.max(...runs.map(r => r.len));

    let autocorr = 0;
    const n = normPositions.length;
    for (let i = 0; i < n - 1; i++) {{
        autocorr += (normPositions[i] - avgPos) * (normPositions[i+1] - avgPos);
    }}
    const variance = normPositions.map(p => (p - avgPos)**2).reduce((a,b)=>a+b,0);
    autocorr = variance > 0 ? autocorr / variance : 0;

    const analysisHTML = `
<pre>
<span class="highlight">== ESTATISTICAS DE POSICAO NO RANGE ==</span>
Media:              ${{avgPos.toFixed(2)}}%  (esperado ~50% para uniforme)
Desvio Padrao:      ${{stdPos.toFixed(2)}}%  (esperado ~28.87% para uniforme)
Autocorrelacao(1):  ${{autocorr.toFixed(4)}}  (esperado ~0 para independente)

Distribuicao:
  < 30%:   ${{posBelow30}} puzzles (${{(posBelow30/n*100).toFixed(1)}}%)
  30-70%:  ${{posMid}} puzzles (${{(posMid/n*100).toFixed(1)}}%)
  > 70%:   ${{posAbove70}} puzzles (${{(posAbove70/n*100).toFixed(1)}}%)

<span class="highlight">== ANALISE DE SEQUENCIA ==</span>
Maior sequencia monotonica:  ${{maxRun}} puzzles consecutivos
Total de runs:               ${{runs.length}}

<span class="highlight">== HAMMING WEIGHT ==</span>
Media:  ${{avgHW.toFixed(2)}}%  (esperado ~50% para aleatorio)
${{Math.abs(avgHW - 50) > 5 ? '<span class="warn">ANOMALIA: Desvio significativo do esperado!</span>' : 'Dentro do esperado para chaves aleatorias.'}}

<span class="highlight">== ULTIMO NIBBLE ==</span>
Distribuicao dos ultimos 4 bits:
${{Array.from({{length:16}}, (_,i) => '  0x' + i.toString(16).toUpperCase() + ': ' + nibbleCounts[i] + ' (' + (nibbleCounts[i]/n*100).toFixed(1) + '%)').join('\\n')}}
Esperado por nibble: ${{(100/16).toFixed(1)}}%
${{Math.max(...nibbleCounts) > n/16 * 2 ? '<span class="warn">ANOMALIA: Distribuicao nao uniforme nos ultimos nibbles!</span>' : 'Distribuicao razoavelmente uniforme.'}}

<span class="highlight">== OBSERVACOES ==</span>
- O criador afirmou usar "chaves consecutivas de uma wallet deterministica"
- Chaves foram mascaradas com 000...0001 para definir a dificuldade
- Se a wallet e BIP32/HD, as chaves derivadas teriam correlacao via HMAC-SHA512
- Padroes nos nibbles ou posicoes podem indicar o esquema de derivacao
- Autocorrelacao ${{Math.abs(autocorr) > 0.3 ? '<span class="warn">SIGNIFICATIVA</span> - possivel correlacao entre chaves adjacentes' : 'baixa - chaves parecem independentes entre si'}}
</pre>`;

    document.getElementById('analysisText').innerHTML = analysisHTML;
    </script>
</body>
</html>"""

    return html

if __name__ == '__main__':
    html = generate_html()
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'puzzle_3d_map.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Mapa 3D gerado: {output_path}")
    print("Abra o arquivo HTML no navegador para visualizar.")
    os.startfile(output_path)
