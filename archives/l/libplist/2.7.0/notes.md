# libplist 2.7.0 HarmonyOS 适配记录

## 来源与依赖

- 上游版本：libplist 2.7.0
- 上游地址：https://github.com/libimobiledevice/libplist/releases/tag/2.7.0
- 下载地址：https://github.com/libimobiledevice/libplist/releases/download/2.7.0/libplist-2.7.0.tar.bz2
- SHA256：`7ac42301e896b1ebe3c654634780c82baa7cb70df8554e683ff89f7c2643eb8b`
- Conan 第三方依赖：无。`libcnary` 随上游源码提供；系统数学库由工具链处理。

依赖预检已确认配方没有声明的第三方 Conan 依赖。`ohpcd` 远程的配方占用探测受当前环境网络策略限制，未将其作为依赖缺失依据。

## 构建适配

- 构建系统：Autotools。
- `settings.os` 仅接受 `Linux` 和 `OHOS`。
- 使用 `--build=aarch64-unknown-linux-gnu` 绕过 `config.guess` 对 OHOS 的识别缺口。
- 使用私有 `.hmos_fix/mktemp` 包装器，让 Autoconf 使用目录创建回退路径，避免 HMDFS 临时目录权限导致 `config.status` 失败。
- 使用 `--without-cython`，不构建 Python 绑定。
- 保留 `plistutil` 工具，并启用上游测试框架。
- 默认静态构建，链接库名为 `plist-2.0`，pkg-config 名称为 `libplist-2.0`。

## 测试范围

上游 `test/Makefile.am` 声明 41 个 `.test` 测试脚本和 7 个辅助测试程序，统一入口为 `make check`。本包消费者测试包含：

1. `test.c`：C API 创建字典、XML 序列化、反序列化及布尔值校验。
2. `test_ohos.c`：仅允许在定义 `__OHOS__` 的目标上编译，验证 2.7.0 的 Unix 时间 API，并在 HarmonyOS 临时目录完成文件写入、读取和时间戳回读。

## 验证记录

- 本地仓库 CI：包级静态预检 PASS；`test_v1222.py` PASS（21/21）。完整 `run_all.py` 未能在当前 Windows 环境收敛：`test_smoke.py` 依赖 POSIX `fcntl`，`test_v1218.py` 受到 Windows 默认 GBK 解码和 `stderr=None` 兼容性问题影响，另有 `test_v1220.py` 使用的 CI 固定 Git 路径不存在，以及 `test_v1221.py` 的 2 项既有目录基线计数失败；均未指向 libplist 包文件。
- Conan package build：WSL Ubuntu、Conan 2.29.1、`wsl-build` profile 构建 PASS；Autotools `make -j1`、`make -j1 check` 和安装打包完成，静态链接所需系统数学库已通过 `system_libs=["m"]` 声明。
- Conan test package：PASS；CMakeDeps/CMakeToolchain 配置、构建和 `test_libplist` 消费者测试均通过，输出 `PASS: libplist C XML round-trip test`。Linux Conan profile 不执行 OHOS 条件测试，HarmonyOS 测试单独在 hdc 虚拟机执行。
- 上游 `make check`：WSL 实测 41/41，通过 41、跳过 0、失败 0、错误 0。HarmonyOS 虚拟机按同一批上游脚本实测也是 41/41；虚拟机缺少 `diff`，测试时临时注入宿主机编译的兼容工具，未修改上游测试脚本。
- HarmonyOS 6.0 `hdc` 测试：连接 `127.0.0.1:5555` 的 x86_64 虚拟机，使用 OpenHarmony SDK clang 15.0.4 交叉编译 C/C++ 源码、`plistutil`、通用消费者和 `test_ohos`；两项消费者测试均 PASS，`test_ohos` 输出 `PASS: HarmonyOS Unix-date and temp-file test`，`plistutil` 输出版本 `2.7.0`。
