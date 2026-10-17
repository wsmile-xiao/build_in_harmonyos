# tiny-aes-c

> A small C++ AES-256-CTR library with deterministic array-based APIs.

tiny-aes-c packages the CryptoManiac/tiny-aes-cpp project. The public API
offers single-block and vector AES-256-CTR operations and has no third-party
dependencies. This package is distinct from the C tiny-AES-c project by kokke,
which is archived separately as tiny-aes.

## HarmonyOS adaptation

- The upstream snapshot has no build system, so the Conan recipe compiles
  aes.cpp directly with the profile C++ compiler and archives a static library.
- The source is pinned to commit b2761c223710.
- The portability patch adds the standard header required by std::copy_n,
  replaces inactive-union-member type punning with explicit byte mapping, and
  avoids pointer arithmetic on an empty vector.

## Dependencies

None.

## Reference

- [Upstream repository](https://github.com/CryptoManiac/tiny-aes-cpp)
- [The Unlicense](https://unlicense.org/)
