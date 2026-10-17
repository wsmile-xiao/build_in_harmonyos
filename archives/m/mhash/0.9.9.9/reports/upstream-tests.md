# mhash 0.9.9.9 upstream tests

Date: 2026-07-30

## Release test inventory

The release source registers 5 Autotools tests in `src/Makefile.am`:

- `hash_test.sh`
- `hmac_test`
- `keygen_test`
- `rest_test`
- `frag_test`

`hash_test.sh` drives the `driver` test binary across many digest vectors.
The other four tests are compiled C test binaries linked against `libmhash`.

## OHOS execution status

Executed during Conan `build()` on the OHOS real device.

- SSH port: old port `56267`
- Runner mode: `heavy --try-lock`
- Run dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-mhash-mhash-0.9.9.9-conan-r7-test-package-20260730-115812-21953`
- Recipe revision: `974b33885624a6e6ddd418a702a32ebb`
- Package revision: `e63f71718400508af68f2e1e99daa400`
- Full reference: `mhash/0.9.9.9#974b33885624a6e6ddd418a702a32ebb:21b17f8b2bc0e9511e276e3d57a23893067cefe5#e63f71718400508af68f2e1e99daa400`

Command executed by the recipe:

```sh
make -j1 check
```

Result:

- `hash_test.sh`: PASS
- `hmac_test`: PASS
- `keygen_test`: PASS
- `rest_test`: PASS
- `frag_test`: PASS

Overall upstream result: 5/5 passed, 0 failed, 100.00%.

## OHOS test script handling

`hash_test.sh` uses `perl -e 'print "a"x1000000'` to generate the standard
one-million-`a` input for SHA/RIPEMD/Whirlpool vectors. The OHOS worker does
not provide `perl`. The recipe replaces only that generator with an equivalent
`python3` command on OHOS. The upstream test vectors, expected digest strings,
and pass/fail assertions are unchanged.

## Added consumer test

The Conan `test_package` builds and runs a C consumer that links `mhash::mhash`
and verifies the MD5 digest of `abc`.

- Result: 1/1 passed, 100.00%.
- Runner L1e destructive negative test: passed, confirming the test genuinely
  depends on the packaged headers and library.
