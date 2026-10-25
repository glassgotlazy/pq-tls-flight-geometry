# Minimal AF_PACKET sniffer: prints TCP segments to/from ports 4501-4506 on one interface.
import socket,struct,sys,time
iface,dur=sys.argv[1],float(sys.argv[2])
s=socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.ntohs(3)); s.bind((iface,0)); s.settimeout(0.5)
t0=time.time(); print(f"# capture on {iface} for {dur}s",flush=True)
while time.time()-t0<dur:
    try: pkt,addr=s.recvfrom(65535)
    except socket.timeout: continue
    if len(pkt)<34 or struct.unpack('!H',pkt[12:14])[0]!=0x0800: continue
    ip=pkt[14:]; ihl=(ip[0]&15)*4; tot=struct.unpack('!H',ip[2:4])[0]
    if ip[9]!=6: continue
    tcp=ip[ihl:]; sp,dp,seq=struct.unpack('!HHI',tcp[:8]); off=(tcp[12]>>4)*4; fl=tcp[13]
    if not ({sp,dp} & set(range(4501,4507))): continue
    pl=tot-ihl-off; pay=tcp[off:off+pl]
    f=''.join(c for b,c in zip((1,2,4,8,16),'FSRPA') if fl&b)
    print(f"{time.time()-t0:8.4f} {'OUT' if addr[2]==4 else 'IN '} {socket.inet_ntoa(ip[12:16])}:{sp} > {socket.inet_ntoa(ip[16:20])}:{dp} "
          f"ip_len={tot} tcp_payload={pl} flags={f} seq={seq} head={pay[:6].hex()} sni_www.example.com={'yes' if b'www.example.com' in pay else 'no'}",flush=True)
