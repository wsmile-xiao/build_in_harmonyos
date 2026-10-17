# munge 0.5.16 Adaptation Notes

## Source
- URL: https://github.com/dun/munge/releases/download/munge-0.5.16/munge-0.5.16.tar.xz
- SHA256: 6fa6f14de41064c2b56422592df7ad1de2af483912c54460863db2827e6a2861
- Build system: Autotools (configure/make)
- Language: C

## Dependencies
- openssl/3.0.16 (crypto)
- bzip2/1.0.8 (compression)
- zlib/1.3.1 (compression)

## Configuration
- --with-crypto-lib=openssl (use OpenSSL for crypto)
- --disable-suid (SUID not supported on OHOS)
- --enable-static / --disable-shared (static library)

## Notes
- munge uses autotools with libtool (LT_INIT)
- The library is libmunge, which exports munge_* symbols
- munge also builds executables: munge, unmunge, remunge, munged, mungekey
- config.guess (2022-01-09) may not recognize OHOS - conan AutotoolsToolchain handles triplet
