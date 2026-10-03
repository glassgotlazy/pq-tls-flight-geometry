#!/usr/bin/env python3
# Parse s_server -msg captures with the repro package's own parser (geometry/ch.py) and
# cross-check W against the 5-byte TLS record header printed by -msg.
import sys, json, glob, math, re, csv, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'geometry')); import ch
def gname(g):
    if (g & 0x0f0f) == 0x0a0a and (g >> 8) == (g & 0xff): return 'GREASE'
    return ch.GN.get(g, hex(g))
runs = {(r['label'], r['run']): r for r in map(json.loads, open('runs.jsonl'))}
rows = []
for f in sorted(glob.glob('raw/*.txt')):
    label, run = re.match(r'raw/(.+)_(\d+)\.txt', f).groups(); run = int(run)
    out = open(f, errors='replace').read()
    ms = ch.parse_msgs(out)
    chs = [m for m in ms if m['dir'] == '<<<' and m['name'] == 'ClientHello']
    if not chs: rows.append(dict(label=label, run=run, status='FAILED: no ClientHello')); continue
    c = chs[0]
    # record header precedes the ClientHello message in the -msg output
    idx = ms.index(c); rh = ms[idx - 1] if idx > 0 and ms[idx - 1]['kind'] == 'RecordHeader' else None
    rec_len = int(rh['hex'][6:10], 16) if rh and len(rh['hex']) >= 10 else None
    ext = ch.parse_ch(c['hex'])
    b = bytes.fromhex(c['hex'])
    shares = []
    for x in ext:
        if x['type'] == 51:
            d_off = None
    # re-parse key_share with raw group ids so GREASE is recognisable
    i = 4 + 2 + 32; i += 1 + b[i]; i += 2 + int.from_bytes(b[i:i+2], 'big'); i += 1 + b[i]
    el = int.from_bytes(b[i:i+2], 'big'); i += 2; end = i + el; ext_types = []
    while i < end:
        t = int.from_bytes(b[i:i+2], 'big'); l = int.from_bytes(b[i+2:i+4], 'big'); d = b[i+4:i+4+l]; ext_types.append(t)
        if t == 51:
            j = 2
            while j < len(d):
                g = int.from_bytes(d[j:j+2], 'big'); kl = int.from_bytes(d[j+2:j+4], 'big'); shares.append((gname(g), kl)); j += 4 + kl
        i += 4 + l
    ech = [x['len'] for x in ext if x['type'] == 0xfe0d]
    pad = [x['len'] for x in ext if x['type'] == 21]
    grease_ext = sum(1 for t in ext_types if (t & 0x0f0f) == 0x0a0a and (t >> 8) == (t & 0xff))
    W = c['len'] + 5
    rows.append(dict(label=label, run=run, browser_version=runs.get((label, run), {}).get('version', ''),
        W=W, record_len_from_header=rec_len, W_check=('OK' if rec_len is not None and rec_len + 5 == W else 'MISMATCH'),
        ch_handshake_len=c['len'], n_ext=len(ext), n_ext_grease=grease_ext,
        key_shares=';'.join(f'{n}/{l}' for n, l in shares), ech_len=(ech[0] if ech else ''), padding_len=(pad[0] if pad else ''),
        psk_present=int(any(x['type'] == 41 for x in ext)), n_clienthellos_in_capture=len(chs),
        seg_mss1448=math.ceil(W / 1448), seg_mss1208=math.ceil(W / 1208), status='OK'))
keys = ['label', 'run', 'browser_version', 'W', 'record_len_from_header', 'W_check', 'ch_handshake_len', 'n_ext', 'n_ext_grease',
        'key_shares', 'ech_len', 'padding_len', 'psk_present', 'n_clienthellos_in_capture', 'seg_mss1448', 'seg_mss1208', 'status']
with open(sys.argv[1], 'w', newline='') as o:
    w = csv.DictWriter(o, fieldnames=keys); w.writeheader(); [w.writerow(r) for r in rows]
for r in rows: print(r)
