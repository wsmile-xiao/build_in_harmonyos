# zcfan 1.4.0 for HarmonyOS

## 概述

zcfan 是 ThinkPad 的**零配置风扇守护进程**。它周期读取内核 hwmon 暴露的温度传感器，
在 `off / low / medium / maximum` 四档间驱动 ThinkPad ACPI 风扇接口，并维护内核
watchdog 心跳；检测到系统 resume（CLOCK_BOOTTIME 相对 CLOCK_MONOTONIC 跳变）后重写档位。

本仓库收录其在 HarmonyOS / OpenHarmony PC（aarch64）上的 Conan 适配。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | zcfan |
| 版本 | 1.4.0 |
| 上游仓库 | https://github.com/cdown/zcfan |
| 源码归档 | https://github.com/cdown/zcfan/archive/refs/tags/1.4.0.tar.gz |
| sha256 | `33e4944303c778581b6471c79e1273a5668917542e412c8125f028133b684718` |
| 许可证 | MIT |
| 构建系统 | makefile（上游手写 Makefile） |
| 包类型 | application（CLI 工具） |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 架构 | aarch64-linux-ohos |
| 编译器 | clang 15.0.4（OHOS toolchain，musl sysroot） |
| 三方依赖 | 无（仅 libc/POSIX） |
| 补丁 | 1 个（`0001-zcfan.c.patch`，编译器可移植性） |

## 编译步骤

```bash
conan create archives/z/zcfan/1.4.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=default
```

配方内部实际执行的构建动作只有一条（见 `conanfile.py` 的 `build()`）：

```bash
make -j1 CC=clang
```

上游 `CFLAGS` 原样保留（`-std=gnu99 -O2 -pedantic -Wall -Wextra -Wwrite-strings
-Warray-bounds -Wconversion -Wstrict-prototypes -Werror`），不额外注入编译标志。

## 适配要点

1. **零依赖** — 只 include libc/POSIX 头文件，无需 conan 依赖，无 R36 依赖链风险。
2. **唯一补丁：clang `-pedantic` 下的 GNU 变参宏**
   上游 `info()/err()` 使用 `##__VA_ARGS__`。GCC 静默接受，clang 在 `-pedantic` 下报
   `-Wgnu-zero-variadic-macro-arguments`，叠加上游自带的 `-Werror` 变成致命错误。
   上游 CI 不会暴露它：`ci.yml` 只跑 `make lint` / `make clean clang-tidy` /
   `make clean clang-everything`，而最后一个目标显式带
   `-Wno-gnu-zero-variadic-macro-arguments`，且上游从不用 clang 跑裸 `make`。
   补丁改为标准 C99 全变参宏，输出逐字节不变，无平台宏。
3. **不使用上游 `make install`** — 该目标把构建期 `$(bindir)` 用 `sed` 展开进
   `zcfan.service`（systemd unit），会把 Conan 缓存路径写进交付文件；OHOS 亦无 systemd。
   配方直接 copy 真实产物：`bin/zcfan`、`share/man/man1/zcfan.1`、`licenses/LICENSE`。
4. **运行期硬件契约** — zcfan 需要 `/proc/acpi/ibm/fan`（`thinkpad_acpi`）。宿主机无该接口时
   按上游设计 `abort()`（退出码 134），与 Linux 非 ThinkPad 机器行为一致。带任意参数运行
   则打印帮助并 exit 0，不触碰硬件。

## 测试

| 层级 | 内容 | 结果 |
|------|------|------|
| 上游测试 | 无运行时测试套件；真实入口为 3 个静态检查步骤（`make lint` / `make clean clang-tidy` / `make clean clang-everything`） | 3 / 3 通过 |
| 鸿蒙专项（新增） | `tests/ohos_spec.sh` —— 产物平台契约与 ABI 断言 | 见测试报告 |
| Conan L1 | `test_package/test.sh` —— 5 条打包后消费者冒烟用例 | 见测试报告 |

上游测试清点与逐项结果见 `1.4.0/test_package/MANIFEST.yml` 与 `1.4.0/notes.md`。
