# bruteforce-wallet

Try to find the password of an encrypted Peercoin (or Bitcoin, Litecoin,
...) wallet file (`wallet.dat`), by exhaustive search or dictionary attack.

## OHOS adaptation

- Direct `cc` build (knock/zimg precedent): the tag archive ships no
  pre-generated `configure` and the build box has no `autoreconf`/`bash`;
  upstream is 2 C files with no `config.h`, so the recipe compiles
  `src/*.c` directly.
- Links OpenSSL (`openssl/3.5.8.1`) and Berkeley DB
  (`berkeley-db/4.8.30`) from Conan, statically (`-static`, R26).
- Upstream ships no test suite (see `1.5.4/test_package/MANIFEST.yml`
  audit); `test_package/test.sh` exercises the real binary (`-h`,
  missing-arg and unknown-option paths).

## References

- https://github.com/glv2/bruteforce-wallet
