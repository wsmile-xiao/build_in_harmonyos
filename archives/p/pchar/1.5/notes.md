# pchar 1.5

## Upstream

- Official source: https://kitchenlab.org/www/bmah/Software/pchar/
- Release: `pchar-1.5.tar.gz`
- SHA256: `7019297084f1000557a019501532ecae67772851717329cc02227f5c17e36d27`

## Adaptation

The default build uses the bundled Autotools build and does not enable optional
SNMP or libpcap support. Runtime path probing requires network access and may
require raw-socket privileges on the target system.
