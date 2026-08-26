# wait4ports

wait4ports is a small utility to wait for network peer availability.

It repeatedly attempts TCP connections to one or more `host:port` endpoints
and exits as soon as any of them becomes reachable, making it useful in
container orchestration and CI pipelines that need to wait for services
to be ready before proceeding.

## Upstream

- **Repository**: https://github.com/erikogan/wait4ports
- **License**: MPL-2.0
- **Language**: C

## Versions

| Version | Status |
|---------|--------|
| 0.3.3-r1 | built |
