import subprocess, time, os, re, json, sys
sys.path.insert(0,'.'); import ch
from curl_cffi import requests, CurlOpt
O='/opt/ossl35/bin/openssl'; env=dict(os.environ,LD_LIBRARY_PATH='/opt/ossl35/lib')
G='X25519MLKEM768:X25519:secp256r1:secp384r1:SecP256r1MLKEM768:MLKEM768'
res={}
port=7300
for b in ['chrome150','chrome146','chrome131','chrome131_android','edge101','firefox147','firefox144','firefox133','safari260','safari260_ios','safari184','tor145']:
    port+=1
    s=subprocess.Popen([O,'s_server','-accept',str(port),'-cert','../c.pem','-key','../k.pem','-msg','-groups',G,'-naccept','1'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env)
    time.sleep(1.0)
    try:
        requests.get(f'https://www.example.com:{port}/',impersonate=b,verify=False,timeout=4,curl_options={CurlOpt.RESOLVE:[f'www.example.com:{port}:127.0.0.1']})
    except Exception as e: pass
    time.sleep(0.5); s.kill(); out=s.stdout.read().decode(errors='replace')
    ms=ch.parse_msgs(out)
    chs=[m for m in ms if m['dir']=='<<<' and m['name']=='ClientHello']
    if not chs: res[b]='no CH'; print(b,'no CH',out[:200]); continue
    c=chs[0]; ext=ch.parse_ch(c['hex'])
    ks=[x for x in ext if x['type']==51]; ks=ks[0]['shares'] if ks else []
    types=[x['type'] for x in ext]
    ech=[x['len'] for x in ext if x['type']==0xfe0d]
    pad=[x['len'] for x in ext if x['type']==21]
    res[b]=dict(W=c['len']+5,shares=ks,n_ext=len(ext),ech=ech,pad=pad)
    print(b,res[b],flush=True)
json.dump(res,open('browsers.json','w'),indent=1)
