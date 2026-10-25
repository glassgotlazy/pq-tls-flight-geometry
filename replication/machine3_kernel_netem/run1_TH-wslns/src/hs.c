// hs.c — TLS 1.3 handshake probe (OpenSSL 3.5). Measures timing, ClientHello/ServerHello structure, resumption.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netinet/tcp.h>
#include <sys/socket.h>
#include <openssl/ssl.h>
#include <openssl/err.h>

static double now(){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec*1e3+t.tv_nsec/1e6;}
typedef struct { int ch_len, sh_len, ch_ks_n, ch_ks_bytes, ch_psk, sh_ks_group, sh_ks_len, sh_psk; char ch_groups[128]; } info_t;
static info_t I;
static unsigned g16(const unsigned char*p){return (p[0]<<8)|p[1];}
static void parse_ext(const unsigned char*b,int n,int is_ch){
  int off=4+2+32; if(off>=n) return; off+=1+b[off];
  off+=2+g16(b+off); if(is_ch){off+=1+b[off];} else {off+=1;} // CH: compression list; SH: cs(2) handled below
  if(!is_ch){ /* SH: we skipped cs as 2+len incorrectly; recompute */ off=4+2+32; off+=1+b[off]; off+=2; off+=1; }
  int el=g16(b+off); off+=2; int end=off+el; if(end>n) end=n;
  while(off+4<=end){ int t=g16(b+off), l=g16(b+off+2); const unsigned char*d=b+off+4;
    if(t==51){ if(is_ch){ int sl=g16(d), p=2; I.ch_ks_bytes=sl; I.ch_groups[0]=0;
          while(p+4<=2+sl){ int g=g16(d+p), kl=g16(d+p+2); char s[16]; snprintf(s,16,"%s%04x/%d",I.ch_ks_n?";":"",g,kl); strncat(I.ch_groups,s,127-strlen(I.ch_groups)); I.ch_ks_n++; p+=4+kl; } }
      else if(l>=4){ I.sh_ks_group=g16(d); I.sh_ks_len=g16(d+2);} else if(l==2){ I.sh_ks_group=g16(d); I.sh_ks_len=-1; /*HRR*/ } }
    if(t==41){ if(is_ch) I.ch_psk=1; else I.sh_psk=1; }
    off+=4+l; }
}
static void msgcb(int wp,int ver,int ct,const void*buf,size_t len,SSL*s,void*a){
  const unsigned char*b=buf; if(ct!=SSL3_RT_HANDSHAKE||len<4) return;
  if(wp && b[0]==1){ I.ch_len=len; parse_ext(b,len,1); }
  if(!wp && b[0]==2){ I.sh_len=len; parse_ext(b,len,0); }
}
static SSL_SESSION* saved=NULL;
static int newsess(SSL*s,SSL_SESSION*sess){ if(saved) SSL_SESSION_free(saved); saved=sess; return 1; }

int main(int argc,char**argv){
  if(argc<6){fprintf(stderr,"usage: hs host port groups sni N [resume(0/1)] [label] [psk_ke(0/1)]\n");return 1;}
  const char*host=argv[1]; int port=atoi(argv[2]); const char*groups=argv[3]; const char*sni=argv[4]; int N=atoi(argv[5]);
  int resume=argc>6?atoi(argv[6]):0; const char*label=argc>7?argv[7]:"-"; int pskke=argc>8?atoi(argv[8]):0;
  SSL_CTX*ctx=SSL_CTX_new(TLS_client_method());
  SSL_CTX_set_min_proto_version(ctx,TLS1_3_VERSION);
  if(strcmp(groups,"default") && !SSL_CTX_set1_groups_list(ctx,groups)){ERR_print_errors_fp(stderr);return 2;}
  SSL_CTX_set_verify(ctx,SSL_VERIFY_NONE,NULL);
  static const unsigned char alpn[]="\x02h2\x08http/1.1"; SSL_CTX_set_alpn_protos(ctx,alpn,sizeof(alpn)-1);
  SSL_CTX_set_session_cache_mode(ctx,SSL_SESS_CACHE_CLIENT|SSL_SESS_CACHE_NO_INTERNAL_STORE);
  SSL_CTX_sess_set_new_cb(ctx,newsess);
  if(pskke) SSL_CTX_set_options(ctx,SSL_OP_ALLOW_NO_DHE_KEX);
  printf("label,iter,mode,group_cfg,sni_len,t_tcp_ms,t_tls_ms,t_total_ms,ch_len,ch_ks_n,ch_ks_bytes,ch_groups,ch_psk,sh_len,sh_group,sh_ks_len,sh_psk,reused,retrans,ok\n");
  for(int i=0;i<N;i++){
    for(int phase=0; phase<(resume?2:1); phase++){
      memset(&I,0,sizeof I);
      int fd=socket(AF_INET,SOCK_STREAM,0); struct sockaddr_in sa={0}; sa.sin_family=AF_INET; sa.sin_port=htons(port); inet_pton(AF_INET,host,&sa.sin_addr);
      struct timeval tv={30,0}; setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&tv,sizeof tv); setsockopt(fd,SOL_SOCKET,SO_SNDTIMEO,&tv,sizeof tv);
      double t0=now(); if(connect(fd,(void*)&sa,sizeof sa)){perror("connect");close(fd);continue;}
      double t1=now();
      SSL*s=SSL_new(ctx); SSL_set_fd(s,fd); SSL_set_tlsext_host_name(s,sni); SSL_set_msg_callback(s,msgcb);
      if(phase==1 && saved) SSL_set_session(s,saved);
      int ok=SSL_connect(s)==1; double t2=now();
      struct tcp_info ti; socklen_t tl=sizeof ti; memset(&ti,0,sizeof ti); getsockopt(fd,IPPROTO_TCP,TCP_INFO,&ti,&tl);
      if(ok && resume && phase==0){ // pull NewSessionTicket(s)
        char buf[256]; struct timeval tv2={0,300000}; setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&tv2,sizeof tv2);
        for(int k=0;k<3 && !saved;k++){ SSL_read(s,buf,sizeof buf); }
        if(!saved){ for(int k=0;k<5;k++) SSL_read(s,buf,sizeof buf);} }
      printf("%s,%d,%s,%s,%zu,%.3f,%.3f,%.3f,%d,%d,%d,%s,%d,%d,%04x,%d,%d,%d,%u,%d\n",label,i,phase?"resumed":"full",groups,strlen(sni),
        t1-t0,t2-t1,t2-t0,I.ch_len,I.ch_ks_n,I.ch_ks_bytes,I.ch_groups,I.ch_psk,I.sh_len,I.sh_ks_group,I.sh_ks_len,I.sh_psk,SSL_session_reused(s),ti.tcpi_total_retrans,ok);
      fflush(stdout);
      SSL_shutdown(s); SSL_free(s); close(fd);
      if(phase==1 && saved){ SSL_SESSION_free(saved); saved=NULL; }
    }
  }
  return 0;
}
