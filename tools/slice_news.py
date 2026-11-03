#!/usr/bin/env python3
"""
Fatia uma news da Amakha a partir das fatias enviadas pela Fernanda (zip ou pasta) + a arte completa (PNG/JPG).

Descobre sozinho onde cada fatia fica na arte (template matching), monta as linhas
(header, banners, linhas de vitrines, rodapé), reproduz desalinhamentos/sobreposições da arte
e grava as imagens finais + um spec.json com os links/alts para preencher.

Uso:
  python3 tools/slice_news.py <zip_ou_pasta_das_fatias> <arte_completa.png> <pasta_saida> 
  ex: python3 tools/slice_news.py ~/Downloads/20261101-news.zip ~/Downloads/arte.png emails/20261101-monte-seu-kit-bf

Gera:
  <pasta_saida>/img/*.jpg|png   (as fatias finais, nomes padronizados)
  <pasta_saida>/spec.json       (layout + links; troque todos os "TODO" antes de montar)
"""
import sys, os, json, zipfile, tempfile, io
import numpy as np
import cv2
from PIL import Image

W = 600
HEADER_COLS = [0, 143, 252, 368, 480, 600]
HEADER_LINKS = [('Lançamentos', '/lancamentos'), ('Perfumaria', '/perfume'), ('Amakha Paris', '/'),
                ('Best Sellers', '/queridinhos-da-amakha'), ('Presentes', '/presenteaveis-amakha-paris')]
FOOTERS = {  # alturas conhecidas do rodapé padrão -> faixas verticais de cada parte
    643: dict(depto=(0, 180), benef=(180, 355), contato=(355, 490), social=(490, 570), end=(570, 643)),
    664: dict(depto=(0, 217), benef=(217, 392), contato=(392, 527), social=(527, 607), end=(607, 664)),
}
DEPTO = [('Perfumaria', '/perfume'), ('Cabelo', '/produtos-para-cabelo'),
         ('Nutracêuticos', '/nutricional'), ('Corpo & Banho', '/produtos-para-corpo')]
IG = 'https://www.instagram.com/amakhaoficial/'
SOCIAL = [('Siga a Amakha Paris nas redes sociais', IG), ('Facebook', 'https://www.facebook.com/AmakhaCosmeticosOficial'),
          ('YouTube', 'https://www.youtube.com/c/AmakhaCosm%C3%A9ticosOficial'), ('Instagram', IG), ('', IG)]
SOCIAL_COLS = [0, 282, 362, 440, 520, 600]


def load_slices(src):
    files = {}
    if zipfile.is_zipfile(src):
        with zipfile.ZipFile(src) as z:
            for n in z.namelist():
                if n.endswith('/') or os.path.basename(n).startswith('.'):
                    continue
                if os.path.splitext(n)[1].lower() in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
                    files[os.path.basename(n)] = z.read(n)
    else:
        for n in sorted(os.listdir(src)):
            if os.path.splitext(n)[1].lower() in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
                files[n] = open(os.path.join(src, n), 'rb').read()
    out = []
    for name, data in files.items():
        im = Image.open(io.BytesIO(data))
        animated = getattr(im, 'n_frames', 1) > 1
        im.seek(0)
        rgba = im.convert('RGBA')
        bg = Image.new('RGB', rgba.size, 'white')
        bg.paste(rgba, mask=rgba.split()[3])
        out.append(dict(name=name, raw=data, img=bg, animated=animated, ext=os.path.splitext(name)[1].lower()))
    return out


def locate(art, piece):
    a = cv2.cvtColor(np.array(art), cv2.COLOR_RGB2BGR)
    p = cv2.cvtColor(np.array(piece), cv2.COLOR_RGB2BGR)
    if p.shape[0] > a.shape[0] or p.shape[1] > a.shape[1]:
        return None
    res = cv2.matchTemplate(a, p, cv2.TM_SQDIFF)
    _, _, loc, _ = cv2.minMaxLoc(res)
    x, y = loc
    diff = float(np.abs(a[y:y + p.shape[0], x:x + p.shape[1]].astype(int) - p.astype(int)).mean())
    return x, y, diff


def bg_hex(im):
    a = np.array(im.convert('RGB')).reshape(-1, 3)
    m = np.median(a, axis=0).astype(int)
    return '#%02x%02x%02x' % tuple(m)


