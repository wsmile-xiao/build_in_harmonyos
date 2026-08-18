# libssh2 1.11.1 HarmonyOS adaptation notes

## Build environment

- Build system: CMake
- Evaluation date: 2026-08-17
- Target: OHOS aarch64
- Compiler: `/storage/Users/currentUser/usr/local/bin/clang`
- Compiler version: clang 15.0.4
- Compiler target: `aarch64-unknown-linux-ohos`

## Adaptation

The libssh2 1.11.1 Conan recipe builds the upstream release with OpenSSL as the crypto backend and zlib compression enabled.

The HarmonyOS build uses the real native OHOS clang compiler supplied through Conan `tools.build:compiler_executables`.

The package is built as a shared library and depends on:

- `openssl/3.5.6.1`
- `zlib/1.3.1.1`

## Verification completed

- Source archive downloaded successfully from the official libssh2 release URL.
- Source SHA256 is `d9ec76cbe34db98eec3539fe2c899d26b0c837cb3eb466a56b0f109cabf658f7`.
- Conan recipe Python syntax check passed.
- `git diff --check` passed before the package build.
- `conan create` completed with `CONAN_CREATE_RC=0`.
- Final package contains `libssh2.so`, `libssh2.so.1`, and `libssh2.so.1.0.1`.
- `libssh2.so.1.0.1` is a 64-bit ARM64 ELF shared object.
- Core exported APIs including `libssh2_init`, `libssh2_exit`, `libssh2_version`, `libssh2_session_init_ex`, `libssh2_session_handshake`, and `libssh2_sftp_init` are present.
- Conan `test_package` compiled and linked a real consumer against the packaged library.
- The consumer test executed successfully on HarmonyOS and printed `libssh2 consumer probe ok: 1.11.1`.
- The consumer test covers initialization, version retrieval, session allocation, session timeout set/get, session cleanup, and global cleanup.

## Upstream test verification

- Upstream libssh2 1.11.1 provides an automated test suite.
- With Docker and sshd dependent tests disabled, CTest registered 2 tests that can run independently in the current HarmonyOS PC environment.
- `mansyntax` passed.
- `test_simple` passed.
- Upstream tests executed in the current environment: 2/2 passed.
- The remaining upstream tests require Docker/OpenSSH server or sshd and were not executable in the current environment.

## Final verification

- `conan-verify libssh2 1.11.1` passed.
- Repository `ci/conan/build_and_test.sh archives/l/libssh2/1.11.1` passed.
- Build summary: Success 1, Failed 0.
- Conan `test_package` passed with the packaged libssh2 library.
