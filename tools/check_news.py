#!/usr/bin/env python3
"""
Confere a news antes de entregar. Rode SEMPRE antes de mandar o código pro Cavilha.

Uso:
  python3 tools/check_news.py <pasta_da_news> <arte_completa.png>

Checa:
  1. Render em 600px igual à arte (diferença média por bloco; > 4 = investigar)
  2. Celular: 375px e 320px sem rolagem lateral e todas as imagens carregando
  3. Todas as imagens respondem 200 (quando a base é https)
  4. Todos os links abrem (200) e nenhum é relativo (o Connectif recusa link relativo)
  5. Vitrines (/p): nome, preço, preço "de", parcelas e estoque direto da VTEX
     -> compare com o que está escrito na arte e com a inspiração ("Inspirado por")
Salva prints em <pasta>/check_600.png, check_375.png, check_320.png
"""
import sys, os, re, json, time, subprocess, urllib.parse
import numpy as np
from PIL import Image

SITE = 'https://www.amakhaparis.com.br'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36'


def http_code(u, tries=4):
    c = '000'
    for _ in range(tries):
        c = subprocess.run(['curl', '-s', '-o', '/dev/null', '-L', '-A', UA, '-w', '%{http_code}', u],
                           capture_output=True, text=True).stdout
        if c == '200': return c
        time.sleep(1.5)
    return c


def vtex(slug):
    u = f'{SITE}/api/catalog_system/pub/products/search/{slug}/p'
    out = subprocess.run(['curl', '-s', '-A', UA, u], capture_output=True, text=True).stdout
    try:
        d = json.loads(out)
    except Exception:
        return None
    if not d: return None
    p = d[0]; o = p['items'][0]['sellers'][0]['commertialOffer']
    ins = max(o.get('Installments', []), key=lambda i: i['NumberOfInstallments'], default={})
    return dict(nome=p['productName'], por=o['Price'], de=o['ListPrice'], estoque=o['AvailableQuantity'],
                parcelas=f"{ins.get('NumberOfInstallments')}x R$ {ins.get('Value')}")


def main():
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(1)
    folder, art_path = sys.argv[1], sys.argv[2]
    s = open(os.path.join(folder, 'corpo.html')).read()
    spec = json.load(open(os.path.join(folder, 'spec.json')))
    problems = []

    # 1-2 render
    from playwright.sync_api import sync_playwright
    prev = 'file://' + os.path.abspath(os.path.join(folder, 'preview.html'))
    with sync_playwright() as p:
        b = p.chromium.launch()
        for w in (600, 375, 320):
            pg = b.new_page(viewport={'width': w, 'height': 800})
            pg.goto(prev); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(1000)
            sw = pg.evaluate('document.documentElement.scrollWidth')
            ok = pg.evaluate('[...document.images].filter(i=>i.naturalWidth>0).length'); tot = pg.evaluate('document.images.length')
            pg.screenshot(path=os.path.join(folder, f'check_{w}.png'), full_page=True)
            print(f'[render {w}px] largura {sw} | imagens {ok}/{tot}')
            if sw > w: problems.append(f'{w}px tem rolagem lateral')
            if ok != tot: problems.append(f'{w}px: {tot-ok} imagem(ns) não carregaram')
        b.close()
    a = np.array(Image.open(os.path.join(folder, 'check_600.png')).convert('RGB')).astype(int)
    r = np.array(Image.open(art_path).convert('RGB')).astype(int)
    a = a[:r.shape[0]]
    if a.shape != r.shape:
        problems.append(f'altura do e-mail ({a.shape[0]}) menor que a arte ({r.shape[0]})')
    else:
        print(f'[arte] diferença média total: {np.abs(a-r).mean():.2f}')
        y = 0
        for i, bl in enumerate(spec['blocks']):
            d = np.abs(a[y:y+bl['h']] - r[y:y+bl['h']]).mean()
            nome = bl.get('role') or (bl.get('img') or bl['cells'][0]['img'])
            flag = '  <-- INVESTIGAR' if d > 4 else ''
            print(f'   bloco {i+1:<2} y={y:<5} h={bl["h"]:<4} diff={d:5.2f}  {nome}{flag}')
            if d > 4: problems.append(f'bloco {i+1} ({nome}) diferente da arte')
            y += bl['h']

    # 3 imagens
    imgs = sorted(set(re.findall(r'<img src="([^"]+)"', s)))
    if imgs and imgs[0].startswith('https://'):
        bad = [u for u in imgs if http_code(u) != '200']
        print(f'[imagens online] {len(imgs)-len(bad)}/{len(imgs)} ok')
        problems += [f'imagem não abre: {u}' for u in bad]
    else:
        print(f'[imagens] {len(imgs)} locais (rode de novo com a base https antes de entregar)')

    # 4 links
    hrefs = list(dict.fromkeys(re.findall(r'<a href="([^"]+)"', s)))
    rel = [h for h in hrefs if not h.startswith('https://')]
    if rel: problems.append(f'links não-https/relativos: {rel}')
    print('[links]')
    for h in hrefs:
        h2 = h.replace('&amp;', '&')
        c = http_code(h2) if 'amakhaparis' in h2 else 'ext'
        print(f'   {c}  {h2.split("utm_")[0].replace(SITE, "").rstrip("?&")}')
        if c not in ('200', 'ext'): problems.append(f'link não abre ({c}): {h2}')
    utms = set(re.findall(r'(utm_source=[^"]+)"', s.replace('&amp;', '&')))
    utms = {re.sub(r'^.*?(utm_source=)', r'\1', x) for x in utms}
    print(f'   UTMs usadas: {utms}')
    if len(utms) > 1: problems.append(f'UTMs diferentes entre links: {utms}')

    # 5 vitrines
    slugs = list(dict.fromkeys(re.findall(r'amakhaparis\.com\.br/([a-z0-9-]+)/p[?"]', s)))
    if slugs:
        print('[vitrines na VTEX] confira com a arte: nome/inspiração, preço, parcelas')
        for sl in slugs:
            v = vtex(sl)
            if not v:
                print(f'   !! {sl}: NÃO ENCONTRADO'); problems.append(f'produto não encontrado: {sl}'); continue
            est = '  <-- ESGOTADO' if v['estoque'] <= 0 else ('  <-- ESTOQUE BAIXO' if v['estoque'] < 20 else '')
            if v['estoque'] <= 0: problems.append(f"produto ESGOTADO no site: {v['nome']}")
            print(f"   {v['nome']} | de R$ {v['de']} por R$ {v['por']} | {v['parcelas']} | estoque {v['estoque']}{est}")

    print('\n' + ('TUDO CERTO' if not problems else 'PROBLEMAS:\n  - ' + '\n  - '.join(problems)))


if __name__ == '__main__':
    main()
