# librhash 1.4.4 适配笔记

## 软件简介

LibRHash 是 RHash 工具套件的核心组件，提供 MD5、SHA1、SHA256、SHA512、Torrent、TTH、
ED2K、AICH 等哈希算法的共享库实现，供 lgogdownloader 等下游项目做文件完整性校验。

## 构建要点（configure + make）

1. **工具链**：`./configure --cc=clang --ar=llvm-ar` 指定鸿蒙工具链，
   `--enable-lib-shared --disable-static --disable-openssl` 仅构建共享库并关闭可选
   OpenSSL 依赖。
2. **Makefile 修复**：上游 `SOLINK_TARGET` 依赖在 `LIBRHASH_SO_MAJ == LIBRHASH_SHARED`
   时返回非零，会中断构建。`build()` 中执行
   `sed -i 's/$(SOLINK_TARGET)//' librhash/Makefile` 移除该依赖。
3. **仅构建库**：`make -C librhash -j1 lib-shared|lib-static`，跳过 rhash CLI 编译
   （目标绑定 shared 选项）。
4. **SONAME 符号链接**：上游产物为 `librhash.so.1`，`package()` 创建
   `librhash.so -> librhash.so.1` 符号链接，保证 CMake `find_package(Rhash CONFIG)`
   能发现 unversioned 库名。
5. **OHOS 产物签名**：`build()` 对 `librhash/*.so*` 执行
   `llvm-objcopy --remove-section .codesign` + `binary-sign-tool -selfSign 1` 自签名，
   保证鸿蒙平台可加载；签名工具路径从环境变量（LLVM_OBJCOPY / BINARY_SIGN_TOOL /
   LLVM_READELF）读取，避免硬编码。共享模式未产出 .so 时抛 ConanException（不静默）。
6. **rhash CLI**：同时构建并打包 rhash 命令行工具到 `bin/`（响应 AI 检视与人工评审
   建议），test_package 使用 CLI 执行上游移植断言。

## 测试说明

- 上游 RHash 自带 `tests/test_rhash.sh`（针对 rhash CLI）；本适配将核心断言
  （--message CRC32/MD5/SHA1/SHA256、空消息 MD5、--list-hashes）移植为
  `test_package/test_rhash_cli.sh`（assertion_count=6），CI L0/L1 门禁通过。
- test_rhash_cli.sh 使用 `set -euo pipefail`（bash 扩展），test_package 统一用
  `CONFIG_SHELL`（OHOS 默认 `/data/service/hnp/bin/bash`）执行，避免 dash 不支持
  pipefail 导致失败。

## 依赖与发布

- 无外部依赖（所有哈希算法内置，自包含 C 库）。
- `package_info()` 暴露 `Rhash::Rhash` imported target、`cmake_file_name="Rhash"`、
  `pkg_config_name="librhash"`，供下游 find_package 使用。
- 版本级 status: built，可直接发布；下游 lgogdownloader 3.18 通过 Conan 拉取。
