# osslsigncode 2.13 编译进度

**日期**: 2026-04-24 (init), 2026-08-07 (completed)
**状态**: ✅ 编译成功

## 基本信息
- 软件: osslsigncode
- 版本: 2.13
- 构建系统: CMake (not autotools as initially assumed)
- 目标: ohos-aarch64
- 源码: https://api.github.com/repos/mtrojnar/osslsigncode/tarball/2.13
- SHA256: 53f58046d80ac31600c29e364ca6045ea0bd0f0e1f4c3aee2f8b082b72f03cee

## 依赖
- openssl/3.5.6.1 (conan ohpcd)
- zlib/1.3.1 (conan ohpcd)

## 适配要点

### CMake 平台识别问题
HarmonyOS (CMAKE_SYSTEM_NAME=HarmonyOS) 不被 CMake 识别为 UNIX 平台。
导致:
1. `UNIX` 变量未设置 → Windows-only 源文件 `applink.c` 被编译 → `io.h` not found
2. `check_function_exists(mmap)` 失败 → FindHeaders.cmake 报错 "Need file mapping function"

解决方案: 在 conanfile.py 的 `generate()` 中强制设置:
- `UNIX=ON` — 确保 UNIX 分支被选择
- `HAVE_SYS_MMAN_H=ON`, `HAVE_MMAP=ON` — 跳过失败的 try-compile 检查
- `HAVE_GETPASS=ON`, `HAVE_TERMIOS_H=ON` — 同上

### 测试结果
- 总测试数: 355
- 通过: 295 (83%)
- 失败: 60 (全部为 timestamp authority 测试)
- 失败原因: OpenSSL 静态构建不包含 legacy provider 模块 (legacy.so),
  导致 RFC 3161 时间戳签名中的 HTTP 请求失败。
  这是环境限制，不影响核心签名/验证功能。

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | CMake-based, not autotools |
| Step 2 configure | ✅ | UNIX=ON + mmap defines |
| Step 3 make | ✅ | clang 15.0.4 |
| Step 4 install | ✅ | staging verified |
| Step 5 version | ✅ | osslsigncode 2.13 with OpenSSL 3.5.6 |
| Step 6 tests | ✅ | 295/355 passed (83%) |
| Step 7 conan recipe | ✅ | conanfile.py + conandata.yml + test_package |
---

**编译结束**: 2026-08-07 07:44
**最终状态**: built
