"""开环负载发生器：发送与接收分离，发送速率不受响应延迟限制。"""
import argparse, socket, statistics, threading, time

def run(target, rate, dur, warmup=2.0):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 << 20)
    sock.settimeout(0.5)
    dst = (target, int(__import__('os').environ.get('LP_PORT','9997')))
    sent, lat, stop = {}, [], threading.Event()

    def receiver():
        while not stop.is_set():
            try: data, _ = sock.recvfrom(64)
            except (socket.timeout, OSError): continue
            t0 = sent.pop(int(data), None)
            if t0 is not None: lat.append((time.time() - t0) * 1000)

    rt = threading.Thread(target=receiver, daemon=True); rt.start()
    iv, seq, t_start = 1.0 / rate, 0, time.time()
    t_measure = t_start + warmup
    while True:
        now = time.time()
        if now >= t_start + warmup + dur: break
        target_t = t_start + seq * iv
        if target_t > now: time.sleep(target_t - now)
        seq += 1
        sent[seq] = time.time()
        if seq * iv < warmup: sent.pop(seq)      # 预热期不计
        try: sock.sendto(str(seq).encode(), dst)
        except OSError: pass
    time.sleep(1.0); stop.set(); rt.join(timeout=1)

    offered = seq
    if not lat:
        print(f"RESULT:{rate:.0f},nan,nan,nan,0,{offered}"); return
    s = sorted(lat)
    print(f"RESULT:{rate:.0f},{statistics.mean(s):.2f},{s[len(s)//2]:.2f},"
          f"{s[int(0.99*(len(s)-1))]:.2f},{len(s)},{offered}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('-t', '--target', default='127.0.0.1')
    p.add_argument('-r', '--rate', type=float, required=True)
    p.add_argument('-d', '--dur', type=float, default=6.0)
    a = p.parse_args(); run(a.target, a.rate, a.dur)
