# libbrotli 1.1.0 适配笔记（HarmonyOS PC）

## 适配范围

- 上游：Google Brotli `v1.1.0`
- 构建系统：CMake
- Conan 包：`libbrotli/1.1.0`
- 上游库名保持 `brotlicommon`、`brotlidec`、`brotlienc`
- 依赖：无第三方依赖

## 构建方案

配方自发现 OHOS SDK 的 `ohos.toolchain.cmake`，使用 `arm64-v8a`、共享库和
上游 CTest。构建树内测试程序和共享库先执行 OHOS ELF 自签，再运行 CTest；
安装后对 `lib/**/*.so*` 与 `bin/` 中的 ELF 产物再次签名。

`libbrotli` 是平台任务/Conan 包名，不能与产物库名混淆：消费者仍通过
`<brotli/encode.h>`、`<brotli/decode.h>` 和 `libbrotli*.so` 使用上游接口。

## 测试设计

- 上游 CTest：对多组文本和源码数据执行 Brotli 压缩/解压逐字节往返。
- `test_package`：同时链接 encoder、decoder、common 三个组件，验证真实压缩、
  压缩率、解压长度和逐字节一致性。

官方 tag 归档被上游 `.gitattributes` 的 `export-ignore` 白名单裁剪，`tests/testdata` 只带
4 个文件，直接构建只生成 14 个用例。配方 `source()` 从上游官方 PyPI sdist
（`Brotli-1.1.0.tar.gz`，`MANIFEST.in` 显式 `include tests/testdata/*`）取回同 tag 的
全量 67 个测试语料，恢复上游完整测试覆盖。

本地交叉验证结果：上游 CTest **72/72 通过**（28 个 roundtrip、44 个 compatibility），
消费者用例 **5/5 断言通过**。

## 平台注意事项

- OHOS 测试程序必须先代码签名，否则执行报 `Operation not permitted`。
- 动态测试需将构建树中的 `c/lib` 或 `lib` 加入 `LD_LIBRARY_PATH`。
- `make jobserver mkfifo` 在 HMDFS 上可能给出非致命权限提示，不影响产物。
