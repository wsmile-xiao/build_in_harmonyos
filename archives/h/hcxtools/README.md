# hcxtools

A small set of tools to convert packets from capture files (pcap/pcapng)
to hash files for use with Hashcat or John the Ripper.

## Tools

| Tool | Description |
|------|-------------|
| hcxpcapngtool | Convert pcapng to hash formats |
| hcxhashtool | Hash manipulation and conversion |
| hcxpsktool | Pre-shared key tool |
| hcxpmktool | Pairwise master key tool |
| hcxpottool | Password tool |
| hcxeiutool | EAP identity tool |
| hcxwltool | Wireless LAN tool |
| hcxhash2cap | Hash to capture file converter |
| wlancap2wpasec | Upload captures to wpasec |
| whoismac | MAC address lookup |

## Build

```bash
make CC=clang -j1
make install PREFIX=/usr DESTDIR=/path/to/staging
```

Dependencies: OpenSSL, zlib, libcurl (discovered via pkg-config)

## License

MIT
