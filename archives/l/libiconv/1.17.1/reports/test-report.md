# libiconv 1.17.1 test evidence

## Conan verification

- Recipe: `libiconv/1.17.1#8545618022496ff2c0d87bbd8ac61f86`
- Package ID: `4b977264131a1c74e82bd6bb51b63cc9aadc4cfa`
- Package revision: `fcd1c297e8323d8ba957441b00499c71`
- Command: `conan create archives/l/libiconv/1.17.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=default --build=missing -tf=./test_package`
- Result: exit code 0
- Full log SHA-256: `31c928621852305a4a41b77a23c99dff0bc96536c7d64a06d57c70636c8e805c`

## Upstream tests

- Command: `make -j1 check`
- Working directory: Conan build folder `build-release/`
- Result: exit code 0
- Test targets: recursive upstream `check` target, including `tests/`
- Expanded test commands: 201
- Passed: 201/201
- Standalone check log SHA-256: `559bf1bf2ded1eb47d70b14213a2cde3291fdb922a44befd9feb1ce0c392f18e`

## Consumer tests

- Command: `./test_libiconv`
- Result: exit code 0
- Assertions: 3/3
- Coverage: UTF-8→ASCII, EUC-KR→UTF-8, UTF-8→ISO-2022-JP
- Consumer output is included in the Conan verification log above.

## Package content

- `libiconv.a` and `libcharset.a` are present.
- No `*.la` files are present in the final package.
