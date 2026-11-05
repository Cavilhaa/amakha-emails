#!/usr/bin/env python3
"""
Monta o HTML da news (corpo para colar no bloco HTML do Connectif) a partir do spec.json.

Uso:
  python3 tools/build_news.py <pasta_da_news> <url_base_das_imagens>
  ex (teste local):  python3 tools/build_news.py emails/20261101-bf file:///caminho/emails/20261101-bf/img/
  ex (final):        python3 tools/build_news.py emails/20261101-bf https://cdn.jsdelivr.net/gh/Cavilhaa/amakha-emails@<COMMIT>/emails/20261101-bf/img/

Gera na pasta da news:
  corpo.html    -> o que vai no bloco HTML do Connectif
  preview.html  -> página completa para conferir no navegador (sem o <style>, simula o pior caso)
Regras embutidas: layout fluido (100% até 600px), tabelas, sem link relativo, UTM em todo link do site.
Opcional por bloco/célula: "term" (vira utm_term) e "base" (URL jsDelivr de imagem já hospedada em outra news).
"""
import sys, os, json, html

SITE = 'https://www.amakhaparis.com.br'
STYLE = '''<style type="text/css">
  body{margin:0!important;padding:0!important;width:100%!important;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;}
  table,td{border-collapse:collapse;mso-table-lspace:0pt;mso-table-rspace:0pt;}
  img{border:0;outline:none;text-decoration:none;-ms-interpolation-mode:bicubic;display:block;}
  a img{border:0;}
  a[x-apple-data-detectors]{color:inherit!important;text-decoration:none!important;font-size:inherit!important;font-family:inherit!important;font-weight:inherit!important;line-height:inherit!important;}
  u + #body a{color:inherit;text-decoration:none;}
  @media only screen and (max-width:620px){
    .amk-wrapper{width:100%!important;max-width:100%!important;}
    .amk-wrapper img{width:100%!important;height:auto!important;}
  }
</style>'''


