# ucommon 7.0.1 适配笔记

## 源码信息

- **上游**：Debian 维护的 GNU uCommon C++ 7.0.1（GNU 官方最高版本为 7.0.0，Debian/Ubuntu 继续维护到 7.0.1）
- **下载地址**：https://deb.debian.org/debian/pool/main/u/ucommon/ucommon_7.0.1.orig.tar.gz
- **SHA256**：99fd0e2c69f24e4ca93d01a14bc3fc4e40d69576f235f80f7a8ab37c16951f3e
- **解压目录**：commoncpp-7.0.1/

## 构建系统

- 支持 CMake 和 autotools 两种构建系统
- CMakeLists.txt 位于源码根目录
- 使用 CMake 进行 Conan 适配

## 依赖分析

### 核心依赖
- **SSL/TLS 库**（二选一）：
  - gnutls >= 3.0.0（默认选项）
  - openssl >= 1.0.0（可选，通过 `with_ssl=openssl` 切换）
- **PkgConfig**：构建时用于检测依赖

### 可选依赖
- doxygen-latex、graphviz（文档生成，本次不包含）

## 构建选项

- `BUILD_STDLIB`: ON（启用 C++ stdlib）
- `BUILD_STATIC`: 根据 shared 选项动态设置
- `BUILD_TESTING`: OFF（测试由 test_package 负责）
- `BUILD_EXTRAS`: OFF（不构建额外工具）
- `CRYPTO_OPENSSL`: 根据 with_ssl 选项设置
- `POSIX_TIMERS`: OFF（HarmonyOS 可能不支持）

## 输出库

- 默认 `shared=False` 的设备端 Conan 包输出：`libcommoncpp.a`、`libucommon.a`、`libusecure.a`
- 配方仍支持 `shared=True`；本轮消费者测试覆盖默认静态链接配置

## 注意事项

1. Debian 维护版本与 GNU 官方 7.0.0 的差异已通过设备端构建验证
2. HarmonyOS 环境下本轮默认配置未启用 POSIX timers，未发现额外适配错误
3. SSL 库选择会影响运行时依赖，默认使用 GnuTLS；配方通过 `runenv_info` 暴露 Conan 的 GnuTLS 库目录，避免设备系统同名库被错误加载

## 适配变更

- 使用 `PkgConfigDeps` 并把生成目录加入 `PKG_CONFIG_PATH`，使上游 CMake 找到 Conan 提供的 GnuTLS。
- 将可选 OpenSSL 依赖固定为已发布的 `openssl/3.5.6`，避免范围依赖被错误解析为多个参数。
- 按上游实际安装结果声明 `commoncpp`、`usecure`、`ucommon` 三个库，并导出 `ucommon::ucommon` CMake target。
- 修正 `nossl/secure.cpp` 与头文件声明不一致的两个函数签名。
- 消费者测试覆盖 `String`、`Thread::sleep`、条件 TLS 初始化和 SHA-256 摘要；`with_ssl=False` 时不错误要求 TLS 初始化成功。

## 验证结果

- 远端环境：HarmonyOS PC arm64，Conan 2.29.1，host/build profile 为 `ohos-aarch64`。
- `with_ssl=gnutls`：PASS；日志出现 `Found gnutls, version 3.8.10`，消费者程序输出 `Hello from ucommon` 和 `ucommon test passed`。
- `with_ssl=False`：PASS；构建 `nossl` 后端，消费者程序输出 `Hello from ucommon` 和 `ucommon test passed`。
- 上游 `BUILD_TESTING=OFF`，因此未执行上游测试套件；真实 API 验证由 `test_package` 完成。
- 本地静态检查：`git diff --check`、项目 `.venv/bin/python -m py_compile`、`graph validate` 通过；图谱检查仅保留仓库已有的 12 条警告。
- 本机未运行 Conan；未执行 `conan_verify`、PR、CI 或 AI Review，未将设备端验证冒充为发布完成。

---
**编译结束**：2026-08-31
**最终状态**：built
