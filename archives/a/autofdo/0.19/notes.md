# AutoFDO 0.19

The recipe builds the upstream autotools project for OHOS armv8 with LLVM
support disabled (`--without-llvm`; `create_llvm_prof` is therefore
non-functional, which is expected). The vendored `perf_data_converter` and
`protobuf` git submodules are fetched separately because they are not part of
the tag tarball.

Source patches cover OHOS portability:
- `basename()`: OHOS sysroot only provides the POSIX `char *basename(char *)`,
  so the calls use `libgen.h` plus a `strdup`/`free` mutable buffer
  (`profile_creator.cc`, `sample_reader.cc`).
- byteswap macros: the sysroot `byteswap.h` defines `bswap_16/32/64` as macros
  that clash with the project's own functions; they are `#undef`'d in
  `base/port.h` and the vendored protobuf `port.h`.
- `NATIVE_ELF_ARCH`: `__WORDSIZE` is undefined on OHOS, so the word-size chain
  falls into `#error`; aarch64/LP64 now selects `Elf64`.

The build depends on `openssl/3.5.6` (MD5 in quipper) and `elfutils/0.191`
(libelf for ELF parsing).

## Test Status

The upstream 0.19 release has no `make check` target. The package smoke test
starts `create_gcov` and verifies its gflags command interface. A real profile
conversion fixture is still required before this recipe is eligible for the
"all test cases passed" review path.
