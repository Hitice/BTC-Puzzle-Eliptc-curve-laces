# Reformulações — Tentativa de Linguagem Matemática Inédita para P = kG

> Nota de pesquisa especulativa. Regras: não usar teoria de grupos, algoritmos publicados, nem
> nada da lista proibida como FUNDAMENTO. Tratar `P = kG` como objeto primitivo do universo.
> Matar ideia apenas por contradição interna. Distinguir o que é construção minha do que é
> observação. Status: exploratório, não estabelecido. O valor é o ENQUADRAMENTO, não um break.

---

## Etapa 0 — Despir o problema até o osso observável

Sem teoria de grupos, o que *observamos* de fato? Apenas isto:

- Existe um conjunto finito **S** de "estados" (os pontos) e um conjunto **K = {0,…,N−1}**.
- Existe um mapa **E: K → S**, bijetivo, computável para frente (barato).
- Existem dois "fluxos" observáveis em S: o **fluxo-sucessor** `σ: P ↦ P+G` e o **fluxo-dobra**
  `δ: P ↦ 2P`. (Não os chamo de "grupo"; são apenas dinâmicas que vejo agir nos estados.)
- A única relação testável entre estados é **igualdade**.

Duas FATOS observados (vou elevá-los a axiomas da minha teoria, não importados de fora):

- **Axioma C (Ciclicidade):** o fluxo-sucessor σ, iterado a partir de qualquer estado, retorna
  ao início após exatamente N passos. S é uma única órbita fechada de σ.
