# gdnsd 3.8.2 — OHOS Adaptation

Geographic Authoritative DNS server adapted for OpenHarmonyOS.

## Key Changes
- 3 patches for `#ifdef __OHOS__` guard on pthread_setcanceltype calls
- Build system: autotools
- Dependencies: libev, openssl, zlib, userspace-rcu, libsodium, ragel

## Verification
- gdnsd --version → 3.8.2 ✅
- gdnsdctl --version → 3.8.2 ✅
