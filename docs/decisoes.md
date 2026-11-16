# Decisões

Registro curto do porquê. Cada uma custou uma tentativa errada antes.

## D1 — Janela crítica dez–jan, não a safra inteira

Primeira versão mediu chuva acumulada de setembro a abril e correlacionou com rendimento:
r = −0,07. Parecia "clima não explica safra", mas era janela errada. Na soja do Paraná,
floração e enchimento de grão caem em dezembro–janeiro; é ali que o veranico quebra lavoura.

Com a janela dez–jan: r = −0,58 para o maior veranico e R² = 0,37 com chuva + veranico.
A safra inteira continua no modelo, mas só como contexto — e para o check de cobertura.

## D2 — 170 municípios, não 399

O POWER responde um ponto por chamada (~1,5 s, com throttle). Os 399 municípios do PR custam
~30 min de download para ganhar 20% de área. O recorte atual pega os municípios em ordem de
área plantada até 80% da área do estado (170 municípios, 4,63 M ha) — número que aparece
no log e é verificado pelo check `cobertura_area`.

Consequência assumida: os 20% restantes (municípios pequenos) ficam fora do fato. A
reconciliação contra o total do estado existe justamente para deixar essa diferença visível
em vez de escondida.

## D3 — Centroide do município como ponto de clima

Alternativa seria a célula de 0,5° do próprio POWER. Centroide é mais legível e permite
dizer "choveu X no município de Tibagi"; a resolução do POWER (0,5° ≈ 55 km) é a mesma coisa
para municípios vizinhos, e isso está no limite conhecido: em município pequeno o ponto pode
estar em célula que representa o vizinho.

## D4 — Bronze cru, inclusive as sentinelas

O SIDRA devolve `-` (sem lavoura), `..` e `...` no mesmo campo numérico. A tentação é converter
tudo para NULL no silver e seguir. Guardamos o texto original e um flag `suprimido`, porque
"não plantou" e "o IBGE não publicou" são coisas diferentes quando alguém pergunta por que
certo município não aparece no gráfico.

## D5 — DuckDB local em vez de Athena + dbt

O objetivo do repositório é rodar em qualquer máquina com `make demo`, sem conta AWS e sem
custo. DuckDB lê a mesma estrutura de partição que o Athena leria, então a migração é trocar
o prefixo de leitura. dbt ficou de fora porque o projeto tem 8 modelos: o ganho de lineage e
testes prontos não paga a dependência, e os testes daqui testam o dado, não o SQL.

## D6 — Regressão pequena, e o R² dito em voz alta

Duas variáveis (chuva e veranico de dez–jan), nos desvios em relação à média do próprio
município. Com 9 safras por município, cada parâmetro extra come um grau de liberdade e o R²
sobe sem significar nada. R² = 0,37 quer dizer: clima explica cerca de um terço da variação
ano a ano; o resto é tecnologia, manejo, cultivar, data de plantio, e erro de medição da
própria PAM.

O que ficaria de fora se eu fosse prever produção: preço na safra anterior (área plantada),
crédito rural, e ENSO (El Niño/La Niña) como variável de contexto.

## D7 — Sem dado sintético e sem código do trabalho

Todos os números vêm de API pública (IBGE + NASA POWER). Nada aqui é cópia de código de
empresa: o que veio do trabalho foi o desenho (bronze/silver/gold em arquivo, orquestração
Airflow, check de reconciliação), que é conhecimento, não código.
