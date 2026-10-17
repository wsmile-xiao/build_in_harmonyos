# cahute 0.6 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMake >= 3.16，C 语言，ANSI C90 约束）
- 编译日期: 2026-09-06
- 编译器: clang/clang++ 15.0.4（OHOS aarch64 工具链）
- 状态: built

## 编译步骤
1. `cmake -S <src> -B build-ohos -G Ninja -DCMAKE_BUILD_TYPE=Release -DCAHUTE_CLI=ON -DCAHUTE_LIBUSB=OFF -DCAHUTE_SDL=OFF -DCAHUTE_UDEV=OFF -DCMAKE_INSTALL_PREFIX=<prefix>` → 配置成功
2. `cmake --build build-ohos -j 8` → 构建成功（libcahute.a 静态库 + p7/p7os/xfer9860 CLI 工具）
3. `cmake --install build-ohos --prefix <staging>` → 安装成功
4. 冒烟: `p7 --version`（退出码 0）、`xfer9860 -h`（退出码 0）

构建目标: libcahute(STATIC)、p7、p7os、xfer9860（CaS 需 CAHUTE_CLI_EXPERIMENTAL，默认关闭；p7screen 需 SDL，本配置关闭）。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 github.com 超时 | 执行端直连 GitHub 不可达（仅 gitcode/gh-proxy 可达） | 本地用 gh-proxy 作传输兜底下载官方 tarball；配方仍用官方 https URL，不写入代理地址 |
| 2 | `process_chars.py` 报 ModuleNotFoundError: toml | 上游构建脚本依赖 Python `toml` 模块 | `pip3 install toml` 补齐构建期依赖 |
| 3 | `lib/linkmedium.c` 报 `fd_set`/`struct timeval` 未声明 | OHOS 的 select() 相关类型需显式 `<sys/select.h>`/`<sys/time.h>`；上游仅在部分平台间接包含 | 补丁: 非 WIN32 分支显式 include 两个头（同 bossa E 模式） |
| 4 | libusb 在 ohpcd registry 未发布（conan list 实测 Recipe not found） | 可选特性 CAHUTE_LIBUSB 依赖未发布 | 本配置关闭 CAHUTE_LIBUSB（上游 CMake 选项，FXSDK/Amiga 平台同样默认关闭）；不阻塞核心库与 CLI |
| 5 | SDL 特性依赖 sdl2 | 可选项 | 本配置关闭 CAHUTE_SDL（p7screen 不构建）；sdl2/2.30.10 已发布，如需可后续开启 |

## 源码修改
- `lib/linkmedium.c`: 非 WIN32 分支增加 `#include <sys/select.h>`、`#include <sys/time.h>`（patches/ 补丁，见 conanfile.py patches 列表）

## 依赖版本
- 无运行时/编译期 Conan 依赖（libusb/SDL 特性均已关闭）
- 构建期: python3 + toml（chars 表生成）

## 上游测试申报（R51，完整台账见 reports/upstream-test-enumeration.md）
- 测试目录数: 0
- CTest 注册数: 0（ctest -N → Total Tests: 0）
- 测试框架引用: 0（无 gtest/catch2/doctest/CTest）
- 结论: 官方 tag 0.6 无任何测试声明；source_declared_total=0，configured_executable_total=0，executed_passed_total=0

## 验证结果
```bash
p7 --version        # 退出码 0: "p7 - from Cahute v0.6 (licensed under CeCILL 2.1)"
xfer9860 -h         # 退出码 0: "fx-9860G (SD) communication utility."
ctest -N            # Total Tests: 0
```
- libcahute.a 构建并安装成功，SHA-256 见 adaptation_validation 证据日志
- 鸿蒙专项测试、test_package、消费者验证见对应阶段报告

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（静态库 + CLI 工具，commands.json） |
| conandata.yml | 官方源码声明（url/sha256） |
| patches/0001-*.patch | linkmedium.c sys/select.h+sys/time.h include 补丁 |
| test_package/ | 消费者验证 |
| reports/upstream-test-enumeration.md | 上游测试全量枚举台账 |
| reports/adaptation-validation-*.log | OHOS 构建验证证据 |
---

**编译结束**: 2026-09-06 15:03
**最终状态**: built
