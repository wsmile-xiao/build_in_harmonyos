# 内核态/DKMS 交付物（Kbuild obj-m）不可由 OHOS PC 用户态适配框架交付

> 草稿来源：lenovolegionlinux 0.0.20 适配任务（平台任务 `contrib-13021`）
> 状态：DRAFT（待评审转正式 E 条目）
> 日期：2026-09-20　实测环境：DevEco Studio HarmonyOS 26 SDK native clang 15.0.4，target `aarch64-linux-ohos`，sysroot `os=OHOS 6.0 / arch=armv8`

## 1. 适用场景（什么时候该想起这条知识）

任务里的三方库，其**交付物本身位于内核空间**——典型特征是上游构建方式为内核 Kbuild：

```make
KERNELVERSION  ?= $(shell uname --kernel-release)
KSRC := /lib/modules/$(KERNELVERSION)/build
obj-m += legion-laptop.o
all:
	$(MAKE) -C $(KSRC) M=$(shell pwd) modules
```

或存在 `dkms.conf`（`BUILT_MODULE_NAME` / `DEST_MODULE_LOCATION` / `AUTOINSTALL`）、发行版
kernel driver 打包脚本。此类任务即使语言标记为 C/C++，也**不属于** OHOS PC 用户态 conan
适配流程的适用对象。

## 2. 判定清单（全部为可复现命令）

| 步骤 | 命令 | 判据 |
|---|---|---|
| ① 交付物是否内核态 | `grep -n "obj-m\|KERNELDIR\|KSRC\|/lib/modules" Makefile */Makefile` | 命中 `obj-m` / `KSRC` / `/lib/modules` ⇒ 内核态 |
| ② 头文件核验 | `grep -hE '^[[:space:]]*#[[:space:]]*include[[:space:]]*<[^>]+>' *.c \| sed -E 's/.*<([^>]+)>.*/\1/' \| sort -u \| while read -r h; do test -e "$SYSROOT/usr/include/$h" && echo present $h \|\| echo MISSING $h; done` | 统计「缺失」与「UAPI 桩」数量；**头名勿用 `tr -d "#include<>"` 提取**（`tr -d` 删字符集合，会把 `linux/module.h` 变成 ` x/mo.h`，令所有头恒报 MISSING） |
| ③ UAPI 桩判定 | `grep -c "_UAPI_\|MODULE_LICENSE\|module_init" $SYSROOT/usr/include/linux/module.h` | 行数极少（20~62 行）且不含模块注册 API ⇒ 桩 |
| ④ 内核构建树 | `test -e $SYSROOT/usr/src -o -e $SYSROOT/usr/include/linux/kconfig.h` | 不存在 ⇒ 无构建树 |
| ⑤ 实测编译 | `clang --target=aarch64-linux-ohos --sysroot=$SYSROOT -fsyntax-only <module>.c` | 应失败于第一个内核内部头 |
| ⑥ 是否存在不裁剪路径 | 检查用户态子集是否独立可用 | 若子集功能依赖内核模块接口 ⇒ 交付该子集即裁剪，禁止 |

## 3. 实测证据（lenovolegionlinux 0.0.20）

**交付物**：`kernel_module/legion-laptop.c`（单文件 191,630 bytes），Kbuild + DKMS，安装目标
`/lib/modules/<kver>/kernel/drivers/platform/x86`，`dkms.conf` 中 `AUTOINSTALL="yes"`。

**头文件核验**：16 个 include 全为内核内部头；OHOS sysroot 提供 **5/16**，其中 4 个是 `_UAPI_` 桩：

| 结果 | 头文件 |
|---|---|
| 缺失（11） | `linux/acpi.h`、`asm/io.h`、`linux/debugfs.h`、`linux/delay.h`、`linux/dmi.h`、`linux/leds.h`、`linux/hwmon.h`、`linux/hwmon-sysfs.h`、`linux/moduleparam.h`、`linux/platform_device.h`、`linux/platform_profile.h` |
| UAPI 桩（4） | `linux/kernel.h`(25 行)、`linux/module.h`(**23 行，仅 2 个常量**)、`linux/types.h`(39 行)、`linux/wmi.h`(62 行) |
| 普通头（1） | `linux/version.h`(20 行) |

`linux/module.h` 全文实质只有两行常量定义（`MODULE_INIT_IGNORE_MODVERSIONS 1`、
`MODULE_INIT_IGNORE_VERMAGIC 2`）；`MODULE_LICENSE` / `module_init` / `module_exit` /
`THIS_MODULE` / `struct module` / `__init` 命中数**均为 0**。

