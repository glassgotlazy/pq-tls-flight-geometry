import subprocess, re, sys, time, os, json
O='/opt/ossl35/bin/openssl'; env=dict(os.environ, LD_LIBRARY_PATH='/opt/ossl35/lib')
GN={0x1d:'X25519',0x17:'secp256r1',0x18:'secp384r1',0x19:'secp521r1',0x1e:'x448',0x11ec:'X25519MLKEM768',0x11eb:'SecP256r1MLKEM768',0x11ed:'SecP384r1MLKEM1024',0x200:'MLKEM512',0x201:'MLKEM768',0x202:'MLKEM1024',0x100:'ffdhe2048',0x101:'ffdhe3072'}
def parse_msgs(out):
    # collect '>>> ... Handshake [length xxxx], ClientHello' followed by hex lines
    msgs=[]; cur=None
    for line in out.splitlines():
        m=re.match(r'(>>>|<<<) .*?(RecordHeader|Handshake) \[length ([0-9a-f]+)\](?:, (\w+))?',line)
        if m:
            if cur: msgs.append(cur)
            cur={'dir':m.group(1),'kind':m.group(2),'len':int(m.group(3),16),'name':m.group(4),'hex':''}
            continue
        if cur and re.match(r'^\s+([0-9a-f]{2}\s?)+$',line):
            cur['hex']+=line.replace(' ','').strip()
        elif cur and line.strip()=='' : pass
    if cur: msgs.append(cur)
    return msgs
def parse_ch(h):
    b=bytes.fromhex(h); i=4+2+32; sl=b[i]; i+=1+sl
    cl=int.from_bytes(b[i:i+2],'big'); i+=2+cl
    i+=1+b[i]
    el=int.from_bytes(b[i:i+2],'big'); i+=2; end=i+el; ext=[]
    while i<end:
        t=int.from_bytes(b[i:i+2],'big'); l=int.from_bytes(b[i+2:i+4],'big'); d=b[i+4:i+4+l]; i+=4+l
        info={'type':t,'len':l}
        if t==51:
            j=2; ks=[]
            while j<len(d):
                g=int.from_bytes(d[j:j+2],'big'); kl=int.from_bytes(d[j+2:j+4],'big'); ks.append((GN.get(g,hex(g)),kl)); j+=4+kl
            info['shares']=ks
        if t==45: info['modes']=list(d[1:])
        if t==41:
            il=int.from_bytes(d[0:2],'big'); info['identities_len']=il
        ext.append(info)
    return ext
NAMES={0:'server_name',10:'supported_groups',11:'ec_point_formats',13:'signature_algorithms',16:'alpn',22:'encrypt_then_mac',23:'extended_master_secret',35:'session_ticket',41:'pre_shared_key',42:'early_data',43:'supported_versions',45:'psk_kex_modes',49:'post_handshake_auth',51:'key_share',21:'padding',27:'compress_certificate'}
def run(cargs, sargs=[], port=4433, resume=False):
    s=subprocess.Popen([O,'s_server','-tls1_3','-accept',str(port),'-cert','../c.pem','-key','../k.pem','-naccept','20','-quiet']+sargs,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    time.sleep(0.9)
    res=[]
    import os as _o
    _o.path.exists('sess.pem') and _o.remove('sess.pem')
    rounds=[['-sess_out','sess.pem']] if resume else [[]]
    if resume: rounds.append(['-sess_in','sess.pem'])
    for extra in rounds:
        for _try in range(8):
            p=subprocess.Popen([O,'s_client','-connect',f'127.0.0.1:{port}','-msg']+cargs+extra,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env)
            time.sleep(0.7); p.stdin.close(); out=p.stdout.read().decode(errors='replace'); p.wait()
            if 'errno=111' not in out: break
            time.sleep(0.5)
        if resume and not extra[0].endswith('in'): time.sleep(0.2)
        ms=parse_msgs(out)
        chs=[m for m in ms if m['dir']=='>>>' and m['name']=='ClientHello']
        if not chs: print('FAIL',cargs+extra,out[:600]); raise SystemExit
        ch=chs[0]
        ext=parse_ch(ch['hex'])
        reused='Reused, TLSv1.3' in out
        sh_serv=sum(m['len']+0 for m in ms if m['dir']=='<<<' and m['kind']=='Handshake' and m['name']!='NewSessionTicket'); nst=[m['len'] for m in ms if m['dir']=='<<<' and m['name']=='NewSessionTicket']
        res.append({'ch_hs_len':ch['len'],'tls_bytes':ch['len']+5,'reused':reused,'ext':ext,'server_hs_bytes':sh_serv,'nst':nst})
    s.kill(); s.wait()
    return res
if __name__=='__main__':
    import itertools
    print(json.dumps(run(sys.argv[1:]),indent=0)[:3000])
