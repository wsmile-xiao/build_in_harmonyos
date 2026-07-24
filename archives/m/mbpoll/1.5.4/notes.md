# mbpoll 1.5.4 适配笔记

## 概述
- 上游：https://github.com/epsilonrt/mbpoll （tag v1.5.4）
- 类型：命令行工具（Modbus 主站仿真，RTU/串口 + TCP）
- 构建系统：CMake
- 许可证：GPL-3.0-only

## 依赖处理（关键）
mbpoll 唯一运行时依赖是 libmodbus（>= 3.1.7）。**libmodbus 未发布到 OHOS 制品仓**
（archives 中 libmodbus 3.1.10/3.1.12 仅 `built`、无 conanfile.py、无任何配方 require 它），
按 R36/W0 不能 `self.requires`，故在配方内 **vendor libmodbus 官方源码静态编译**：

- 选用 **libmodbus.org 官方发布包 3.1.7**：它自带预生成 `configure`（GitHub 源码归档需要
  autogen/autotools，而构建机无 autotools）。
- `source()` 同时下载 mbpoll 与 libmodbus（libmodbus 解到 `libmodbus/` 子目录）。
- `build()` 先用 autotools 把 libmodbus 编成静态库装到 build 目录下的 `libmodbus-root/`，
  生成 `libmodbus.pc`；再通过 `PKG_CONFIG_PATH` 让 mbpoll 的 `pkg_check_modules` 找到它。
- 最终包只含 `bin/mbpoll`（libmodbus 已静态链入，`readelf -d` 仅见 `libc.so`）。

## 三个适配补丁

### 0001-hardcode-version-no-git-dep.patch
上游 `cmake/GitVersion.cmake` 用 `git describe --tags` 取版本号，取不到时直接
`FATAL_ERROR` 中止 configure（源码包/构建树非匹配 tag 的 git 仓库时会触发，例如上层目录
恰好是个不相关的 git 仓库）。改为硬编码版本 1.5.4，直接 `file(WRITE)` 生成 `version-git.h`。

### 0002-make-libmodbus-quirks-optional.patch
mbpoll 无条件引用 `MODBUS_QUIRK_MAX_SLAVE` / `MODBUS_QUIRK_REPLY_TO_BROADCAST` /
`modbus_enable_quirks()`（对应 `-Q`/`-X` 选项）。**libmodbus 3.1.7 早于 quirks API**
（3.1.12 才有，但 3.1.12 GitHub 归档需 autogen、官方站无 3.1.8+ 发布包）。用
`#if defined(MBPOLL_ENABLE_LIBMODBUS_QUIRKS)` 守卫该代码块；本构建不定义该宏，
`-Q`/`-X` 选项可解析但为空操作（已记录为已知限制）。mbpoll 核心 Modbus 读写功能不受影响。

### linux/serial.h shim（conanfile.py 内 save()）
musl/OHOS 工具链无 `linux/serial.h` 内核头（`modbus-rtu.c` 在 `HAVE_DECL_TIOCSRS485`
下为 RS485 ioctl 包含它）。提供最小标准定义（`struct serial_rs485` + `SER_RS485_*`）。

## 其它适配点
- 禁用 piduino（`MBPOLL_CUSTOM_RTS_GPIO=OFF`）：GPIO RS-485 RTS 在 OHOS 无此设施。
- `CMAKE_SKIP_RPATH=ON`：libmodbus 静态链接无需 RPATH，且规避 cmake 安装期
  `CMakeRelink.dir` 报错。
- libmodbus configure 传 `--build=aarch64-unknown-linux-gnu --host=...`：其自带
  config.guess 早于 OHOS，在 HarmonyOS worker 上识别失败；显式标准三元组（build==host
  原生）绕过 config.guess 且能过 config.sub 校验。
- E011：libmodbus configure/config.status 的 `umask 077/000` 在 HMDFS 上建目录无写权限，
  relax 为 `umask 022`。

## 编译验证（本地构建容器，HarmonyOS aarch64 同源工具链）
```
conan create archives/m/mbpoll/1.5.4 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → exit 0；test_package 通过（mbpoll -V 输出 1.5.4）
```

## 二进制安全检查（L4）
```
file bin/mbpoll → ELF, arm64, dynamic (/lib/ld-musl-aarch64.so.1)
readelf -d → NEEDED: libc.so （libmodbus 已静态链入，不出现）
readelf -h → Type: DYN (PIE)
readelf -l → GNU_STACK（NX）+ GNU_RELRO；FLAGS_1: PIE
```
PIE / NX / RELRO 齐全。

## 上游测试（本地实测，CI 未接入门禁）
上游 `tests/` 下两个 CTest 单测（无框架，手写 harness），配方 `BUILD_TESTING=OFF`
未把它们接进 conan build()，按本仓惯例（同 strace/qrencode）本地实跑取数。

源码：mbpoll-1.5.4/tests/test_utils.c、tests/test_serial.c（已套用两个补丁后构建）。

| 测试程序 | 用例计数方式 | 通过/总数 | 说明 |
|----------|-------------|-----------|------|
| test_utils.c | 10 个测试函数 | 10/10 | iGetIntList 解析(5) + 字交换 lSwapLong/fSwapFloat(5) |
| test_serial.c | 程序自计数 g_tests_run | 23/23 | 串口枚举转串(flow/databits/stopbits/parity) |
| **合计** | | **33/33（100%）** | |

实测输出摘录：
```
$ ./bin/test_utils    → All tests passed.            (exit 0)
$ ./bin/test_serial   → Tests run: 23, Tests failed: 0, ALL TESTS PASSED  (exit 0)
$ ctest               → 100% tests passed, 0 tests failed out of 2
```

反向验证（防假绿）：把 test_serial 换成 `exit 1` 桩重跑 ctest → `test_serial (Failed)`，
确认 harness 真能抓到失败。

## 已知限制 / TODO
- `-Q`（MAX_SLAVE）/`-X`（REPLY_TO_BROADCAST）quirks 选项为空操作（libmodbus 3.1.7 无该 API）。
- 上游测试为本地实测，CI 侧未接入门禁（配方 `BUILD_TESTING=OFF`）。

## 鸿蒙真机复测

- 日期：2026-07-19
- 环境：HarmonyOS HAD 206.1.0 真机（aarch64 musl，OHOS SDK clang 15.0.4）
- 结果：✅ 通过（conan create + test_package 真机原生执行）