def main():
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(1)
    folder, base = sys.argv[1], sys.argv[2]
    if not base.endswith('/'): base += '/'
    spec = json.load(open(os.path.join(folder, 'spec.json')))
    todos = [k for k in ('preheader', 'note', 'utm_campaign', 'utm_content') if 'TODO' in str(spec.get(k, ''))]
    todos += [f'utm.{k}' for k, v in (spec.get('utm') or {}).items() if 'TODO' in str(v)]
    for i, b in enumerate(spec['blocks']):
        for c in (b.get('cells') or [b]):
            for k in ('alt', 'href'):
                if 'TODO' in str(c.get(k)): todos.append(f'bloco {i+1} {c.get("img")} {k}')
    if todos:
        sys.exit('Ainda tem TODO no spec.json:\n  ' + '\n  '.join(todos))
    # Padrão MGP (manual da agência): source/medium minúsculos; campaign MGP_EMAIL_<OBJETIVO>_<ALGO-UTIL> em MAIÚSCULO,
    # sem data; content <PECA>_<FORMATO>_<AAMM>. Sem acento, espaço ou caractere especial (nada que precise codificar).
    import re as _re
    u = spec.get('utm') or {k: spec[k] for k in ('utm_source', 'utm_medium', 'utm_campaign', 'utm_content') if spec.get(k)}
    u.setdefault('utm_source', 'connectif'); u.setdefault('utm_medium', 'email')
    u = {k: u[k] for k in ('utm_source', 'utm_medium', 'utm_campaign', 'utm_content') if u.get(k)} | {k: v for k, v in u.items() if k not in ('utm_source', 'utm_medium', 'utm_campaign', 'utm_content')}
    for k, v in u.items():
        if not v or not _re.fullmatch(r'[A-Za-z0-9_-]+', str(v)):
            sys.exit(f'UTM fora do padrão MGP ({k}={v!r}): só letras sem acento, números, _ e -')
    if u.get('utm_source') != u['utm_source'].lower() or u.get('utm_medium') != u['utm_medium'].lower():
        sys.exit('utm_source e utm_medium precisam ser minúsculos')
    if not u.get('utm_campaign', '').startswith('MGP_') or u['utm_campaign'] != u['utm_campaign'].upper():
        print('AVISO: utm_campaign fora do padrão MGP_<ORIGEM>_<OBJETIVO>_<ALGO-UTIL> em maiúsculo (ok só se for exceção combinada com o cliente)')
    utm = '&'.join(f'{k}={v}' for k, v in u.items())

    def link(h, term=None):
        if not h: return None
        if h.startswith('/'):
            h = SITE + h
        if not h.startswith('https://'):
            sys.exit(f'Link inválido (precisa ser https:// ou começar com /): {h}')
        if h.startswith(SITE):
            if term and not _re.fullmatch(r'[A-Za-z0-9_-]+', term):
                sys.exit(f'utm_term fora do padrão MGP: {term!r}')
            h += ('&' if '?' in h else '?') + utm + (f'&utm_term={term}' if term else '')
        return h

    def img(c, h, bg):
        a = html.escape(c.get('alt') or '', quote=True)
        b_ = c.get('base') or base  # "base" no spec = imagem já hospedada em outra news (reaproveitada)
        if not b_.endswith('/'): b_ += '/'
        if c.get('base') and not b_.startswith('https://cdn.jsdelivr.net/gh/Cavilhaa/amakha-emails@'):
            sys.exit(f'base por imagem precisa ser jsDelivr com commit fixo: {b_}')
        t = (f'<img src="{b_}{c["img"]}" width="{c["w"]}" height="{h}" alt="{a}" border="0" '
             f'style="display:block;width:100%;max-width:{c["w"]}px;height:auto;border:0;outline:none;text-decoration:none;'
             f'font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#555555;background-color:{bg};" />')
        href = link(c.get('href'), c.get('term'))
        if href:
            t = f'<a href="{href.replace(chr(34), "%22")}" target="_blank" style="display:block;text-decoration:none;">{t}</a>'
        return t

    rows = []
    for b in spec['blocks']:
        bg = b.get('bg', '#ffffff')
        if b['type'] == 'full':
            rows.append(f'<tr><td style="padding:0;font-size:0;line-height:0;">{img(b, b["h"], bg)}</td></tr>')
        else:
            assert sum(c['w'] for c in b['cells']) == 600, f'linha não soma 600px: {b}'
            tds = ''.join(f'<td width="{c["w"]}" valign="top" style="width:{c["w"]/6:.4f}%;padding:0;font-size:0;line-height:0;">{img(c, b["h"], bg)}</td>' for c in b['cells'])
            rows.append('<tr><td style="padding:0;font-size:0;line-height:0;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
                        f'style="table-layout:fixed;border-collapse:collapse;"><tr>{tds}</tr></table></td></tr>')
    note = (spec.get('note') or '').strip()
    rows.append('<tr><td align="center" style="padding:6px 30px 28px 30px;font-family:Arial,Helvetica,sans-serif;font-size:11px;line-height:16px;color:#8a8a8a;">'
                + (html.escape(note) + '<br />' if note else '') + 'Você recebeu este e-mail porque se cadastrou na Amakha Paris.</td></tr>')
    pad = '&#8202;&zwnj;&nbsp;' * 12
    content = f'''<div style="display:none;font-size:1px;color:#ffffff;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;mso-hide:all;">{html.escape(spec["preheader"])}{pad}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f4f4f4" style="background-color:#f4f4f4;">
<tr><td align="center" valign="top" style="padding:0;">
<!--[if mso]><table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" align="center"><tr><td><![endif]-->
<table role="presentation" class="amk-wrapper" width="100%" cellpadding="0" cellspacing="0" border="0" align="center" bgcolor="#ffffff" style="width:100%;max-width:600px;background-color:#ffffff;margin:0 auto;">
{chr(10).join(rows)}
</table>
<!--[if mso]></td></tr></table><![endif]-->
</td></tr>
</table>'''
    open(os.path.join(folder, 'corpo.html'), 'w').write(content)
    open(os.path.join(folder, 'preview.html'), 'w').write('<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0"/></head><body style="margin:0">' + content + '</body></html>')
    print(f'OK: {os.path.join(folder, "corpo.html")} ({len(content)} caracteres) | imagens em {base}')


if __name__ == '__main__':
    main()
