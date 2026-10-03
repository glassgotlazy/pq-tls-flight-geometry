import json, math, ch
MSS={'v4-1500-TS':1448,'v4-1500':1460,'v6-1500-TS':1428,'v4-1400-TS':1348,'v4-1280-TS':1228,'v6-1280-TS':1208,'v6-1280':1220}
groups={'classical X25519':['-groups','X25519'],
 'OpenSSL 3.5 default (hybrid+X25519 shares)':[],
 'X25519MLKEM768 share only':['-groups','X25519MLKEM768:X25519'],
 'SecP256r1MLKEM768 only':['-groups','SecP256r1MLKEM768'],
 'MLKEM768 only':['-groups','MLKEM768'],
 'SecP384r1MLKEM1024 only':['-groups','SecP384r1MLKEM1024'],
 'MLKEM1024 only':['-groups','MLKEM1024']}
profiles={'lean (TLS1.3-only, no SNI)':['-tls1_3','-noservername'],
 'OpenSSL default (TLS1.2+1.3, SNI)':['-servername','www.example.com'],
 'browser-like (SNI+ALPN h2)':['-servername','www.example.com','-alpn','h2,http/1.1']}
rows=[]
port=4500
for pn,pa in profiles.items():
  for gn,ga in groups.items():
    port+=1
    r=ch.run(pa+ga,port=port,resume=True)
    full,res=r
    shares=[x for x in full['ext'] if x['type']==51][0]['shares']
    rshares=[x for x in res['ext'] if x['type']==51]
    rshares=rshares[0]['shares'] if rshares else []
    psk=[x for x in res['ext'] if x['type']==41]
    rows.append(dict(profile=pn,groups=gn,full=full['tls_bytes'],resumed=res['tls_bytes'],reused=res['reused'],shares=shares,rshares=rshares,psk_ext=psk[0]['len'] if psk else 0,srv_full=full['server_hs_bytes'],srv_res=res['server_hs_bytes'],modes=[x.get('modes') for x in res['ext'] if x['type']==45]))
json.dump(rows,open('rows.json','w'),indent=1)
for r in rows:
  segs=' '.join(f"{math.ceil(r['full']/m)}/{math.ceil(r['resumed']/m)}" for m in MSS.values())
  print(f"{r['profile'][:22]:22} | {r['groups'][:26]:26} | full {r['full']:5} res {r['resumed']:5} reused={r['reused']} psk={r['psk_ext']} srv {r['srv_full']}/{r['srv_res']} | {segs} | {r['shares']} -> {r['rshares']} {r['modes']}")
print(list(MSS))
