# qperf

qperf measures bandwidth and latency between two nodes. It works over TCP/IP
as well as over the RDMA transports, and is the benchmark tool shipped with the
OpenIB / linux-rdma stack.

On one node qperf is run without arguments to act as the server; on the other
node it is run with the server name plus one or more test names
(`tcp_bw`, `tcp_lat`, `udp_bw`, `udp_lat`, `rc_bw`, ...):

```bash
qperf                      # server node
qperf myserver tcp_bw tcp_lat   # client node
```

- Homepage: <https://github.com/linux-rdma/qperf>
- License: GPL-2.0-only OR BSD-2-Clause (upstream's dual "choose one of" notice)
- Build system: GNU autotools (tag tarballs ship no generated `configure`)

## Adapted versions

See [`0.4.11/notes.md`](0.4.11/notes.md) for the OpenHarmony adaptation record,
including which transports are actually available on HarmonyOS PC and the
measured evidence behind that judgement.
