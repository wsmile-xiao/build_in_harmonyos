# Patches

No source patch is applied for scanlogd 2.2.8. The selected upstream
`make linux` backend uses ordinary Linux/musl headers and has no libpcap or
libnids dependency. Adding a patch before an OHOS clang 15 build demonstrates a
specific defect would alter the candidate without evidence, so the core
packet-processing and raw-socket capture logic remain unchanged.
