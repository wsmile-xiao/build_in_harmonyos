# vgabios 0.8a 适配笔记（LGPL'd VGABIOS）

## 项目信息

- **软件名称**: VGABIOS（LGPL'd VGA BIOS，Bochs / QEMU / plex86 的显卡固件）
- **版本**: 0.8a（版本证据：上游 tag `v0_8a`，README "History" 首行
  `vgabios-0.8a : Jun 03 2021`）
- **上游仓库**: https://github.com/bochs-emu/VGABIOS
- **源码归档**: `https://github.com/bochs-emu/VGABIOS/archive/refs/tags/v0_8a.tar.gz`
- **SHA256**: `4e1e1d5a41225a1b842f1afaa030c058420fba4b377bdd35e623e57bd0cd4835`
- **许可证**: LGPL-2.0-or-later
- **构建系统**: GNU make（无 configure）
- **产物类型**: 8086 实模式 Option ROM 固件镜像 + `biossums` 镜像工具

## 编译环境

- **目标平台**: HarmonyOS PC aarch64（`uname -s` = HarmonyOS，HongMeng Kernel 1.12.0）
- **编译器**: clang 15.0.4（`/data/service/hnp/bin/clang`，目标 `aarch64-unknown-linux-ohos`）
- **8086 工具链**: dev86/0.16.21（`bcc` / `as86`，OHOS aarch64 原生）
- **Conan Profile**: `ci/conan/profiles/ohos-aarch64`（os=OHOS, arch=armv8, clang 15, libc++）

## 依赖

`conanfile.py` 只有**一个**构建期依赖：

| 类型 | 依赖 | 说明 |
|------|------|------|
| tool_requires | `dev86/0.16.21` | 提供 OHOS aarch64 原生的 `bcc`（8086 C 编译器）与 `as86`（8086 汇编器），以及 `bcc` 运行期组件 `lib/bcc/{bcc-cpp,bcc-cc1,include}` |

**W0 依赖发布检查（R36 + R35）**

```bash
$ bash ci/scripts/preflight_check.sh vgabios/0.8a --deps "dev86/0.16.21"
[OK] 已发布: dev86/0.16.21
[OK] 版本号未被占用: vgabios/0.8a
[OK] 所有依赖均已发布到制品仓，可以安全开始适配 vgabios/0.8a
# 退出码 0
```

```bash
$ conan download dev86/0.16.21 -r=ohpcd
dev86/0.16.21: Retrieving package 6b129b068851896169fae42d399fa922d239ce8a from remote 'ohpcd'
dev86/0.16.21: Package installed 6b129b068851896169fae42d399fa922d239ce8a
# 退出码 0
# 二进制 settings: arch=armv8 compiler=clang compiler.version=15 os=OHOS libc++
```

结论：dev86/0.16.21 已发布且可消费（未使用本地缓存或 `--build=missing` 绕过）。
无其它强制第三方依赖；`dev86` 的 8086 成员库（libc 等）本次未纳入（与 dev86 适配
边界一致）。

## 构建过程

上游 Makefile 的构建规则（`Makefile:66-74`）：

```make
%.bin:
	$(GCC) -E -P vgabios.c $(VGABIOS_VERS) $(VGAFLAGS) $(VGABIOS_DATE) > _$*_.c   # 宿主预处理
	$(BCC) -o $*.s -C-c -D__i86__ -S -0 _$*_.c                                   # 8086 编译
	sed -e 's/^\.text//' -e 's/^\.data//' $*.s > _$*_.s
	$(AS86) _$*_.s -b $*.bin -u -w- -g -0 -j -O -l $*.txt                        # 8086 汇编
	mv $*.bin $(DISTNAME)
	./biossums $(DISTNAME)                                                       # 补校验页+写校验和
```

`make all` 依次构建 5 个 ROM（`bios` / `cirrus-bios` / `banshee-bios`）。

### 依赖注入（OHOS 相关）

| 注入项 | 值 | 原因 |
|--------|----|------|
| `CC` / `GCC` | `tools.build:compiler_executables.c`（clang） | 宿主工具（biossums / vbetables-gen）与 `-E -P` 预处理 |
| `BCC` | `<dev86>/bin/bcc` | 8086 C 编译器 |
| `AS86` | `<dev86>/bin/as86` | 8086 汇编器 |
| `BCC_PREFIX` | dev86 包目录 | `bcc` 依此定位 `lib/bcc/{bcc-cpp,bcc-cc1,include}`；缺省时报 `Unable to execute bcc-cpp.` |
| `TMPDIR` | `<build_folder>/tmp` | **HMDFS 的 `/tmp` 只读**，`bcc` 需在可写目录落中间文件（dev86 已打补丁令其遵循 `TMPDIR`） |