- **Axioma M (Mistura):** qualquer coordenada computável dos estados (x, y, funções delas) não
  exibe correlação suave detectável com a posição na órbita. Estados vizinhos na órbita têm
  coordenadas "distantes" sem gradiente. *(Isto é empírico — testado no nosso domínio #5.)*

---

## Etapa 1 — Objetos tradicionais, e "e se nenhum fosse fundamental?"

Normalmente descrevemos curvas com: pontos (coordenadas), o corpo F_p, a lei de adição, a ordem
N, funções/divisores, o jacobiano, isogenias, torção, emparelhamentos, j-invariante, o grupo
formal, a função zeta, o endomorfismo de Frobenius, parametrização modular.

**E se nenhum for o objeto fundamental?** Hipótese de trabalho: todos esses são *sombras* de uma
estrutura mais simples — a **órbita fechada com mistura** (Axiomas C+M). Os objetos acima seriam
maneiras de coordenar a órbita; a dificuldade não viria deles, mas da tensão C∧M.

---

## Etapas 2–5 — Cinco reformulações, desenvolvidas até quebrar

### R1 — Itinerário dinâmico (k como história de um fluxo)
**Objeto novo:** *assinatura de órbita* σ̂(P) = estrutura do ciclo de P sob o fluxo-dobra δ.
**Axiomas:** δ é uma permutação de S; o ciclo de qualquer P sob δ tem comprimento L = ordem de
"dobrar" sobre a órbita. **Desenvolvimento:** como dobrar = avançar de forma uniforme no índice,
TODOS os estados caem em ciclos de **mesmo** comprimento L. **Consequência interna:** σ̂(P) é
*constante* sobre S → carrega zero informação para distinguir k. **Computável?** Sim. **Preserva
k?** Não. **Volta ao clássico em:** para *usar* o itinerário você teria de contar passos = achar
o log na dinâmica de dobra, que é o mesmo problema numa roupa nova. Morre por **inutilidade**
(homogeneidade), não por contradição.

### R2 — Condição de ressonância (k como frequência)
**Objeto novo:** *campo de coincidência* F(t) = Σ_j Φ(jP) · Φ(−tG), onde Φ é uma fase computável
das coordenadas (ex.: e^{2πi·x(·)/p}). **Sonho:** F(t) teria um pico em t=k → leríamos k por
análise, sem busca. **Desenvolvimento:** um pico em t=k exige que Φ(jP) e Φ(jG) "batam fase"
linearmente em j — isto é, exige que Φ seja um *caractere aditivo* da órbita. **Consequência:**
pelo Axioma M, nenhuma fase de coordenada é aditiva na órbita → F(t) é plano (sem ressonância).
Construir uma Φ aditiva *é* reconstruir a lei de adição. **Volta ao clássico em:** o passo de
exigir Φ aditiva. Morre por **achatamento** (M), salvo se M for falso (ver Etapa 6).

### R3 — Métrica de informação (k por geometria, não por busca)
**Objeto novo:** *potencial de chave* V(P) = uma função real computável das coordenadas, com a
esperança de que ∇V aponte para k. **Axiomas:** V suave; descida de gradiente segue −∇V.
**Desenvolvimento:** pelo Axioma M, a paisagem de qualquer V de coordenadas é um "campo de golfe":
plana em quase todo lugar, com um único buraco em P. Gradiente ≈ 0 em quase toda parte →
descida não tem direção. **Consequência interna:** a métrica induzida por coordenadas é
**degenerada** (gradiente nulo q.t.p.). **Volta ao clássico em:** uma métrica NÃO-degenerada
exigiria que a vizinhança em k correspondesse a vizinhança em V — que é exatamente a estrutura
suave que M nega. Morre por **degenerescência**, salvo se M for falso.

### R4 — Dimensão oculta (k como projeção de um vetor)
**Objeto novo:** *coordenadas partidas* — postular que k é a sombra 1-D de um par (a,b) vivendo
num espaço onde a geometria dá DUAS equações independentes. **Sonho:** duas equações, duas
incógnitas → sistema solúvel. **Desenvolvimento:** de um único P, quantas equações independentes
sobre (a,b) consigo *observar*? Cada homomorfismo independente da órbita dá uma. **Consequência
interna:** a órbita-com-mistura fornece **posto de informação = 1** (só a relação sucessor). Logo
obtenho 1 equação para 2 incógnitas → subdeterminado; o "ganho dimensional" é ilusório. **Volta
ao clássico em:** a segunda equação nunca materializa sem uma segunda estrutura independente.
Morre por **posto-1 de informação**.

### R5 — k como duração (a órbita como linha de tempo)
**Objeto novo:** *monovariante* μ: S → ℝ, estritamente crescente ao longo do fluxo-sucessor:
μ(P+G) > μ(P) para todo P. **Sonho:** se μ existe e é computável, k = posição de μ(P) no
ranqueamento → leitura direta por comparação. **Desenvolvimento:** μ estritamente crescente ao
longo de σ implica μ(0) < μ(G) < … < μ((N−1)G) < μ(NG). Mas pelo **Axioma C**, NG = 0, logo
μ(NG) = μ(0). Teríamos μ(0) < μ(0). **Contradição interna.** **Consequência:** nenhum
monovariante real existe sobre uma órbita fechada. Morre por **CONTRADIÇÃO LÓGICA PURA** — a
ciclicidade proíbe qualquer relógio monótono. (Esta é a única que morre sem apelo a M.)

---

## Síntese — uma estrutura sem nome: "Rigidez Cíclica da Informação"

Todas as cinco batem no mesmo muro, mas o muro **não é** "teoria de grupos". É a tensão entre os
dois axiomas observados:

> **Rigidez Cíclica (proposta):** Numa órbita fechada (C) com mistura de coordenadas (M), a única
> estrutura relacional que a órbita carrega é o *sucessor*, e essa relação é embaralhada em toda
> coordenada computável. Consequências:
> - Nenhum monovariante global (C mata R5).
> - Nenhuma métrica/gradiente local (M mata R3).
> - Nenhuma ressonância analítica (M mata R2).
> - Nenhuma dimensão extra de informação: posto = 1 (R4).
> - Nenhuma dinâmica localizante: homogênea (R1).

O ECDLP "clássico" é então apenas o **nome tradicional** de tentar realizar a relação-sucessor
explicitamente. Ele reaparece sempre no passo em que a reformulação precisa *ligar sucessão em k
a algo computável* — e C∧M proíbem essa ligação a não ser pela própria adição.

**Onde isto é honesto:** derivei o muro de DOIS fatos observáveis (periodicidade + mistura), sem
importar nenhum teorema da lista proibida. **Onde isto é frágil:** o Axioma M é *empírico*, não
provado. R2/R3/R4 morrem por M; só R5 morre por contradição pura (C). Portanto:

> **O único lugar onde a teoria pode estar errada é o Axioma M.** Se M for falso — se existir UMA
> coordenada computável com correlação real com a sucessão — R2/R3/R4 ressuscitam.

---

## Etapa 6 — A hipótese mais promissora e como falsificá-la

**Hipótese escolhida:** *Existe um funcional de coordenada g, computável só da chave pública, tal
que g(kG) tem dependência estatística não-nula com k que persiste ao crescer N.* (= negação de M.)

Por que merece investigação: é o **único** elo não fechado por contradição pura; é o mesmo
resíduo empírico do nosso domínio #5 (incompressibilidade do gerador), agora reformulado de
"as chaves são aleatórias?" para "**o fluxo-sucessor tem algum invariante de coordenada
não-plano?**" — uma pergunta sobre a CURVA, não sobre o gerador. Ninguém, que eu saiba, ataca
assim.

**Experimentos falsificáveis (baratos, em curvas-brinquedo onde computo tudo):**
1. **Varredura de informação mútua:** curvas de ordem pequena (N ~ 2¹⁶–2²⁴, primo). Para uma
   bateria de funcionais g (momentos de x, paridades, somas parciais de dígitos, funções de
   (x·y), distâncias de campo a constantes…), medir I(g(kG); k) varrendo todo k. Se I≈0 para
   todos g e todos N → M sustentado. Se algum g dá I>0 que **cresce ou persiste** com N → lead
   real.
2. **Teste de equivariância:** procurar g com g((k+1)G) − g(kG) aproximadamente constante (um
   "quase-monovariante local"). C proíbe global; mas um *local* não-plano violaria M.
3. **Curvas primas vs. compostas:** repetir em N composto (onde C se quebra em sub-órbitas) como
   *controle positivo* — confirmar que a metodologia DETECTA estrutura quando ela existe, antes
   de confiar nos nulos em N primo.

**Resultado esperado (honesto):** I≈0 em N primo (consistente com tudo). Mas o *enquadramento* —
"caçar um invariante de coordenada do fluxo-sucessor" — é uma representação que a matemática atual
não nomeia, e o experimento 3 dá um controle que torna o nulo informativo em vez de vazio.

---

## Resposta direta: como uma simetria oculta se manifestaria nos pontos públicos?

Dentro desta teoria, uma simetria invisível só pode aparecer como **violação de C ou de M**:

- **Violação de C (estrutural):** o fluxo-sucessor ou o fluxo-dobra teriam **sub-órbitas** mais
  curtas que N → a ordem fatoraria, ou existiria um auto-mapa não-trivial levando pontos públicos
  uns nos outros. *Em secp256k1, N é primo* → C é maximamente satisfeito; nenhuma sub-órbita.
  **Exceção honesta:** existe UM auto-mapa observado (multiplicar k por uma constante fixa λ). Ele
  É uma simetria real — mas é um *automorfismo da órbita* (permuta estados preservando sucessão),
  então embaralha sem localizar: leva o problema em k para o mesmo problema em λk. Dentro da
  teoria, ele preserva a Rigidez Cíclica em vez de quebrá-la.
- **Violação de M (estatística):** algum funcional de coordenada g(P) seria **não-uniforme ou
  não-plano** ao longo da órbita — uma "impressão digital" mensurável nos pontos públicos.
  **É exatamente o que o experimento 1 procura.** Uma simetria oculta se manifestaria como um
  g com I(g(kG);k) > 0 estável — uma textura nas coordenadas que correlaciona com a posição.

**Síntese da resposta:** se secp256k1 escondesse uma simetria que toda a literatura perdeu, ela
apareceria como **um invariante de coordenada não-plano sob o fluxo-sucessor** (textura
estatística nos pontos públicos) ou como **um automorfismo além do λ conhecido** (sub-estrutura
na órbita). A ordem prima fecha a segunda porta; a primeira é empírica, parcialmente testada,
e é o único lugar onde vale a pena olhar com olhos novos.

---

# Autocrítica — Redução Axiomática (a teoria acima está parcialmente ERRADA)

> Exercício: assumir que a teoria está errada e achar o MENOR conjunto de hipóteses a modificar
> para uma teoria sobreviver. Resultado: **um axioma (C) não faz trabalho obstrutivo independente.**

## 3+4 primeiro (são a alavanca): a prova do monovariante estava viciada

R5 "matou" o monovariante por contradição pura: μ(0) < μ(G) < … < μ(NG)=μ(0). Mas essa prova usa
**três** coisas, e eu só declarei duas:
- C (NG = 0) — declarado.
- "estritamente crescente" = ordem estrita transitiva — declarado implicitamente.
- **o contradomínio é ℝ (ordem LINEAR)** — *não declarado*. ← o pecado.

**Generalizando o contradomínio (Etapa 4):**

| Contradomínio | A contradição sobrevive? | Por quê |
|---------------|--------------------------|---------|
| ℝ / ordem total | **Sim** | cadeia fechada força x < x |
| Poset (ordem parcial) | **Sim** | passos-σ comparáveis-e-maiores ainda formam cadeia; cadeia fechada = contradição |
| Tournament / relação **não-transitiva** | **Não** | ciclos são consistentes (pedra-papel-tesoura); mas só dá comparador *local* → andar N passos = força bruta |
| **Círculo / fase ℝ/ℤ / e^{2πik/N}** | **Não** | μ(P) = k/N envolve perfeitamente, sem contradição. **O monovariante EXISTE.** |
| Categoria cíclica / torsor | **Não** | é o próprio coordenada-torsor; existe |

**Conclusão demolidora:** a contradição de R5 era um **artefato de eu ter escolhido ℝ**. O
contradomínio NATURAL de um fluxo cíclico é cíclico (uma fase). Nele o monovariante canônico
**existe**: `μ(P) = e^{2πik/N}`. Ele não viola C — ele *gira* com C. Logo **C não proíbe
monovariante.** O que impede de usá-lo é que μ(P) = (a fase de k) **não é computável de P barato**
— isto é, **M**. A barreira migra de "lógica (C)" para "complexidade (M)".

## 1+2: M é independente de C? Existe axioma mais profundo?

Reescrevendo o que C e M realmente são, à luz do acima:
- **C** = "S é um *torsor* sobre ℤ/Nℤ via σ" — uma única órbita homogênea. **Fato estrutural**,
  só sobre o domínio.
- **M** = "a coordenada-torsor canônica (a fase de k) não é eficientemente computável a partir da
  representação ambiente (coordenadas em F_p)". **Fato de complexidade**, sobre a *relação*
  domínio↔representação.

Ambos são consequências de um objeto mais fundamental — a **imersão** ι: (torsor abstrato) ↪
(coordenadas F_p²):
- C ⇐ ι é morfismo de torsor (homogeneidade algébrica).
- M ⇐ ι é *embaralhadora* (a fase e as coordenadas de campo não têm refinamento comum eficiente).

**Mas C e M são consequências de propriedades de tipos lógicos DIFERENTES de ι:** C é
**extensional/estrutural** (o que o objeto É); M é **intensional/computacional** (quão difícil é
computar *através* dele). Um torsor abstrato ℤ/Nℤ tem log discreto TRIVIAL (k é o próprio
elemento) — toda a dureza vem da *imersão*, não da estrutura.

## 6: redução mínima — e por que C e M NÃO colapsam em um

Conjunto mínimo de axiomas:
- **A1 (Torsor):** S ≅ ℤ/Nℤ como σ-torsor. ⟹ C; ⟹ a fase canônica existe.
- **A2 (Imersão embaralhadora):** a fase canônica não é poli-computável da representação ambiente.
  ⟹ M.

**Por que a independência é inevitável:** A1 é uma afirmação *estrutural*; A2 é uma afirmação de
*complexidade*. **Nenhum fato estrutural implica um fato de dureza sem injetar uma hipótese de
complexidade.** (É o mesmo abismo de P vs NP: estrutura não entrega dureza de graça.) Logo A2
não se deriva de A1. A independência não é entre "C e M como obstruções" — é entre **estrutura e
complexidade como tipos lógicos**. Esse é o limite real.

## 5: onde assumi matemática clássica sem perceber

1. **Contradomínio = ℝ** (ordem linear) — o erro central; matou R5 indevidamente.
2. **"Computável" = Turing/poli-tempo** — uma escolha de modelo, não um dado.
3. **S como conjunto com só igualdade** — ignorei a topologia/estrutura fraca de F_p.
4. **σ-equivariância exata** (homomorfismo) — M é também sobre aproximação *estatística*, não só exata.
5. **Origem canônica** (G fixo) — torsor não tem origem; a escolha de G é *gauge*.

## A teoria que sobrevive (menor modificação)

**Descartar C como obstrução.** Ela não faz trabalho independente — só sinalizava que eu usava o
contradomínio errado. A teoria correta tem **uma única barreira operativa: A2 (M)** — a fase
canônica `e^{2πik/N}` existe e gira com a órbita; tudo se resume a *ela ser computacionalmente
inacessível da representação*.

**Consequência prática (afia o experimento):** não procuramos "qualquer estrutura". Procuramos
**uma aproximação poli-computável da fase canônica** — um funcional g(P) tal que g(kG) ≈ função
de e^{2πik/N} com erro melhor que aleatório. É exatamente a violação de A2. O experimento de
informação mútua (Etapa 6) vira: *medir se algum g(P) computável tem dependência com a fase k/N*,
com controle positivo em N composto. A autocrítica **convergiu no mesmo experimento, com
justificativa mais limpa e um alvo nomeado** (a fase canônica), em vez de "procurar algo".

> **Saldo da autocrítica:** a teoria encolheu de 2 axiomas-obstrução (C, M) para 1 (A2). C virou
> descrição (A1), não barreira. A pergunta final do universo, destilada: *a fase de k é uma
> sombra computável das coordenadas de P?* Se sim (A2 falso), tudo muda. A2 nunca foi teorema —
> é hipótese empírica, e agora **mensurável** (ver experimento abaixo).

---

# Experimento — A2 medido: incompressibilidade da órbita

> Operacionaliza A2 como hipótese falsificável (sugestão do revisor: trocar "log discreto" por
> "compressibilidade da órbita"). Script: `orbit_compressibility.py`. Curva-brinquedo de **ordem
> prima** onde computo k de todo ponto. Detectores calibrados por **controle positivo**.

## A2 em três formas mensuráveis (para um funcional g: E(F_p) → ℝ)
- (i) **fase:** potência de corr(g(P_k), e^{2πi m k/N}) nos harmônicos m=1..24 ≈ ruído χ²(2);
- (ii) **informação mútua:** I(g(P_k); bit de k) ≈ 0;
- (iii) **predição de bit:** acurácia de prever um bit de k a partir de g ≤ ½ + ε;
- (iv) **dinâmica (Δ):** var(g(P_{k+1}) − g(P_k)) / 2var(g) ≈ 1 (sem suavidade na sucessão).

## Resultado (curva y²=x³+7, p=20143, N=20359 primo)

| | Controles positivos | Funcionais da curva (13) |
|---|---|---|
| Disparos | **4/4** (LSB(k), rampa, 3k mod N, cos) | **0/13** |
| Fase z | 12 376 – 20 358 | 3.5 – 19.9 (≈ máx de 24 χ²(2)) |
| MI (bit) | até 1.0000 | ≤ 0.0006 (piso de amostra) |
| Δ-suavidade | 0.000 – 0.001 | 0.98 – 1.01 (=aleatório) |

Funcionais testados: x, y, x+y, x·y, x²+y², legendre(x/y), lsb(x/y), x(2P), x(3P), x(5P), x(7P).

**Leitura:** nenhum funcional da classe correlaciona com a fase de k acima do acaso, **enquanto**
os controles positivos disparam ordens de grandeza acima. Logo o nulo é **informativo**, não
cegueira de detector. Troca de "ninguém achou" (sociológico) por "testamos 13 funcionais × 24
harmônicos + MI + predição-de-bit + Δ, todos compatíveis com o acaso, com controle positivo
validado" (experimental).

## Caveats honestos (limites desta evidência)
1. **Uma escala** (N≈2·10⁴). A persistência ao crescer N é o próximo passo *obrigatório* — uma
   rachadura real teria de sobreviver (ou crescer) com N. Pendência.
2. **Classe finita e humana** de funcionais (famílias 1–3 + harmônicos + bit/Δ). Não cobre ML
   (família 5, requer dependências) nem "todo funcional computável" (= K(x), incomputável).
3. Corrobora A2 **nesta escala**; não prova A2 para secp256k1. A2 segue empírico, agora com
   evidência positiva de ausência-de-correlação em vez de argumento de autoridade.

## Varredura de escala — A2 testada de 2¹¹ a 2¹⁶ (`scale_sweep.py`)

Repetição em curvas primas crescentes. Máximo de cada detector sobre os funcionais da curva:

| bits | N | fase | MI | adv | \|Δ−1\| | **fase (controle)** |
|---|---|---|---|---|---|---|
| 11 | 2143 | 12.7 | 0.0021 | 0.0163 | 0.0882 | 1302 |
| 12 | 4243 | 11.3 | 0.0026 | 0.0299 | 0.0427 | 2579 |
| 13 | 8293 | 13.8 | 0.0004 | 0.0089 | 0.0284 | 5041 |
| 14 | 16693 | 22.0 | 0.0002 | 0.0057 | 0.0184 | 10148 |
| 15 | 32497 | 10.6 | 0.0003 | 0.0053 | 0.0123 | 19755 |
| 16 | 65173 | 9.6 | 0.0001 | 0.0038 | 0.0074 | 39620 |

**Leitura:** os detectores da curva seguem **exatamente** a previsão de A2 — fase **achatada**
(~10–22, sem crescer), MI/adv/|Δ−1| **decrescem** com N. O ponto decisivo: a fase do **controle
positivo cresce ∝ N** (1302→39620) — ou seja, o poder do detector AUMENTA com a escala (o SNR de
um sinal real cresce com a amostra), e *mesmo assim* nada aparece na curva. O nulo não é detector
fraco; é detector cada vez mais forte vendo ausência. A2 corroborada **multi-escala**.

### Extensão a 2¹⁸–2²⁰ (`gpu_orbit_sweep.py`, detectores vetorizados)

Mesma ciência, detectores vetorizados (validados: bits=16 reproduz a tabela acima). Estendido
até N≈10⁶:

| bits | N | fase | MI | sep | \|Δ−1\| | fase (controle) |
|---|---|---|---|---|---|---|
| 16 | 65173 | 9.6 | 0.0001 | 0.0136 | 0.0074 | 39 622 |
| 18 | 262567 | 17.2 | 0.0001 | 0.0055 | 0.0056 | 159 623 |
| 20 | 1050337 | 9.6 | 0.0000 | 0.0016 | 0.0015 | 638 530 |

**Expoentes (lei de potência, N: 65k→1.05M, fator 16×):**
- fase (curva): **N^0** (achatada) — ruído, como previsto.
- sep (curva): **~N^−0.77** (decresce ainda mais rápido que 1/√N).
- |Δ−1| (curva): **~N^−0.57** (≈ 1/√N).
- fase (**controle**): **N^+1.0** exato — poder do detector ∝ N.

Contraste decisivo: o poder do detector cresceu **16×** (39 622 → 638 530) enquanto a fase da
curva ficou plana (~10–17). Detectores 16× mais fortes, ausência persistente. A2 corroborada
até ~10⁶ pontos. (Execução em CPU; GPU/CuPy permitiria 2²²⁺.)

## Teste de fechamento — A2 na secp256k1 REAL por amostragem (`secp_window_sample.py`)

Enumerar é impossível além de ~2²⁰; por amostragem (S=40000 chaves/janela, mult. escalar na
curva real, sem armazenar a órbita) testamos janelas até 2⁴⁰:

| janela | fase (curva) | MI | sep | fase (controle) | MI (controle) |
|---|---|---|---|---|---|
| 2²⁰ | 8.5 | 0.0002 | 0.0291 | 24 535 | 1.0000 |
| 2³⁰ | 10.4 | 0.0001 | 0.0177 | 23 958 | 1.0000 |
| 2⁴⁰ | 10.8 | 0.0002 | 0.0177 | 24 486 | 1.0000 |

Curva silenciosa nas três; controles disparando ordens de grandeza acima. **Importante:** a
resolução é fixada por √S (≈200), não pela largura da janela — então isto testa "há correlação
de algum funcional com a fase de k *através* de uma janela de até 2⁴⁰?" na curva-alvo. Resposta:
não. A largura não cria sinal — consistente com A2. (Não usa GPU: 256 bits → CPU.)

> **O que este teste NÃO é:** não é progresso para *resolver* o puzzle. É confirmação cada vez
> mais rigorosa do nulo — de que não há atalho. Continuar aumentando S ou a janela só reconfirma
> o mesmo nulo. O valor é metodológico (evidência quantitativa de incompressibilidade), não
> operacional (não chega a uma chave).

## Limites que permanecem (honestidade)
- Escala-brinquedo: 2¹⁶ ainda está ~51 bits abaixo do intervalo de #135 e ~240 de 2²⁵⁶.
  A extrapolação é indutiva (forte: 6 escalas, tendência limpa) — não é prova.
- Classe finita de funcionais (sem ML). Cobre famílias 1–3 + harmônicos + bit/Δ; não é "todo
  funcional computável" (= K(x), incomputável).
- Corrobora A2; não a prova para secp256k1. Mas troca definitivamente "ninguém achou" por uma
  **tendência quantitativa multi-escala com controle de poder**.

## Próximo passo (se quiser empurrar)
- Estender a 2¹⁸–2²⁰ (custo: EC puro fica lento; ~10–30 min).
- Acrescentar família ML (regressão/rede pequena) como detector universal — requer dependência.
- Ajustar reta log-log dos detectores vs N e reportar os expoentes (confirmar ∝1/√N e ∝1/N).