def save_best(im, path_noext):
    """Salva em PNG se ficar pequeno (texto/fundo liso) ou JPG se for foto. Retorna nome do arquivo."""
    b1 = io.BytesIO(); im.save(b1, 'PNG', optimize=True)
    b2 = io.BytesIO(); im.save(b2, 'JPEG', quality=86, optimize=True, progressive=True)
    if b1.tell() <= b2.tell() * 1.3:
        data, ext = b1.getvalue(), '.png'
    else:
        data, ext = b2.getvalue(), '.jpg'
    open(path_noext + ext, 'wb').write(data)
    return os.path.basename(path_noext + ext)


def main():
    if len(sys.argv) != 4:
        print(__doc__); sys.exit(1)
    src, art_path, out = sys.argv[1:]
    img_dir = os.path.join(out, 'img'); os.makedirs(img_dir, exist_ok=True)
    art = Image.open(art_path).convert('RGB')
    if art.width != W:
        sys.exit(f'A arte precisa ter {W}px de largura (tem {art.width}).')
    H = art.height
    slices = load_slices(src)
    placed = []
    print(f'Arte {art.size} | {len(slices)} fatias')
    for s in slices:
        r = locate(art, s['img'])
        if r is None:
            print(f'  !! {s["name"]} {s["img"].size} maior que a arte, ignorada'); continue
        x, y, d = r
        s.update(x=x, y=y, w=s['img'].width, h=s['img'].height, diff=d)
        flag = '  <-- CONFERIR (não bate bem com a arte)' if d > 8 else ''
        print(f'  {s["name"]:<22} {s["w"]}x{s["h"]} em x={x} y={y} diff={d:.2f}{flag}')
        placed.append(s)
    # agrupa em blocos verticais
    placed.sort(key=lambda s: (s['y'], s['x']))
    blocks = []
    for s in placed:
        if s['w'] >= W - 2:
            blocks.append(dict(kind='full', pieces=[s], top=s['y']))
        else:
            if blocks and blocks[-1]['kind'] == 'row' and abs(blocks[-1]['top'] - s['y']) <= 8:
                blocks[-1]['pieces'].append(s); blocks[-1]['top'] = min(blocks[-1]['top'], s['y'])
            else:
                blocks.append(dict(kind='row', pieces=[s], top=s['y']))
    # faixa vertical de cada bloco: do topo dele até o topo do próximo (cobre a arte inteira, sem buracos)
    for i, b in enumerate(blocks):
        b['start'] = 0 if i == 0 else b['top']
        b['end'] = H if i == len(blocks) - 1 else blocks[i + 1]['top']
    arr_art = art

    def canvas(x0, x1, y0, y1, pieces):
        """Recorte da arte [x0:x1, y0:y1] com as fatias originais coladas por cima (qualidade original)."""
        c = arr_art.crop((x0, y0, x1, y1)).copy()
        for p in pieces:
            c.paste(p['img'], (p['x'] - x0, p['y'] - y0))
        return c

    spec = dict(utm_campaign='TODO', preheader='TODO', folder='TODO-pasta-curta-ex-bf',
                note='TODO texto legal (validade da promoção) ou deixe vazio',
                art=os.path.basename(art_path), blocks=[])
    n = 1
    for b in blocks:
        y0, y1 = b['start'], b['end']
        hgt = y1 - y0
        p0 = b['pieces'][0]
        if b['kind'] == 'full' and p0['h'] == 88 and p0['y'] <= 2:
            cells = []
            full = canvas(0, W, y0, y1, b['pieces'])
            for i in range(5):
                fn = save_best(full.crop((HEADER_COLS[i], 0, HEADER_COLS[i + 1], hgt)), os.path.join(img_dir, f'{n:02d}-header-{i+1}'))
                cells.append(dict(img=fn, w=HEADER_COLS[i + 1] - HEADER_COLS[i], alt=HEADER_LINKS[i][0], href=HEADER_LINKS[i][1]))
            spec['blocks'].append(dict(type='row', h=hgt, bg=bg_hex(full), cells=cells, role='header'))
        elif b['kind'] == 'full' and p0['h'] in FOOTERS and abs(p0['y'] + p0['h'] - H) <= 4:
            f = FOOTERS[p0['h']]
            full = canvas(0, W, y0, y1, b['pieces'])
            off = p0['y'] - y0  # espaço extra acima do rodapé vai pro primeiro pedaço
            def seg(key, first=False):
                a, z = f[key]; return (0 if first else a + off), (z + off if key != 'end' else hgt)
            a, z = seg('depto', True)
            cells = []
            for i in range(4):
                fn = save_best(full.crop((i * 150, a, (i + 1) * 150, z)), os.path.join(img_dir, f'{n:02d}-depto-{i+1}'))
                cells.append(dict(img=fn, w=150, alt=DEPTO[i][0], href=DEPTO[i][1]))
            spec['blocks'].append(dict(type='row', h=z - a, bg='#ffffff', cells=cells, role='footer-depto')); n += 1
            a, z = seg('benef'); fn = save_best(full.crop((0, a, W, z)), os.path.join(img_dir, f'{n:02d}-beneficios'))
            spec['blocks'].append(dict(type='full', img=fn, w=W, h=z - a, bg='#ffffff', href='/', role='footer',
                                       alt='Só na Amakha Paris: 3% OFF no PIX, frete grátis acima de R$149,90 e parcele em até 6x sem juros')); n += 1
            a, z = seg('contato'); cells = []
            for i, (alt, href) in enumerate([('Nossas lojas - encontre a mais próxima de você', '/institucionais/nossas-lojas'),
                                             ('Entre em contato: suporte@amakhaparis.com.br', '/fale-conosco')]):
                fn = save_best(full.crop((i * 300, a, (i + 1) * 300, z)), os.path.join(img_dir, f'{n:02d}-contato-{i+1}'))
                cells.append(dict(img=fn, w=300, alt=alt, href=href))
            spec['blocks'].append(dict(type='row', h=z - a, bg='#ffffff', cells=cells, role='footer')); n += 1
            a, z = seg('social'); cells = []
            for i in range(5):
                fn = save_best(full.crop((SOCIAL_COLS[i], a, SOCIAL_COLS[i + 1], z)), os.path.join(img_dir, f'{n:02d}-social-{i+1}'))
                cells.append(dict(img=fn, w=SOCIAL_COLS[i + 1] - SOCIAL_COLS[i], alt=SOCIAL[i][0], href=SOCIAL[i][1]))
            spec['blocks'].append(dict(type='row', h=z - a, bg='#ffffff', cells=cells, role='footer')); n += 1
            a, z = seg('end'); fn = save_best(full.crop((0, a, W, z)), os.path.join(img_dir, f'{n:02d}-endereco'))
            spec['blocks'].append(dict(type='full', img=fn, w=W, h=z - a, bg='#ffffff', href=None, role='footer',
                                       alt='Rua Sacramento, 522 - 09640-000 - São Bernardo do Campo - SP - Brasil. CNPJ: 54.101.165/0001-89'))
        elif b['kind'] == 'full':
            if p0['animated'] and p0['y'] == y0 and p0['h'] == hgt:
                fn = f'{n:02d}-banner{p0["ext"]}'; open(os.path.join(img_dir, fn), 'wb').write(p0['raw'])  # mantém o GIF animado
                print(f'  GIF animado mantido: {fn}')
            else:
                if p0['animated']: print(f'  !! {p0["name"]} é GIF animado mas precisou de ajuste: vai estático')
                fn = save_best(canvas(0, W, y0, y1, b['pieces']), os.path.join(img_dir, f'{n:02d}-banner'))
            spec['blocks'].append(dict(type='full', img=fn, w=W, h=hgt, bg=bg_hex(p0['img']), alt='TODO', href='TODO',
                                       source=p0['name']))
        else:
            ps = sorted(b['pieces'], key=lambda p: p['x'])
            edges = [0] + [p['x'] for p in ps[1:]] + [W]
            cells = []
            for i, p in enumerate(ps):
                fn = save_best(canvas(edges[i], edges[i + 1], y0, y1, [p]), os.path.join(img_dir, f'{n:02d}-v{i+1}'))
                cells.append(dict(img=fn, w=edges[i + 1] - edges[i], alt='TODO', href='TODO', source=p['name']))
            spec['blocks'].append(dict(type='row', h=hgt, bg='#ffffff', cells=cells))
        n += 1
    json.dump(spec, open(os.path.join(out, 'spec.json'), 'w'), ensure_ascii=False, indent=2)
    total = sum(bl['h'] for bl in spec['blocks'])
    print(f'\nOK: {len(os.listdir(img_dir))} imagens em {img_dir} | altura total {total}px (arte {H}px)')
    print(f'Agora preencha os "TODO" em {os.path.join(out, "spec.json")} e rode build_news.py')


if __name__ == '__main__':
    main()
