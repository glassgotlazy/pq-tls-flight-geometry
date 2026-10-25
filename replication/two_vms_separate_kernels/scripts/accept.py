# Acceptance check on the R=50 p=0 cell: per config, t_tls_ms - 50: median, IQR, p99.
# Pass if every config has median <= 3, IQR <= 2, p99 <= 10 (ms). Same percentile rule as big.py.
import csv,glob,os,sys,statistics as st
OUT=sys.argv[1]; R=50
def pct(v,q): v=sorted(v); return v[min(len(v)-1,int(q*len(v)))]
ok_all=True
for g in ('x','h1','d'):
    v=[float(x['t_tls_ms'])-R for f in glob.glob(os.path.join(OUT,f'raw_PH_R{R}_p0_{g}_s*.csv')) for x in csv.DictReader(open(f)) if x['ok']=='1']
    med=st.median(v); iqr=pct(v,.75)-pct(v,.25); p99=pct(v,.99); ok=med<=3 and iqr<=2 and p99<=10; ok_all&=ok
    print(f"{g:2} n={len(v)} median_excess={med:.3f} IQR={iqr:.3f} p99={p99:.3f} min={min(v):.3f} max={max(v):.3f}  {'PASS' if ok else 'FAIL'}")
print('ACCEPTANCE:', 'PASS' if ok_all else 'FAIL')
