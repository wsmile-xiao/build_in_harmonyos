#!/usr/bin/env bash
# Deterministic mock ping for prettyping tests; ignores ping arguments.
set -euo pipefail

printf 'PING example.test (192.0.2.1): 56 data bytes\n'
printf '64 bytes from 192.0.2.1: icmp_seq=1 ttl=64 time=10.0 ms\n'
printf '64 bytes from 192.0.2.1: icmp_seq=2 ttl=64 time=20.0 ms\n'
printf '64 bytes from 192.0.2.1: icmp_seq=3 ttl=64 time=30.0 ms\n'
printf '%s\n' '--- example.test ping statistics ---'
printf '3 packets transmitted, 3 received, 0%% packet loss\n'
printf 'round-trip min/avg/max/stddev = 10.0/20.0/30.0/8.1 ms\n'
