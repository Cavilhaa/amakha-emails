# Newsletters Amakha Paris — instruções para o Claude

Este repositório guarda as imagens e o HTML das newsletters da Amakha Paris (amakhaparis.com.br, loja VTEX)
disparadas pelo **Connectif**. As imagens são servidas de graça pelo **jsDelivr** a partir deste repo público.
(O Netlify foi abandonado: a conta gratuita foi restringida por consumo em out/2026.)

## Fluxo para cada news nova
O Cavilha manda: o .zip com as fatias + a arte completa (PNG) + o e-mail da cliente com os links
(banner principal, vitrines, adendo). Às vezes vem uma linha de planilha: `Nome | criação | disparo | link banner | - | link adendo | drive`.

1. **Fatiar** (descobre sozinho a posição de cada fatia na arte, inclusive desalinhamentos de 3px):
   `python3 tools/slice_news.py <zip> <arte.png> emails/AAAA-MM-DD-nome-da-news`
2. **Preencher o `spec.json`**: troque todos os `TODO`
   - `utm` (**padrão MGP**, manual da agência — sem acento, espaço ou caractere que precise codificar):
     `utm_source=connectif` · `utm_medium=email` (minúsculos) ·
     `utm_campaign=MGP_EMAIL_<OBJETIVO>_<ALGO-UTIL>` em MAIÚSCULO e **sem data** (ex.: `MGP_EMAIL_VENDAS_MONTE-SEU-KIT-BF`;
     OBJETIVO: VENDAS, LEADS, TRAFEGO, RECONHECIMENTO, ENGAJAMENTO, REMARKETING, RETENCAO…) ·
     `utm_content=<PECA>_<FORMATO>_<AAMM>` com formato `NEWSLETTER` (ex.: `NEWS-KIT-BF-VITRINES_NEWSLETTER_2611`).
     Disparos da mesma ação = mesma campaign, peça diferente no content. Push web: `utm_medium=web-push`.
     O `build_news.py` recusa UTM fora do padrão.
   - `preheader`: frase curta que complementa o assunto
   - `note`: texto legal da promoção (validade, cupom, valor mínimo) — copie do rodapé do banner
   - cada bloco/célula com `"source"` = qual fatia original; preencha `alt` (texto da imagem) e `href`
   - links do site podem ser só o caminho (`/monte-seu-kit`); a UTM é adicionada sozinha
   - título de seção (ex. "Aproveite antes que acabe!") fica com `href: null`
3. **Montar local e conferir**:
   `python3 tools/build_news.py emails/<news> file://$PWD/emails/<news>/img/`
   `python3 tools/check_news.py emails/<news> <arte.png>`
4. **Publicar as imagens**: `git add emails/<news> && git commit && git push`
5. **Montar final com o commit fixo** (nunca use `@main`: o cache do jsDelivr pode servir versão velha):
   `python3 tools/build_news.py emails/<news> https://cdn.jsdelivr.net/gh/Cavilhaa/amakha-emails@$(git rev-parse HEAD)/emails/<news>/img/`
   e rode o `check_news.py` de novo (agora checa as imagens online). Commit/push do `corpo.html` final.
6. Entregar ao Cavilha o `corpo.html` (como .txt para facilitar o copiar/colar) + o passo a passo do Connectif abaixo.

## Regras que já custaram retrabalho (não pule)
- **Conferir cada vitrine na VTEX** (o `check_news.py` lista): preço "de/por", parcelas, estoque e a
  **inspiração** ("Inspirado por: X") contra o nome do produto no site. A arte da cliente já veio errada
  duas vezes (Affection com "Chloé"; Chic Woman com "Olympéa" quando o site diz Coco Mademoiselle). Avise antes de entregar.
- **Celular**: o layout é fluido (100% até 600px) e não depende do `<style>` do cabeçalho. Nunca volte a largura fixa de 600px.
- **Nada de link relativo** (`#algo`): o Connectif recusa salvar. `mailto:` só gera alerta (sem rastreio) — prefira `/fale-conosco`.
- **Não reutilize nome de arquivo** com conteúdo diferente: e-mails já enviados apontam para esses endereços. Correção de fatia = arquivo novo.
- **Link sem página clara** (ex.: banner de lançamento sem link no e-mail da cliente): use `/lancamentos` ou uma busca do site e **avise** que precisa confirmar.
- Abra a página de destino quando ela não for categoria/produto (ex.: `/kits-presenteaveis` é landing de campanha — renderize para ver se tem produto).
- Não apague nem renomeie nada em `img/` ou `emails/`.

## Connectif (o que o Cavilha faz com o código)
- Criar e-mail → aba **Geral** → *Opções de HTML* → **Cabeçalho**: colar `tools/cabecalho-connectif.html`;
  **desmarcar** "Converter classes CSS em estilos em linha".
- Aba **Componentes** → arrastar bloco **HTML** → colar o `corpo.html`.
- *Pré-cabeçalho e título no navegador*: preencher. Renomear o e-mail no lápis. Salvar.
- Workflows → Criar workflow → **Workflow express → E-mail**: nome `AAAAMMDD - News Nome`, tipo **Boletim**,
  segmento combinado com a cliente, assunto, conteúdo; **Google Analytics desligado** (as UTMs já vão no HTML).
- Teste para o Cavilha e para a cliente antes de agendar. Horários-base: 8h (abertura de ação), 11h30, 19h30 (últimas horas).

## Estrutura
- As news de 02/10 a 01/11/2026 usaram o padrão antigo (`utm_campaign=acao_DDMM`); a partir de 04/11 é o padrão MGP.
- `tools/` — `slice_news.py`, `build_news.py`, `check_news.py`, `cabecalho-connectif.html`
- `emails/<data-nome>/` — `spec.json`, `img/`, `corpo.html` (news feitas com a ferramenta) ou só `corpo.html` (arquivo histórico)
- `img/` — imagens das news de out/2026 (feitas antes da ferramenta). Não mexer.
Dependências: `pip install pillow numpy opencv-python-headless playwright && playwright install chromium`