**内核构建树**：`usr/src`、`usr/include/linux/kconfig.h`、`usr/include/config`、
`usr/include/generated` 均不存在。

**命令修正后的复核（2026-09-20，同一 sysroot 重跑）**：修掉 `tr -d` 缺陷后逐头核验结果为
**16 个头 / 5 present（`linux/kernel.h`、`linux/module.h`、`linux/types.h`、`linux/version.h`、
`linux/wmi.h`）/ 11 MISSING**，与本表一致；用原 `tr -d` 写法复现则为 **16/16 MISSING**（伪证据，
证明该提取方式必须用 sed 按尖括号抽取）。

**实测日志**：

```text
# ① 交叉编译内核模块源码
$ clang --target=aarch64-linux-ohos --sysroot=<sysroot> -fsyntax-only kernel_module/legion-laptop.c
legion-laptop.c:62:10: fatal error: 'linux/acpi.h' file not found
1 error generated.                       # exit 1

# ② 上游 Kbuild 方式（KSRC 指向 sysroot）
$ make -C <sysroot> M=<...>/kernel_module modules
make: *** No rule to make target 'modules'.  Stop.     # exit 2
```

**硬件绑定**：DMI 匹配表限定 `DMI_SYS_VENDOR == "LENOVO"`（Legion 5 / 5 Pro / 7）；源码中
`wmi_` 395 次、`acpi_` 131 次、`platform_driver` 4 次；接口路径 `.../PNP0C09:00`（ACPI EC）。

**不得裁剪**：`python/legion.py` 硬编码 `LEGION_SYS_BASEPATH =
'/sys/module/legion_laptop/drivers/platform:legion/PNP0C09:00'`，只交付 Python 层则包无任何功能。

## 4. 处置（2026-09-20 修订：分层交付 + 分层声明）

**先说结论口径**：内核态功能**不可适配**这一判定不变；变的只是「判定之后怎么做」——
不再关单了事，而是把可交付的部分真实交付、不可交付的部分如实随包交付源码并声明未执行。
可复用的落地模式见配对草稿
`DRAFT-lenovolegionlinux-0.0.20-kernel-module-source-snapshot-delivery.{kv,md}`。

1. **可交付部分真实交付**：用户态层（本例 `python/legion_linux` 的 CLI 与库）作为
   `package_type=application` 制品发布（site-packages + `bin/` 控制台入口 + 桌面集成文件），
   在目标机上可安装、可运行、内核模块缺失时优雅降级；`conan create` 必须真实通过。
2. **不可交付部分随包交付源码 + fail-closed 契约测试**：上游源码快照按原目录布局进入
   `share/<pkg>/upstream/`（含内核模块源码、上游测试脚本），`test_package` 对内核模块源码做
   静态契约校验（缺失源码即非 0 退出），并在 PR/manifest 中**分层声明**内核态构建与加载
   未执行；平台将来提供内核构建树/内核头制品时可直接复用该快照。
3. **绝不伪造**：不得伪造内核头、不得以空壳 stub 让源码「编译通过」、不得交付预编译 `.ko`、
   不得把「源码契约通过」声称为「内核态功能通过」。
4. 若用户态子集**完全不能独立工作**且没有可交付制品（既无 recipe 也无二进制），才退回
   仓库手册的「无法适配」issue 通道（先例 `archives/a/aegisub/3.4.2/notes.md` → issue #2136；
   包目录无 `conanfile.py` 会被 CI 判 `No packages to build` 而失败）。
5. 「不得裁剪」的执行口径：**不得裁剪后宣称适配完成**。交付用户态层时必须同时
   （a）随包交付内核模块源码，（b）在 PR/manifest 中逐项声明未执行的边界，
   （c）补齐 OHOS 侧可执行的消费者/平台契约测试。本例实测：12 个上游用例中 2 个 CLI 用例
   可在 OHOS 侧真实执行（源树变体逐字执行 + 已安装变体经包内 `bin/` 执行），其余 10 个
   逐条给出阻塞证据。

## 5. 未来可重新评估的条件

1. 平台提供 OHOS PC 内核构建树（kernel headers + Kbuild 目标）与模块签名/加载能力；
2. 出现面向 OHOS PC 的内核模块交付通道（当前框架仅覆盖用户态 conan 制品）；
3. 上游提供不依赖该硬件接口的用户态替代实现。
