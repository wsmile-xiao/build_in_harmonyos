# pps-tools 1.0.3 适配笔记

## 编译环境
- 构建系统: makefile（上游手写 Makefile，无 configure）
- 编译日期: 2026-10-03
- 编译器: OHOS SDK clang（`ohos-sdk@26.0.0.18/native/llvm/bin/clang`）
- 状态: built

## 编译步骤

1. 从官方 `codeload.github.com` 取 tag `v1.0.3` 的源码包（`pps-tools-1.0.3.tar.gz`）。
2. `build()` 用配方的 `tools.build:compiler_executables.c`（OHOS clang）执行
   `make CC=<clang> CFLAGS="-Wall -O2 -D_GNU_SOURCE -fPIC" -j1`，产出 4 个可执行文件。
3. `package()` 安装 `bin/{ppstest,ppsctl,ppswatch,ppsldisc,ppsfind}`、
   `include/sys/timepps.h`、`licenses/{COPYING,README.md}`。
4. `test_package` 编译一个头文件消费者（`test_header.c`）并运行
   `test_pps_tools.sh`（12 项检查：程序存在性 + 四个工具的用法/错误路径 + 头文件）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 直接用 brew 的 `clang` 链接时报 `posix_spawn failed: No such file or directory` | brew clang 找不到链接器；Conan OHOS profile 用的是 `ohos-sdk/.../llvm/bin/clang`，并在 buildenv 里注入 `LD=ld.lld` 与 PATH | 配方从 `tools.build:compiler_executables` 取 SDK clang 全路径，借助 Conan buildenv 的 `LD=ld.lld` 完成链接（与 mt-st 同法） |
| 2 | `ppsctl.c` 出现 `unused function 'unbind'` 警告 | 上游在未启用 `PPS_KC_BIND` 时该静态函数未被调用 | 仅警告，不修改上游源码；编译照常通过 |
| 3 | 运行期无法验证 PPS 功能 | 4 个工具都需要真实 `/dev/ppsN` 设备与 `/sys/class/pps`，OHOS 无 PPS 时钟源 | 上游 N=0；消费者测试覆盖编译、参数/用法错误路径与头文件 API 消费，功能级验证需 PPS 硬件 |

## 源码修改

无。上游 tag `v1.0.3` 在 OHOS SDK sysroot 下零补丁编译通过。

## 依赖版本

无三方依赖（仅 OHOS sysroot 的 libc 与 `<linux/pps.h>` 等 uapi 头）。

## 验证结果

```bash
# 消费者（test_package/test_pps_tools.sh，12 项）
PPS_TOOLS_CHECK_SUMMARY checks=12 fails=0

# 头文件消费者（test_package/test_header.c）
timepps-ok mode=3 caps=... seq=0
```

## 注意事项

- 上游无测试套件（release 包仅 4 个 .c + 头 + Makefile），按 §3.6 口径声明上游 N=0，
  另加鸿蒙特有（消费者）测试 12 项。
- `ppstest`/`ppswatch`/`ppsldisc` 无参数时退出码为 1 并打印 usage；
  `ppsctl -h`/`ppswatch -h` 退出码为 0；`ppsctl`/`ppswatch` 无设备时分别打印
  `No command specified!` / `Device name missing!`——消费者测试据此断言。
