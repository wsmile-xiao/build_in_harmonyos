# i2pd 2.58.0-r1 HarmonyOS 适配笔记

## 版本映射

- 上游源码：官方 Git tag `2.58.0`
- Conan 配方：`i2pd/2.58.0-r1`
- 源码 SHA-256：`5ff650c6da8fda3522c10ec22889a7fd1c6b5d1af42c24531d84c36f6cc49019`

## 构建策略

- 使用 Conan 2 的 `CMakeToolchain` 与 `CMakeDeps`，不从裸 shell 环境变量读取编译器或链接参数。
- 精确依赖 `boost/1.90.0.3`、`openssl/3.5.6`、`zlib/1.3.1`。`boost/1.90.0.3` 是 ohpcd 制品仓中已发布的 CMake 构建版本，组件覆盖上游 `find_package(Boost REQUIRED COMPONENTS system filesystem program_options)`；`boost/1.84.0` 未在制品仓发布（origin/main 仅有历史 manifest/notes，无配方）。`zlib/1.3.1` 已在远端发布；i2pd 仅链接 PIE 可执行文件及静态核心库，实测不需要 `1.3.1.1` 的共享库 PIC 修复。
- 构建 `i2pd` 命令和上游三个核心库；关闭未声明依赖的可选 UPnP。
- 上游 CMake 测试以 `Check >= 0.9.10` 作为配置阶段门禁。已依据仓库现有 `archives/c/check/0.15.2` 归档在本地构建 Check，随后以 `BUILD_TESTING=ON` 编译、执行全部 13 项 CTest，结果 13/13 通过；上游测试目标实际未链接 libcheck。
- 消费侧兼容旧版 `openssl/3.5.6` Conan 元数据，为 CMakeDeps 补充 `OpenSSL::SSL` 与 `OpenSSL::Crypto` 组件映射，不修改 OpenSSL 配方。
- 通过自动生成的 `0001-build-CMakeLists.txt.patch` 兼容现代 CMake 的 `OpenSSL_FOUND` 与上游旧检查变量 `OPENSSL_FOUND`。

## test_package

消费者测试直接定位被打包的 `bin/i2pd` 并执行：

1. `i2pd --version`
2. `i2pd --help`
3. 向 `--conf` 传入含未知选项的配置，断言真实配置解析器拒绝该配置。
---

**编译结束**: 2026-08-11 22:43
**最终状态**: built
