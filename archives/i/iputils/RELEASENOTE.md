# Release Note — iputils

**Release Date**: 2026-05-06
**Status**: SUCCESS
**Platform**: OpenHarmony (ohos-aarch64)

## Available Versions

| Version | Date | Status |
|---------|------|--------|
| 20240905 | 2026-05-06 | SUCCESS |

## Version 20240905

### Included Tools

| Tool | Description | IPv4 | IPv6 |
|------|-------------|------|------|
| ping | ICMP Echo tool | ✅ | ✅ |
| tracepath | Path MTU discovery | ✅ | ✅ |
| arping | ARP request tool | ✅ | ❌ |
| clockdiff | Clock difference | ✅ | ❌ |

### Key Features

1. **Unified IPv4/IPv6 Design**: Single tool supports both protocols
2. **musl libc Support**: Compatible with HarmonyOS/musl environment
3. **No setcap/setuid**: Avoids permission issues

### HarmonyOS Adaptations

- `program_invocation_short_name` → `__progname` (glibc → musl)
- `sockaddr_storage` redefinition → macro rename

### Installation

```bash
cd packaging/
./install-iputils-20240905.sh
```

### Usage Examples

```bash
# IPv4 ping
ping 192.168.1.1

# IPv6 ping
ping ::1

# IPv4 tracepath
tracepath 192.168.1.1

# IPv6 tracepath
tracepath ::1
```

### Build Configuration

```
meson setup build \
  --prefix=/storage/Users/currentUser/usr/local \
  -DBUILD_PING=true \
  -DBUILD_TRACEPATH=true \
  -DBUILD_ARPING=true \
  -DBUILD_CLOCKDIFF=true \
  -DNO_SETCAP_OR_SUID=true \
  -DUSE_CAP=false \
  -DUSE_IDN=false \
  -DUSE_GETTEXT=false
```

### Known Limitations

- arping/clockdiff only support IPv4 (protocol limitation)
- libcap/libidn2 not available, CAP/IDN features disabled

### Source

- URL: https://github.com/iputils/iputils
- Version: 20240905