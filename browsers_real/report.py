import csv, json, math, collections
rows=[r for r in csv.DictReader(open('../data/browsers_real.csv')) if r['status']=='OK']
imp=json.load(open('../data/browsers.json'))
NAME={'edge':'Microsoft Edge {v} (Linux, real vendor build)','pw-chromium':'Chromium {v} (Playwright bundled build; supplementary, NOT Google Chrome)'}
def shares_txt(s): return ', '.join(x.split('/')[0] for x in s.split(';'))
g=collections.OrderedDict()
for r in rows: g.setdefault(r['label'],[]).append(r)
L=[]
L.append('| Profile | Key shares offered | ECH GREASE | W | Segments at MSS 1448 / 1208 |')
L.append('|---|---|---|---|---|')
for lab,v in g.items():
    W=sorted(int(r['W']) for r in v); ech=sorted(set(int(r['ech_len']) for r in v if r['ech_len']))
    sh=set(r['key_shares'] for r in v); assert len(sh)==1
    s1=sorted(set(int(r['seg_mss1448']) for r in v)); s2=sorted(set(int(r['seg_mss1208']) for r in v))
    wtxt=f"{W[0]:,}" if W[0]==W[-1] else f"{W[0]:,}–{W[-1]:,}"
    L.append(f"| {NAME[lab].format(v=v[0]['browser_version'])} | {shares_txt(sh.pop())} | {'/'.join(map(str,ech)) or '—'} | {wtxt} | {'/'.join(map(str,s1))} / {'/'.join(map(str,s2))} |")
L.append('')
L.append('n = 5 fresh connections per browser (new temporary profile each, no PSK extension observed in any ClientHello). W = full first TLS record incl. 5-byte header. Per-connection values in browsers_real.csv.')
L.append('')
L.append('Per-connection W (ECH GREASE length):')
for lab,v in g.items(): L.append(f"- {lab}: " + ', '.join(f"{r['W']} ({r['ech_len']})" for r in v))
L.append('')
L.append('## Comparison with impersonated values (data/browsers.json, curl_cffi)')
L.append('')
L.append('ECH GREASE length is drawn per connection, so W is also compared after subtracting the ECH extension payload length ("base" = W − ECH).')
L.append('')
L.append('| Real profile | Impersonated profile | Real W (range) | Imp. W | ΔW range | Real base W−ECH | Imp. base | Δbase | |ΔW| > 20 B? |')
L.append('|---|---|---|---|---|---|---|---|---|')
pairs=[('edge','edge101'),('edge','chrome150'),('edge','chrome146'),('pw-chromium','chrome131'),('pw-chromium','chrome146'),('pw-chromium','chrome150')]
for lab,ik in pairs:
    v=g[lab]; i=imp[ik]; iW=i['W']; iech=i['ech'][0] if i['ech'] else 0
    W=[int(r['W']) for r in v]; base=sorted(set(int(r['W'])-int(r['ech_len'] or 0) for r in v))
    dW=[w-iW for w in W]; db=[b-(iW-iech) for b in base]
    flag='YES' if max(abs(x) for x in dW)>20 else 'no'
    L.append(f"| {lab} {v[0]['browser_version']} | {ik} | {min(W)}–{max(W)} | {iW} | {min(dW):+}…{max(dW):+} | {'/'.join(map(str,base))} | {iW-iech} | {'/'.join(f'{x:+}' for x in db)} | {flag} |")
open('browsers_real.md','w').write('\n'.join(L)+'\n'); print('\n'.join(L))
