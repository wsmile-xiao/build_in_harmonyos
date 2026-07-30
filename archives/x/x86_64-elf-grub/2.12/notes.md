# x86_64-elf-grub 2.12 适配笔记

## 概述

GNU GRUB 2.12 被配置为 `x86_64-elf`/`x86_64-efi` 交叉目标。包内
`x86_64-elf-grub-*` 工具运行在 HarmonyOS PC（AArch64）宿主上，生成和检查
x86_64 GRUB/EFI 目标文件，不在宿主上执行 x86_64 代码。

## 构建系统与依赖

- 构建系统：Autotools（发布包自带 `configure`）
- 宿主编译器：Conan profile 的 Clang/Clang++
- 目标编译器：Clang Linux driver 选择已发布的 `x86_64-elf-ld`，cc1 使用
  `x86_64-unknown-unknown-elf` 裸机三元组
- 编译依赖：`x86_64-elf-binutils/2.46.1`
- 并行度：遵从 Conan `tools.build:jobs`，最多 8 线程

目标 `ld`、`objcopy`、`strip`、`nm` 和 `ranlib` 均从 Conan build dependency 的
package folder 构造绝对路径，避免依赖不确定的全局 `PATH`。

### 前置依赖状态

- 前置包：`x86_64-elf-binutils/2.46.1`
- 前置 PR：[build_in_harmonyos #2089](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/2089)
- 前置 Issue：[build_in_harmonyos #190](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/190)
- 合入时间：`2026-07-17 15:25:55 +08:00`
- main 提交：`621f9b4265736c51c3652c137b7b1252253bb030`
- 发布验证：W0 已通过 `conan download` 验证 OHOS/armv8 binary 可下载；本地
  Linux/x86_64 近似验证另行从该正式配方成功构建工具包。

下游 PR 除正文回链外，还必须在 GitCode 合并区的“前置 PR”下拉框实际选择 #2089。

## 关键配置

| 选项 | 作用 |
|------|------|
| `--target=x86_64-elf` | 选择 x86_64 裸机目标 |
| `--with-platform=efi` | 只构建 EFI 平台 |
| `--program-prefix=x86_64-elf-` | 防止与系统 GRUB 命令冲突 |
| `--disable-efiemu` | 裁剪不需要的 EFI 模拟模块 |
| `--disable-grub-mkfont --disable-grub-themes` | 移除字体/主题依赖 |
| `--disable-grub-mount --disable-device-mapper` | 移除 FUSE/device-mapper 依赖 |
| `--disable-liblzma --disable-libzfs` | 移除额外压缩与 ZFS 构建依赖 |
| `TARGET_LDFLAGS=-Wl,-no-pie` | 生成非 PIE 的裸机目标链接结果 |
| `SHELL=/system/bin/sh` | 让 configure、config.status 与 make 规则走系统 POSIX shell |
| `-ffile-prefix-map/-fdebug-prefix-map` | 把源码/构建绝对路径规范化为 `grub-2.12` |

构建前创建空的 `grub-core/extra_deps.lst`，因为生成的依赖片段会引用该可选文件，
而当前包没有额外的树外模块。

## 适配问题与解决方案

| 问题 | 根因 | 解决方案 |
|------|------|----------|
| `config.guess` 无法识别 HarmonyOS | 上游脚本缺少 HarmonyOS/`__OHOS__` 分支 | `0004` 补丁增加平台识别 |
| `config.sub` 拒绝 `linux-ohos` | 上游 2.12 脚本缺少 OHOS OS/内核组合 | `0005` 补丁增加三元组规范化与白名单 |
| HMDFS 上 `configure` 临时文件不可写 | 两处临时目录使用 `umask 077` | `0006` 精确改为 `umask 022`（E129） |
| 生成的 `config.status` 直接执行返回 126 | HMDFS noexec，即使 shebang 指向系统 shell 也不能直接执行 | 同时修改权威生成输入和三份 shipped `Makefile.in`，统一通过 `$(SHELL) config.status` |
| `make` 调用缺失的 `automake-1.15` | 权威 `.am`/生成器补丁晚于 shipped `Makefile.in`，时间戳触发重生成 | 按 E041 将 `gentpl.py` 先于其生成的 `.am` 应用，并把三个 `.in` 补丁放到补丁链末尾 |
| x86_64-elf Clang driver 回退不存在的 GCC | HNP Clang 没有裸机 driver 对应的默认 linker | driver 用 Linux 三元组选择 GNU ld，cc1 用 `-Xclang -triple` 恢复裸机语义 |
| `grub-file` 报 `can't open '/': Permission denied` | 受限进程可搜索已知路径但不可枚举 `/`，hostfs 把身份探测 `EACCES` 当成坏文件名 | `0010` 仅在 `path == "/"` 且 `errno == EACCES` 时继续，按运行时能力而非平台宏判断（E226） |
| 目标链接产生 PIE 相关错误 | 裸机目标不能使用宿主 PIE 默认值 | make/check 时覆盖 `TARGET_LDFLAGS=-Wl,-no-pie` |
| `make install` 查找不存在的 man page | `HELP2MAN=true` 不生成文档，但安装目标仍包含 `man_MANS` | 安装时显式传入 `man_MANS=`（E217） |
| 包含 GDB 中间件和缓存绝对路径 | `.module`、调试信息、`__FILE__` 与 `modinfo.sh` 保留构建路径 | 删除 GDB-only `.module`，编译期 prefix-map，并在安装后规范化 `modinfo.sh` |

E217 的复现日志 `linux-install.log`（SHA-256
`7f10b0fd016e7aeffabc127eb15f1cd00ebe805d44da044604310ed1dc1ac65c`）以
`install: cannot stat '.../grub-mkimage.1': No such file or directory` 失败；追加
`man_MANS=` 后，`linux-install-no-man.log`（SHA-256
`7b4319d14b658c53df5eb98abf2c1644b906da383b94bd9a1943af9d2482cb6e`）完整走完安装。
不得仅设置 `HELP2MAN=true` 后假定文档已禁用，也不得伪造空手册页或忽略安装失败。

## 路径 C 高难度说明

本适配满足“私有工具链/复杂架构”和“全量测试校验成本极高”两项高难条件；不以
Linux 私有接口这一项单独申报，因为 GRUB 上游已有 `grub-core/osdep/` 分层。

1. **双层私有工具链**：宿主命令由 OHOS/AArch64 Clang 构建，目标代码则由 Clang
   Linux driver 选择 GNU `x86_64-elf-ld`，再以 `-Xclang -triple` 把 cc1 恢复为
   `x86_64-unknown-unknown-elf` 裸机语义，并由 `x86_64-elf-binutils` 完成对象处理。
   GRUB 没有可直接映射到普通 Conan CMake toolchain 的单层跨平台抽象；配方必须
   分别设置 `CC/CXX/BUILD_CC` 与 `TARGET_CC/TARGET_{OBJCOPY,STRIP,NM,RANLIB}`。
   目标工具来源于前置 PR #2089 的 Conan package folder，不能依赖系统同名命令。
2. **汇编与特殊二进制架构**：上游树含 174 个 `.S/.s` 文件；当前目标入口包括
   `grub-core/kern/x86_64/efi/startup.S`，并使用非 PIE、freestanding、无标准库的
   链接模型。构建过程产生 268 个带 GDB 符号的 `.module` 中间件；最终包将其移除，
   保留 268 个运行时 `.mod`，全包共 322 个文件，不是普通单库产物。
3. **系统接口面**：`grub-core/osdep/` 含 78 个 C/H/汇编源文件，覆盖 host disk、
   设备探测、Unix/Linux 路径等平台逻辑。本适配通过
   `--disable-grub-mount --disable-device-mapper` 裁剪 FUSE/device-mapper 壁垒，
   但保留生成镜像所需的宿主工具能力。
4. **依赖拓扑**：`x86_64-elf-grub/2.12` 直接 tool-require
   `x86_64-elf-binutils/2.46.1`；后者提供 GNU ld/objcopy/strip/nm/ranlib，目标编译
   同时依赖 Clang 15 前端。任何一层缺失都会在 configure 探测或模块链接阶段失败。
5. **测试规模与成本**：可复核库存为单元 5、集成 81、其他 6，合计 92。
   完整集成测试依赖 QEMU、文件系统工具和目标运行时；探索性执行只有 8 PASS、
   4 SKIP、45 FAIL、25 ERROR。当前可复跑通过证据为 4 个上游 C 单测加 6 个
   消费者流程，共 10 个独立通过用例；该数字不把未执行库存或断言拆分计数。
   GRUB 是当前普通下游任务，不是本轮首次适配的底层依赖库，因此依赖库的
   `0.5`/`1` 分附加口径不适用于本 PR。

## 上游测试证据

上游源码静态清点得到 92 个测试入口：

| 类型 | 流程数 | 来源 |
|------|-------:|------|
| 单元测试 | 5 | `Makefile.am` 的 5 个 `*_unit_test` C 程序 |
| 集成测试 | 81 | `tests/*.in` 与 `tests/*.sh` 驱动的 GRUB/QEMU/文件系统测试 |
| 其他测试 | 6 | `asm-tests/*.S` 的架构汇编检查 |
| 合计 | 92 | 不等同于 92 个已通过测试 |

在 Linux/Clang 15 定向执行的 4 个自包含 C 单测全部通过：

- `example_unit_test`
- `printf_test`
- `date_test`
- `cmp_test`

`priority_queue_unit_test` 与 GRUB 2.12 内置 gnulib 的 `free()` 异常规范在 Clang 15
下冲突，未编译通过。完整测试套件还需要 QEMU、文件系统工具和目标运行时；探索性
全套运行得到 8 PASS、4 SKIP、45 FAIL、25 ERROR，因此不得宣称 92/92 通过。

正式配方在每次构建后执行以下非空上游子集：

```bash
make check \
  'check_PROGRAMS=example_unit_test printf_test date_test cmp_test' \
  'check_SCRIPTS=' \
  'TESTS=example_unit_test printf_test date_test cmp_test' \
  'TARGET_LDFLAGS=-Wl,-no-pie'
```

## test_package

消费者测试包含 6 个互不重复的测试流程和 10 条语义断言：

| 类型 | 流程数 | 断言数 | 覆盖范围 |
|------|-------:|-------:|----------|
| 单元测试 | 0 | 0 | 无直接调用库内函数的单元测试；消费者均执行包内 CLI |
| 集成测试 | 6 | 10 | Multiboot 正/负识别、配置校验、EFI 生成/识别、版本执行、environment block 往返 |
| 鸿蒙特有测试 | 0 | 0 | 无仅在 OHOS 成立的平台专属断言；现有流程均可跨 Linux/OHOS 运行 |
| 合计 | 6 | 10 | 流程数与断言数分开统计 |

`test_package` 真实调用包内 `x86_64-elf-grub-*` 命令；移走包内 `bin/`/`sbin/`
后测试会失败，满足 R34/L1e 的破坏性反向验证要求。

## Linux 近似预检边界

Ubuntu-D 上的定向构建、安装、4 个上游 C 单测、Multiboot 识别和 EFI 生成均已
通过；安装包含 551 个 `lib/grub/x86_64-efi` 平台文件，生成的 EFI 镜像为
450560 字节。该结果是 Linux/x86_64 近似预检，不代表 HarmonyOS/AArch64 正式 CI。

### Linux 强制源码构建证据

该阶段近似预检通过以下命令强制从源码重建主包；`x86_64-elf-binutils/2.46.1`
使用 Linux/x86_64 本地缓存中的构建依赖包：

```bash
conan create \
  /mnt/e/HarmonyPC/contest-worktrees/x86_64-elf-grub-2.12/archives/x/x86_64-elf-grub/2.12 \
  --profile:host /mnt/e/HarmonyPC/validation/x86_64-elf-grub-2.12/linux-x86_64.profile \
  --profile:build /mnt/e/HarmonyPC/validation/x86_64-elf-grub-2.12/linux-x86_64.profile \
  --build=missing \
  --build='x86_64-elf-grub/*'
```

- 日志：`E:/HarmonyPC/validation/x86_64-elf-grub-2.12/conan-create-linux-forced.log`
- 日志 SHA-256：`0795adc153e041eb393451c82c4e53dab8d2a49c9fb8c403d36597bcf3eb2558`
- recipe revision：`2adec5ea79265187dfdc3723c8041b22`
- package ID：`3d4342fdf09e3869a011f21a8baf7909388f5878`
- package revision：`55f96f9c9e03f3dfd811ce5054213b07`
- 完整包引用：`x86_64-elf-grub/2.12#2adec5ea79265187dfdc3723c8041b22:3d4342fdf09e3869a011f21a8baf7909388f5878#55f96f9c9e03f3dfd811ce5054213b07`
- 同一日志依次记录 `Forced build from source`、上游测试 `4/4`、主包创建和
  `test_package` 的 `6/6` 流程（10/10 断言）。日志以消费者测试 PASS 正常结束。
- 驱动脚本用 `${PIPESTATUS[0]}` 返回 `conan create` 状态，但数值退出码没有写入
  日志文件；因此此处不把日志自身表述为“记录了 exit 0”。

最终消费者脚本需要 `set -o pipefail`。Linux 以 `CONFIG_SHELL=/bin/sh` 启动时，
探测逻辑会跳过不支持 pipefail 的 dash，选择 `/usr/bin/bash`；6/6 流程和 10/10
断言通过。日志 `conan-test-linux-dash-final.log` 的 SHA-256 为
`3361b00436a0451c4eff677a205f2f11bdf46e7705fa035ce8d28409163a4a55`。

## HarmonyOS PC 真机最终验证

最终验证在 HarmonyOS PC AArch64 真机上通过 SSH 隧道执行，目录为
`grub-review-r8-device18`，使用全新 Conan home。归档包含 22 个受版本控制输入和
2 个验证脚本，其中 19 个 CI 配方/测试输入及 1 个共享 OHOS profile 与当前 HEAD
逐字一致；`manifest.yaml` 和 `notes.md` 在验证结束后补录本节结果。归档 SHA-256 为
`59e5b9362cc8325ccd95e03e11c9c69b233caf15afbf57a1e0885ea28801fd8f`；远端流文件
SHA-256 完全一致，解包后文件数为 24。W0 从 `ohpcd` 下载并解压
`x86_64-elf-binutils/2.46.1` 的正式 OHOS/armv8 binary；主包随后从干净源码构建，
并在同一次 `conan create` 中直接执行最终分类的消费者脚本。

- recipe revision：`5887b1b64653291906dff4b4fa6358b1`
- package ID：`6b129b068851896169fae42d399fa922d239ce8a`
- package revision：`27aeedd727c8a6348bf154c127f9d874`
- 完整包引用：`x86_64-elf-grub/2.12#5887b1b64653291906dff4b4fa6358b1:6b129b068851896169fae42d399fa922d239ce8a#27aeedd727c8a6348bf154c127f9d874`
- `conan create` 完整结束；上游 C 单测 `4/4`，`FAIL=0`、`ERROR=0`
- `test_package`：`6/6` 流程、`10/10` 语义断言通过
- 构建与全包审计日志：`E:/HarmonyPC/validation/x86_64-elf-grub-2.12/device-conan-create-review-r8-device18.log`
- 构建与全包审计日志 SHA-256：`ae7432e5f00b3a7348d98c6f1d38d163f5955e2e47966f05a732d9eb6893eb4f`

独立产物审计绑定上述 package revision，结果为：

- 21 个宿主 ELF 全为 AArch64；代表性宿主命令 `x86_64-elf-grub-mkimage` 无
  RPATH/RUNPATH。
- 268 个最终 `.mod` 全为 x86-64；GDB-only `.module` 数量为 0。
- `kernel.exec` 无 NEEDED/RPATH/RUNPATH/INTERP，目标目录无宿主 startup object、
  libc loader 或 Conan/cache 绝对路径。
- 生成的 EFI 为 PE32+ x86-64；全包 322 个文件。
- 322 文件清单 SHA-256：`891bc821af48dea24ab831e16b5df5136483a8a974c04cf5c984438f93a7761b`
- `AUDIT_FAILURES=0`。

device15 曾在同一最终源码内容下因补丁声明顺序失败：`make` 发现权威输入比
shipped `Makefile.in` 新，尝试调用设备上不存在的 `automake-1.15`，返回 127。
失败日志 `device-conan-create-final-device15.log` 的 SHA-256 为
`8aa3992668e705532fb0e49456aaaaeb0508fad0292ec0c9736871167ec97562`。
device16 起通过调整补丁应用顺序越过该重生成规则。Review r8 随后只把 `0010`
从 `__OHOS__` 编译期守卫改为严格的 `path == "/" && errno == EACCES` 运行时条件；
HarmonyOS 真机 `refresh-patch --auto` 重新生成 12 个补丁，其中 11 个 SHA-256 不变，
新 `0010` SHA-256 为
`28f279c4d9163c167b598c1928d7f29dc107da9313039e9b48f391df143d5fe6`。最终补丁链
通过 `git apply --check` 和 GNU `patch --fuzz=0`，重放后的 `hostfs.c` SHA-256
`c51a6b19b6ee9d6ed8b98e1ae806c2400994d748e1b8afbd3b7ff4e5ce942e7f` 与跟踪
`.work` 完全一致；device18 的 Conan patch-ng 也完整应用 12 个补丁。

真机验证不替代当前 PR HEAD 的正式 CI；提交后仍必须绑定 CI 的完整 revision，
并在 CI 成功后重新触发 AI Review。

### 云端知识缺口复核

已对 `origin/main` 提交 `8c5703f967b606bc454831e265005d440d26dce5` 复核。
云端已覆盖部分通用问题：E007 覆盖 `config.guess/config.sub` 的
HarmonyOS 三元组识别，E011/E129 覆盖 HMDFS 上 `umask 077` 临时目录权限问题，
E041 覆盖源码时间戳晚于 shipped `Makefile.in` 时触发 Automake 重生成；
测试驱动需避免不可移植的绝对解释器路径也已有 E049 和仓库内多份可复用配方模式。
但云端没有等价条目说明 `HELP2MAN=true` 只替换生成器、不会清空 Automake 的
`man_MANS` 安装清单，也没有覆盖“应用域可搜索但不可枚举 `/`，hostfs 身份探测
把 `EACCES` 误判为目标文件无效”的模式。本 PR 因此随软件提交：

- E217 知识草稿：`HELP2MAN=true` 与 Automake `man_MANS` 的生成/安装语义分离。
- E226 知识草稿：仅对受限运行域的根目录身份探测做严格 `EACCES` 降级，保留实际文件校验；该方案按运行时失败条件判断，不依赖平台宏。

两项都包含症状、根因、修复边界、禁止做法和可复核日志，因此适配路径追加路径 B。
编译器 driver/cc1 三元组拆分、prefix-map、GDB 中间件清理和 Clang 15 单测豁免
保留为本配方/版本的 L3 记录；云端 Tcl 配方已有生成配置路径重定位的相近模式，
不重复创建仅描述绝对路径替换的知识条目。
