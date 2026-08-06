# fprobe-ulog

ULOG/NFLOG NetFlow probe for network traffic monitoring.

## Description

fprobe-ulog is a libnetfilter_log-based NetFlow probe. It captures network
traffic using the Linux netfilter ULOG/NFLOG mechanism and exports it as
NetFlow datagrams to a collector.

## Version

- 1.2

## Dependencies

- libnfnetlink/1.0.2 (from conan repository)
- libmnl/1.0.5 (built from source, inline)
- libnetfilter_log/1.0.2 (built from source, inline)

## Build

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## License

GPL-2.0
