# procps 鸿蒙系统编译指南

procps-ng（/proc 文件系统工具集）：`ps`、`top`、`free`、`uptime`、`vmstat`、
`w`、`watch`、`slabtop` 等系统监控命令行工具，核心为 **libproc2** 进程状态
查询库（C API）。

## 概述

| 项目 | 内容 |
|------|------|
| 上游 | https://gitlab.com/procps-ng/procps |
| 许可证 | GPL-2.0-or-later |
| 构建系统 | autotools（configure + make） |
| 类型 | 库（libproc2）+ CLI 工具集混合型 |
| 依赖 | ncurses/6.6（conan，静态宽字符 ncursesw，仅 top/slabtop/watch 需要） |

## 版本索引

- procps 4.0.7：当前 Conan 配方（详见 `4.0.7/`）

## 关键适配点（OHOS）

1. **musl 无 strverscmp**：`local/strverscmp.c` 补入 libproc2 源列表
   （0001/0002 补丁，E534）。
2. **平台识别**：config.guess/sub 增加 HarmonyOS 分支，triplet
   `aarch64-unknown-linux-ohos`（0003/0004 补丁，E007）。
3. **HMDFS umask 限制**：configure 两处 `umask 077` 移除（0005 补丁，
   E011/E114）。
4. **utmpx 不可用**：w.c 在 `__OHOS__` 下 `#undef HAVE_UTMPX_H`
   （0006 补丁，E121）。
5. **ncurses 静态链接**：top/slabtop/watch 链接 conan ncurses/6.6 的
   静态 libncursesw.a——通过 PKG_CONFIG_PATH 指向 conan 包（系统无
   ncurses 头文件与 ncursesw.pc，探测只会命中 conan 包）。共享库会与
   系统 shell 依赖的 libncursesw.so.6 冲突（R4/R26），OHOS 强制静态。
6. **可选依赖全禁**：`--disable-nls --disable-numa --without-systemd`
   （gettext/libnuma/systemd 在 OHOS 均不需要）。

## 已知环境限制

上游 `make check` 共 8 个测试程序，OHOS 实测 **7 PASS / 1 FAIL**：
`test_version` 的 `procps_linux_version()` 子用例失败——HongMeng 内核
`/proc/sys/kernel/osrelease` 为非标准 `"HongMeng Kernel 1.12.0"` 串且
`/proc/version` 不可读（Permission denied），sscanf 无法解析出 a.b.c
版本。属环境性失败，未修改上游断言（详见 `4.0.7/notes.md`）。同程序
`LINUX_VERSION` macro 子用例 PASS。另有 `/usr/include/linux/capability.h`
缺失编译警告，不影响结果。

## 消费方式

```bash
conan install --requires=procps/4.0.7
```

- 库：`-lproc2`，头文件 `include/libproc2/*.h`（8 个），pkg-config 名
  `libproc2`
- 工具：`bin/` 下 17 个命令 + `sysctl`（conan 包内统一在 bin/）
- 核心 C API：`procps_uptime()`、`procps_loadavg()`、`procps_pids_new/
  get/unref()`、`procps_sysinfo()` 等（`misc.h`/`pids.h`）