**无源码补丁**：上游 Makefile 的 `CC/GCC/BCC/AS86` 均为简单赋值，命令行覆盖即可
接入 Conan 工具链（R1：参数最少化），因此 `patches/` 为空。

### 首个真实错误（E1）——`tools.build:compiler_executables:c` 不是合法 conf

```
ERROR: vgabios/0.8a: Error in build() method, line 94
    cc = self.conf.get("tools.build:compiler_executables:c", "clang", check_type=str)
    ConanException: [conf] 'tools.build:compiler_executables:c' does not exist in
    configuration list.
```

- **根因**：`tools.build:compiler_executables` 是 **JSON dict 型 conf**
  （`{"c": "...", "cpp": "..."}`），不支持 `:c` 下标访问；模板注释里的 `:c` 写法
  仅对 scalar conf 成立。
- **修复**：改为
  `compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)`
  后 `cc = compilers.get("c", "clang")`（与仓库既有 1934 处用法一致）。
- **重新验证**：`conan create` 进入 `Calling build()`（退出码 0 到该步）。

### 第二个真实错误（E2）——`ConanFile.run(env=...)` 不接受 dict/`VAR=VALUE`

```
ERROR: vgabios/0.8a: Error in build() method, line 116
    self.run(...)
    AssertionError: env argument to ConanFile.run() should be a list
```

- **根因**：`ConanFile.run(env=)` 的 `env` 参数语义是「**环境文件名/环境名**的列表」
  （`conan/internal/model/conan_file.py:367` 起），最终交给
  `command_env_wrapper()`（`conan/internal/subsystems.py`）拼成
  `. "<envfile>.sh" && <cmd>`；传 dict 或 `"VAR=VALUE"` 列表都不成立
  （后者会被当成不存在的 env 文件）。
- **修复**：改用 `conan.tools.env.Environment` + `env.vars(self, scope="build").apply()`
  上下文注入变量（`Environment` 本身没有 `apply()`，必须 `.vars()` 取 `EnvVars`）。
  该形态与仓库既有 1187 处 `.apply()` 用法一致（参考
  `archives/a/abiword-plugin-openwriter/3.0.8/conanfile.py:175` 对同一坑的批注）。
- **重新验证**：变量成功注入（`env` 输出含 `BCC_PREFIX` / `TMPDIR`），构建进入 make。

### 第三个真实错误（E3）——conan 子进程继承 socket 型 stdin 导致 SDK clang 静默 exit 1

```
vgabios/0.8a: RUN: make -j1 CC=/data/service/hnp/bin/clang GCC=… BCC=… AS86=…
/data/service/hnp/bin/clang -o vbetables-gen vbetables-gen.c
make: *** [Makefile:85: vbetables-gen] Error 1
ConanException: Error 2 while executing
```

注意：make 只回显了被调用的编译命令，**没有任何编译器诊断**。

**定位过程（真实探针命令与结果）**

| 探针（均在 conan `self.run` 内执行，另附交互 shell 对照） | conan 内 | 交互 shell |
|------|:--------:|:----------:|
| `clang --version` | ❌ rc=1（零输出） | ✅ rc=0（10/10 次） |
| `<sdk>/llvm/bin/clang-15 --version`（真二进制，109 MB） | ❌ rc=1 | ✅ rc=0 |
| `/data/service/hnp/bin/bash -c '…clang-15 --version'` | ❌ rc=1 | ✅ rc=0 |
| `/storage/…/usr/local/bin/python3 --version`（非 SDK 路径） | ✅ rc=0 | ✅ rc=0 |
| `cat /proc/self/limits` | ✅ 地址空间/进程数/文件数全 unlimited | 同 |
| `/data/service/hnp/bin/bash`（HNP 挂载上的二进制） | ✅ rc=0 | ✅ rc=0 |
| 把 conan 子进程的 **完整 84 项环境变量** 注入交互 shell 后执行 clang-15 | — | ✅ rc=0 |
| **`"$L" --version </dev/null`（仅把 clang 自己的 stdin 指向 /dev/null）** | ✅ **rc=0，打印版本** | ✅ rc=0 |
| 复现 `. "<conanbuild.sh>" && make …`（交互 shell，同一 conan 缓存目录） | — | ✅ 5 个 ROM 全部产出 |

