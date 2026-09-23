# mecab 0.996 - Conan Adaptation Notes

## OHOS Adaptations
1. E007: config.guess/config.sub replaced inline with OHOS-aware versions
2. E011: umask 077 -> 022 in configure and config.status
3. E490: chmod +x for autotools helper scripts
4. TMPDIR: configure patched to use ${TMPDIR:-/tmp} (patch 0003)
5. print->echo: config.status ksh builtin replaced with echo
6. shared option: default static (library package_type requirement)

## W3 Verification
- conan create: PASSED (exit_code=0)
- integrity_hash: 8afcc05158fdf426
