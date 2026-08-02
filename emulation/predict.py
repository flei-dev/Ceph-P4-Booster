import random, heapq, statistics
random.seed(7)
def load(p): return [int(x)/1e6 for x in open(p) if x.strip()]
CE=load('ceph-latency-us.txt')
P4=load('p4-latency-us.txt')

def sim(rate, S, samples, dur=20.0):
    # 单服务器串行占用 S（M/D/1），随后非阻塞等待 sampled
    t=0.0; free=0.0; lat=[]
    n=int(rate*dur)
    for i in range(n):
        t += random.expovariate(rate)
        start=max(t,free); free=start+S
        w=random.choice(samples)
        lat.append((start+S-t)+max(0.0,w-S))
    lat.sort()
    return (statistics.mean(lat)*1000, lat[len(lat)//2]*1000, lat[int(.99*(len(lat)-1))]*1000)

print(f"{'rate':>6} | {'base avg':>9} {'base P50':>9} {'base P99':>9} | {'boost avg':>9} {'boost P50':>9} {'boost P99':>9} | {'P99 ratio':>9}")
for r in (100,500,1000,1500,2000,2200,2400,2500,3000):
    b=sim(r,0.0004,CE); o=sim(r,0.0001,P4)
    print(f"{r:>6} | {b[0]:9.2f} {b[1]:9.2f} {b[2]:9.2f} | {o[0]:9.2f} {o[1]:9.2f} {o[2]:9.2f} | {b[2]/o[2]:9.2f}")
