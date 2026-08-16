# Redis 8.2.7 upstream test accounting

Date: 2026-08-16

## Scope

The final Shadow run executes all official Redis 8.2.7 Tcl entry points against
freshly built and signed HarmonyOS binaries:

```sh
sh ./runtest
MAKE='make -j1 ...' sh ./runtest-moduleapi
sh ./runtest-sentinel
sh ./runtest-cluster
```

The repository contains 212 Tcl files, but this inventory includes runners,
support code, assets, and suite files. The authoritative runtime accounting is:

| Suite | Units/files | OK records | Skips | Errors |
|---|---:|---:|---:|---:|
| Default | 102 | 3,697 | 49 | 0 |
| Module API | 44 | 534 | 6 | 0 |
| Sentinel | 16 | 197 | 1 | 0 |
| Cluster | 28 | 549 | 0 | 0 |
| **Total** | **190** | **4,977** | **56** | **0** |

All four runners ended with their native success summary.

## Why 56 tests are not applicable

The HarmonyOS user session accepts `kill -SIGSTOP <pid>` but does not suspend the
target process. Tests that require a process to remain frozen would therefore
exercise the wrong state and can hang or produce false failures. Patch 0008:

- detects direct use of `pause_process`, `resume_process`, or `debug repl-pause`;
- names coupled cases whose helper hides the pause operation;
- increments the upstream skip count and prints the capability reason;
- fails immediately if an unaccounted pause helper escapes the list.

Default runner skips: 49. They cover client output-buffer pressure, prefetch,
WAIT/WAITAOF while a replica is frozen, replication buffer accounting, Cluster
failure timing, manual FAILOVER timing, minimum-replica lag, shutdown catch-up,
RDB-channel state transitions, backlog changes, streaming replication, and
diskless replication drop/timeout timing.

Module API skips: 6.

- WAIT on a module client blocked on keys.
- WAIT on a module blocked client.
- Kill a cluster node and wait for fail state.
- Verify a key-blocked command unblocks after cluster failure.
- Verify a no-key blocked command unblocks after cluster failure.
- Verify `RM_Call` rejects a command while the cluster is down.

Sentinel skips: 1.

- SDOWN triggered by a non-responding but not crashed instance.

Standalone Cluster skips: 0.

## Replacement coverage

The 121-assertion package test adds process-stop or protocol-level alternatives
for the main skipped functional areas:

| Pause-dependent area | Executed replacement evidence |
|---|---|
| Client output-buffer eviction | Slow pub/sub client exceeds a 64 KiB hard limit and is evicted |
| WAIT/WAITAOF | Success with a live replica and timeout with the replica stopped |
| Manual failover | Controlled FAILOVER to a named replica and back, with data continuity |
| Minimum replica policy | Writes are rejected with `NOREPLICAS`, then recover after restart |
| Cluster outage | One of three nodes is stopped; remaining nodes report fail and reject commands |
| Cluster recovery | The stopped node rejoins; all nodes return to `cluster_state:ok` |
| Sentinel outage handling | The monitored master is stopped; Sentinel promotes the replica |
| Persistence/streaming risk | RDB/AOF restart recovery, rewrite, corruption rejection, and replication continuity |

Exact SIGSTOP timing remains not applicable on this device. It is not reported
as passed, and no complete suite file is silently removed.

## Evidence

- Commit: `de15e2c3afa3f1f91a76ca0e411dda9f0b048cb3`
- Run: `/storage/Users/currentUser/ohpc-ci-shadow/runs/de15e2c3afa3-20260816T093310Z-redis-tcl-run-4598`
- Build log SHA256: `e9a9863d5db13c8ee0f86ceffd069c95270b2d9eb863351bd8905e8964353ff0`
- Package result: `redis 8.2.7 extended package test passed: 121 assertions`