- **根因**：conan 的 `ConanFile.run()` → `conan_run()` 使用
  `subprocess.Popen(command, shell=True, cwd=cwd)`，**未指定 `stdin=`**，
  子进程继承了 OpenDesk 会话的 **socket 型 stdin**；链路上的
  `/data/service/hnp/**/llvm/bin/clang`（180 字节 `#!/bin/sh` 包装脚本 → `clang-15`）
  在该继承关系下启动后**静默 `exit 1`**（不打印版本、不打印诊断），
  make 将其归一为 `Error 1`，外观酷似「源码/配方编译错误」。
  已逐项排除：环境变量、rlimit、LD_LIBRARY_PATH、shell 种类（bash/sh/zsh）、
  `env=None`（不走 conanbuild 包装）、cwd、HNP 挂载本身（`/data/service/hnp/bin/bash` 正常）。
- **修复（调用侧，不改配方）**：把 **conan 进程自身**的 stdin 重定向为 `/dev/null`：

  ```bash
  conan create archives/v/vgabios/0.8a -pr:h=… -pr:b=… --build=missing --build="vgabios/*" < /dev/null
  python3 scripts/ohc-run.py conan-verify vgabios 0.8a < /dev/null
  python3 scripts/ohc-run.py finish      vgabios 0.8a built < /dev/null
  ```

  只把 **make 命令**重定向无效（已实测），必须重定向 conan 进程自身。
- **重新验证**：`conan create` 退出码 0；5 个 ROM 全部产出
  （`Bios checksum at 0x95FF / 0x99FF / 0x81FF / 0x81FF / 0x7FFF`），
  `Package '6b129b068851896169fae42d399fa922d239ce8a' created`，
  test_package 9/9 PASS。日志：`reports/conan-create.log`。
- 已沉淀为知识草稿 `knowledge/drafts/E545-draft-VG08.{kv,md}`。

### 第四个真实错误（E4）——W3 本地 CI 模拟：zsh heredoc 临时文件 + 全仓 junk 全量扫描

```
[fail] L0i: conanfile.py AST 解析失败, 无法提取依赖:
       ci/conan/build_and_test.sh:439: can't create temp file for here document: read-only file system
```

- **根因 A（临时文件）**：`ci/conan/build_and_test.sh` 的 shebang 是 `#!/usr/bin/zsh`。
  zsh 的 here-document 落临时文件，前缀取 `TMPPREFIX`（默认 `/tmp/zsh`），
  **不读 `TMPDIR`**；OHOS 的 `/tmp` 只读 → heredoc 全线失败，
  门禁把真实结论替换成误导性的「AST 解析失败/可能是 BOM」。
- **修复 A**：`export TMPPREFIX=$HOME/tmp/zsh`（同时 `TMPDIR=$HOME/tmp`）后再跑 W3。
  验证：`TMPPREFIX=… zsh -c 'read -r l <<EOF …'` 返回 `got=…`、rc=0。
- **根因 B（junk 门禁）**：`ci/scripts/junk_check.sh` 在
  `git diff origin/main...HEAD` 为空（分支尚无 commit）时回退 **full 模式**，
  扫描**整仓 107607 个跟踪文件**，命中 5 个属于**其它软件**的历史遗留运行时状态文件
  （`archives/c/cloog/0.21.1/.build-closed`、`kics/.staging-verified`、
  `libbfio/.staging-verified`、`thc/.staging-verified`），与本包无关。
- **处置 B**：按 junk_check 的 PR 模式（`JUNK_PR_DIFF`，CI 上由 buildbot 传 pr.diff
  的同一入口）把检查范围限定为本次变更文件清单，等价于 CI 的 PR 校验口径；
  **未提交任何 commit**（按任务要求在 commit/push/PR 前停下等待确认）。
- **重新验证（W3）**：`✅ W3 本地 CI 模拟通过`（`reports/w3-local-ci.log`），
  finish 10 步走完，`status: built`。
- 已沉淀为知识草稿 `knowledge/drafts/E546-draft-VG08.{kv,md}`。

## 上游测试清点（R51 三步法）

### 1. 清点

| 检查项 | 命令 | 结果 |
|--------|------|------|
| 顶层 Makefile 测试目标 | `grep -nE '^(check\|test\|tests)\s*:' Makefile` | 无 |
| 上游测试目录 | `ls tests/` | `testbios.c`、`lfbprof/{Makefile,lfbprof.c,lfbprof.h}` |
| ctest / meson / pytest | 全树检索 | 无 |
| README 声明的测试 | README "Testing" 节 | 指向 `testvga.c`（**0.8a 归档中不存在此文件**） |

