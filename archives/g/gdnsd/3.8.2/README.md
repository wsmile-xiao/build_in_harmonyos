# gdnsd 3.8.2 - OHOS Adaptation

Geographic Authoritative DNS server adapted for OpenHarmonyOS.

## Key Changes
- Source is the official release tarball (ships pre-generated `configure` and
  ragel-generated C sources, so no ragel/autoreconf needed at build time)
- 3 patches guard `pthread_setcanceltype` calls with
  `#ifndef HAVE_PTHREAD_SETCANCELTYPE` (OHOS musl libc has no such function
  and upstream configure never defines the macro)
- Patch 0004 teaches the shipped `acaux/config.sub` to accept `linux-ohos`
  triplets; the recipe passes `--build/--host=aarch64-linux-ohos` explicitly
- Patch 0005 replaces `mktemp -d` with `mkdir -p` in the shipped `configure`
  (HMDFS blocks writes inside mktemp-created 0700 directories)
- Build system: autotools
- Dependencies: libev, userspace-rcu, libsodium (zlib/openssl are not used
  by gdnsd 3.8.2 and are not declared)

## Verification
- gdnsd --version -> 3.8.2 OK
- gdnsdctl --version -> 3.8.2 OK
