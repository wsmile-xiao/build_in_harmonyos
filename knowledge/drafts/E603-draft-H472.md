# E603 — Windows Autotools shell paths and OHOS capability guards

## 错误特征

在 Windows 宿主用 w64devkit 构建 OHOS 目标时，Autoconf/libtool 命令可能在 SDK
路径的空格处报 `syntax error: unexpected "("`，或者把 `/f/...`、`/d/...` 形式的
路径判为 `not found`。源码继续通过编译后，OHOS 链接可能报
`sockaddr_storage redefinition` 或 `undefined symbol: pthread_cancel`。

## 触发条件

- 构建系统：Autotools/Automake/libtool
- 阶段：configure、make、link
- 平台：Windows build host，`aarch64-linux-ohos` target
- 典型环境：SDK 或 w64devkit 安装路径带空格；源码用 `__linux__` 直接启用 Linux UAPI

## 根因分析

Windows 宿主的 Conan/Autotools 命令经过 POSIX shell 和 libtool 的 `eval`，带空格的
绝对路径会被拆词；w64devkit 也不一定支持 MSYS `/drive/...` 映射。OHOS 定义
`__linux__`，但 sysroot 的 Linux 兼容头并不保证与 glibc/Linux UAPI 完全一致，
例如 `linux/wireless.h` 会和 OHOS `sys/socket.h` 重复定义结构。OHOS libc 还可能不
提供非必需的 `pthread_cancel`，因此“源码能编译”不等于静态归档可链接。

## 解决方案

### 推荐方案

1. 在任务目录建立无空格视角的 `cc/cxx/ar/ranlib/nm/strip/ld/sed/grep/make/sh`
   wrappers；wrapper 内部再用正确的 Windows 路径调用 SDK/w64devkit 工具。
2. 将 `PATH`、`MAKE`、`SHELL` 绑定到这些 wrappers，确保递归 Make 和 libtool 的
   `eval` 不再看到带空格或 `/drive` 路径。
   recipe 本身不能写入任务绝对路径；从 Conan 的 compiler/make/bash 配置动态推导
   工具目录，并在 build folder 生成引用实际 Bash 的 shell wrapper，供
   `CONFIG_SHELL` 和递归 Make 使用。必要时将 wrapper 路径转换为 Windows 短路径。
3. 用实际能力守卫源码：Linux-only UAPI 采用
   `defined(__linux__) && !defined(__OHOS__)`；线程停止路径在 OHOS 使用可观察的
   stop flag 和 joinable `pthread_join`，其他平台保留原有取消行为。
4. 运行完整构建，并用真实 public-header consumer 链接目标静态库；Windows 只记录
   ELF 生成和链接结果，目标执行留给 W3 真机阶段。

### 禁止做法

- 不要手改生成的 Makefile 或在配方中写入本机 SDK 绝对路径。
- 不要伪造 `pthread_cancel`，也不要仅通过屏蔽链接错误宣称线程生命周期已修复。
- 不要把 Windows 主机能生成 OHOS ELF 当成目标运行测试 PASS。

## 验证

```bash
configure --host=aarch64-linux-ohos ...
make -j1 SHELL=<task>/toolchain/sh
<task>/toolchain/cc.sh -I<stage>/include test.c <stage>/lib/libhamlib.a -lm -o hamlib_test
objdump -f hamlib_test
```

本次 Hamlib 4.7.2 的 configure、`make -j1`、`make install`、真实 package 生成和
精确包引用的 `conan test` 均已完成；review-11 consumer 测试返回 RC=0，package
包含 16 个头文件、2 个静态库和 14 个 CLI。consumer 产物为 `elf64-little` OHOS
目标，未再出现上述头文件/符号错误或致命的 shell 路径拆词失败。

## 本轮增量：动态 shell 闭包、安装闭包与目标进程判定

review-10 证明只把 `SHELL` 设为 `bash` 仍可能被 w64devkit 内部带空格的 `sh`
路径接管，导致 `cJSON.lo` 处失败。review-11 在 build folder 创建由 Conan 配置的
Bash 路径驱动的 shell wrapper，并将生成 Makefile 的 `SHELL` 绑定该 wrapper；完整
构建和精确包 consumer test 通过。recipe 不再含任务机器的 `F:/`、`D:/` 或带空格
的 SDK 路径，避免 CI worker 复用本机路径。

已通过的 `conan create` 在 w64devkit 安装阶段对两段
多行 awk 目录归并程序报告 `not found`。这说明“make 返回 0”不能证明安装树完整：
安装 helper 的 shell/awk 能力与普通 `install` 是独立边界。recipe 保留安装流程，随后
从当前 `source_folder` 的 `include/hamlib` 和 `tests` 显式复制 16 个头文件与 14 个
CLI，并对最终 package 做逐类计数，确认 `libhamlib.a`、`libhamlib++.a` 也存在。

Conan 的 test_package 生成器直接写入 `source_folder`，因此 `CMakeCache.txt`、
`CMakeFiles`、`conan_toolchain.cmake`、生成的 consumer ELF 等不能留在候选源码树；
验证完成后应移出到任务隔离目录，再只保留 `conanfile.py`、`CMakeLists.txt`、`test.c`
和 `MANIFEST.yml`。

OHOS toybox `ps -A` 可能只显示 PID/名称而不显示 `rigctld -t 4532` 参数。r009 的
目标 harness 因此保留 `HAMLIB_TARGET_TEST_SKIP_PS=1`，用两个真实 `rigctld` 进程的
PID 数量作为 ready 条件，并让 `cachetest.sh` 通过 4532/4534 socket 实际完成缓存交互。
这不是跳过测试：r009 单次 launch 的 consumer 为 4/4 assertions，`rigctl -l` 为
RC=0 且输出非空，upstream 为 `12/12 FAILED=0`，随后远端根 postrelease 回读为
`ABSENT`。

证据：`F:\\HarmonyPC\\hamlib-4.7.2-adapt-20260907\\build-r4\\conan-create-review-11.log`
（SHA-256=`591BE848AFF6DAC629E04F46266CD00CE56CD02FA20C84408433BC12450853C5`）、
`F:\\HarmonyPC\\hamlib-4.7.2-adapt-20260907\\build-r4\\conan-test-review-11-correct.log`
（SHA-256=`DD6E81F97FA0C6350A8162327B5C591B2BEDBD35FDBC6666A8A9B3D0E437310F`）、
`w3-r009/evidence/terminal.json` 和 `w3-r009/evidence/postrelease.json`。

## 适用范围与安全边界

该模式适用于 Windows 宿主交叉编译 OHOS 的 Autotools/libtool 项目。wrapper 只属于
任务构建闭包，不能提交为平台路径；每个新 W3 事务仍须重新绑定目标设备、输入哈希、
唯一 launch 和 target-side test evidence。若某 Linux API 在 OHOS 有等价实现，应优先
使用能力探测和等价实现，而不是无条件禁用功能。

显式复制只能修复已定位的安装 helper 缺口，不能把任意安装失败标为成功；目标进程数
只能在同时有真实 socket/API 断言时替代不可见的命令行参数。recipe 或 harness 改动后
必须创建新的 W3 successor，不能重放已 launch 的 predecessor。