### 2. 实际执行

`make check` / `make test` 在上游 Makefile 中**不存在**（Makefile 仅
`all/bios/cirrus-bios/banshee-bios/clean/dist-clean/release` 与
`biossums/vbetables-gen/vbetables.h` 规则）——即**上游无自动化测试入口**。

对 `tests/` 下两个样例程序的实测（用本适配的 8086 工具链）：

```
$ bcc -S tests/testbios.c -o /dev/null
tests/testbios.c:10: error: Cannot open include file        # #include <dos.h>
# 退出码 1
```

```
$ cat tests/lfbprof/Makefile
lfbprof.exe: lfbprof.c lfbprof.h
    wcl386 -zq -s -d2 lfbprof.c                             # Watcom C++ 10.0a + DOS4GW
```

- `tests/testbios.c` 是 **Turbo C 2.0 DOS 程序**（`<dos.h>`/`<conio.h>`/`intr()`/`REGPACK`）。
- `tests/lfbprof` 是 **Watcom C++ 10.0a + DOS4GW** 程序（`wcl386`）。
- 二者都需 DOS 实模式运行期，且依赖上游未提供的商业编译器头文件，
  **在 OHOS 上既不能编译也不能运行**。

### 3. 结论

**上游 0.8a 无自动化测试入口，上游用例总数 = 0**。上游样例（`testbios.c` /
`lfbprof`）为 DOS 交互式程序，不具备在本平台执行的条件，已逐一实测取证。
消费者侧验证由 `test_package/` 提供（**不计入上游测试统计**）。

## 消费者侧测试（test_package）

`test_package/test_vgabios.sh` + `verify_rom.py`，9 项用例（含 1 项鸿蒙特有），
逐字节校验 5 个 ROM 的 Option ROM 签名 / 校验和 / 长度字段 / PCIR 结构 / 变体标记，
并实际运行包内 `bin/biossums` 修复被破坏的 ROM。结果见 `reports/test-report.md`。

## 已知事项

- 上游归档内含 2021 年发布时预编译的 `VGABIOS-lgpl-latest*.bin`。配方在构建前
  **先移除**这些文件，确保打包的一定是本次真构建产物；构建若产出不全则显式报错。
- 新构建 ROM 与归档内预编译 ROM **不是逐字节相同**（`VGABIOS_DATE` 嵌入构建日期、
  版本串为 `current-svn`），因此验证采用结构断言而非二进制比对。
- `biossums` 的语义：对缺少校验页的 as86 原始输出**追加 512 字节校验页**并写
  `data[2]` 与 PCIR `ImageLength`；对已定稿 ROM 的载荷改动会再追加一页
  （38400 → 38912）后重算校验和 —— 该行为已固化为 TC-08 的期望值。
- 本包在软件级目录声明了 `commands.json`（R38：产出可执行文件 `bin/biossums`），
  与版本目录 `conanfile.py`（`cpp_info.bindirs = ["bin"]`）同提交落地。

---

## 本地门禁结果汇总

| 门禁 | 命令 | 结果 |
|------|------|:----:|
| W0 依赖预检 | `bash ci/scripts/preflight_check.sh vgabios/0.8a --deps "dev86/0.16.21"` | ✅ 退出码 0 |
| R35 依赖可消费 | `conan download dev86/0.16.21 -r=ohpcd` | ✅ 退出码 0 |
| R47 语言预检 | `python3 scripts/ohc-run.py lang-preflight vgabios 0.8a --src <src>` | ✅ `detected=c, expected=cpp`（兼容族） |
| conan create | `conan create archives/v/vgabios/0.8a -pr:h=… -pr:b=… --build=missing --build="vgabios/*" < /dev/null` | ✅ 退出码 0 |
| conan-verify | `python3 scripts/ohc-run.py conan-verify vgabios 0.8a < /dev/null` | ✅ G0–G4 + L2/L4/L5 PASS |
| finish（含 W2/W3） | `python3 scripts/ohc-run.py finish vgabios 0.8a built < /dev/null` | ✅ `status: built`，W3 通过 |
| 上游测试入口 | 见 `reports/upstream-check.log` | ✅ 已核验（无自动化测试） |
| 消费者测试 | `bash test_package/test_vgabios.sh <pkg>` | ✅ 9/9 PASS（含 1 项鸿蒙特有） |

**适配结束**: 2026-09-30
**最终状态**: `built`（本地门禁全通过；按任务要求停在 commit/push/PR 之前等待确认）
---

**编译结束**: 2026-09-30 13:12
**最终状态**: built
