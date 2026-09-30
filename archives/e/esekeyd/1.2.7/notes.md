# esekeyd 1.2.7 适配笔记

## 概述

- 软件: esekeyd — ESE Key Daemon，多媒体键盘守护进程（/dev/input 事件 → shell 命令）
- 上游: https://github.com/burghardt/esekeyd（官方发布渠道为 SourceForge；
  本包源码采用 Debian/Ubuntu pool 的 orig tarball，与上游发布同源）
- 版本: 1.2.7（上游最后一版，2010 年，SVN-r63）
- 许可: GPL-2.0-or-later
- 构建系统: autotools（automake 1.10.1 预生成的 configure + Makefile.in）
- 产物: `esekeyd`（上游 sbin 守护进程）、`keytest`、`learnkeys`（bin 工具），
  以及 noinst 构建辅助 `mkparser`
- 目标平台: OpenHarmony / HarmonyOS PC (aarch64-linux-ohos)

## 时间/状态

- 适配日期: 2026-09-29
- 状态: **built**（真机 shadow CI r5 通过：conan create + test_package 14/14，exit 0）
- 分支: `feat/esekeyd-1.2.7-codex`
- worktree: `D:\harmonyos\worktrees\esekeyd`

## W0 依赖结论

```text
依赖数量：0（仅依赖 libc；无第三方依赖）
已满足依赖：musl libc（pthread mutex 为 musl 内置）、
  内核 UAPI 头 linux/input.h（OHOS sysroot 自带，已核实
  DevEco openharmony sysroot 存在 usr/include/linux/input.h）
缺失依赖：无
是否需要拆分依赖适配：否
阻塞点：无
下一步：本机前置验证 → 真机 shadow CI（单包排队）
```

制品仓 `esekeyd` 不存在（本仓 archives 无记录），属首次适配，
Conan 包版本 = 上游版本 = `1.2.7`，无需 R37 递增。

## 源码归档选择

- URL: `http://archive.ubuntu.com/ubuntu/pool/universe/e/esekeyd/esekeyd_1.2.7.orig.tar.gz`
- SHA256: `58bdac994be805d9c11b21065427c8f53684d38a1b44bb02b175fc4ee594cc56`（本机核验）
- URL 以 `.tar.gz` 结尾，Conan 选 gzip 解压器（E392）。
- tarball 完整：预生成 configure/Makefile.in、**含预生成 src/parser.c**。
- 官方 GitHub 仓库 (burghardt/esekeyd) 与 SourceForge 为镜像渠道；
  Ubuntu orig tarball 内容即上游发布包，且 URL 稳定可复现。

## W1 源码与构建系统分析

源码规模：`esekeyd.c`(338) + `input.c`(76) + `parser.c`(750, 自动生成) +
`keytest.c`(126) + `learnkeys.c`(166) + `mkparser.c`(70) + `esekey.h`。

| 观察点 | 结论 |
|---|---|
| 语言 | 纯 C，`_GNU_SOURCE` |
| 构建入口 | 预生成 `./configure`（automake 1.10.1，无 AC_CANONICAL_HOST） |
| 系统调用 | fopen/fread（事件设备）、syslog、fork、system、setitimer、pthread_mutex、getline/asprintf（musl 均有） |
| linux/input.h | esekey.h 无条件包含；struct input_event 读写；OHOS sysroot 有该 UAPI 头 |
| 运行时设备 | /dev/input/event*、/proc/bus/input/{handlers,devices}（仅自动探测用，可显式传设备路径绕开） |
| 测试 | **上游无任何自动化测试**（无 tests/ 目录；automake check 目标为空实现） |

### 上游测试清点（R51）

- `Makefile` 目标含 `check: check-am`，但 `check-am` 依赖 `all-am` 且无任何
  测试程序注册 —— 空实现。
- 源码归档无 `tests/`、`t/`、`test*` 目录。
- **上游可运行测试数 = 0**。本包以 test_package 消费者断言为验证主体。

### 构建系统踩坑（2 处，均由补丁 0001 解决）

1. **parser.c 生成规则不可移植**：
   `parser.c: mkparser /usr/include/linux/input.h` 要求构建机存在
   `/usr/include/linux/input.h`，且时间戳敏感 —— 任何现代内核头都比
   2010 年的 tarball 新，make 每次都会尝试运行 host 工具 mkparser 重建。
   tarball 已含预生成 parser.c（键名映射表），直接移除该规则。
2. **mkparser 自定义规则破坏 VPATH**：
   `$(CC_FOR_BUILD) -o $@ $(mkparser_SOURCES)` 中 `$(mkparser_SOURCES)`
   不会被 VPATH 解析（只有 make 自动变量会），out-of-source 构建下
   编译器找不到 mkparser.c。改为 `$<`。

另注意 `clean-local` 会 `rm -f parser.c`，即 `make clean` 后无法原地重建
（上游本就要求内核头才可重建）；CI 流程不 clean，不受影响。

### 有利条件

- configure.ac 无 `AC_CANONICAL_HOST` → 不使用 config.guess/config.sub，
  **E007（无法识别 HarmonyOS）不适用**，无需平台三元组补丁。
- configure 只做编译/链接型探测（AC_CHECK_HEADERS/FUNCS），不执行 conftest，
  E064（执行弹窗）不适用。
- 仅 musl libc + 内核 UAPI 头，无第三方依赖、无 libtool。

## W2 配方设计

- `package_type = "application"`，settings 全四项；validate 限 Linux/OHOS。
- `source()`：`get(**conan_data["sources"], strip_root=True, verify=True)`。
- `generate()`：`AutotoolsToolchain`，追加 `--sbindir=<pkg>/bin`
  （上游把 esekeyd 装 sbin，统一收进 bin 方便消费）。
- `build()`：`os.umask(0o022)`（HMDFS 规避，同 rsyslog）→
  `apply_conandata_patches` → `autotools.configure()` → `autotools.make(["-j1"])`。
- `package()`：`autotools.install()` + COPYING → licenses/ + 三个二进制 chmod 755。
- `package_info()`：`cpp_info.bindirs = ["bin"]`，无库信息。
- pthread：musl 内置（符号在 libc），无需 -lpthread/-pthread。

## W3 test_package

- `test_package/conanfile.py`：`test_type="explicit"`、`VirtualRunEnv`，
  经 `bash test.sh` 调用已安装二进制（OHOS /system/bin sh 不能执行 ELF）。
- `test_package/test.sh`：**14 项**确定性断言 ——
  esekeyd 用法/缺配置/坏设备三条错误路径（退出码+输出）、keytest 版本横幅、
  **合成二进制 input_event 记录**（aarch64 布局 24B/事件：timeval 16B +
  type 2B + code 2B + value 4B）回放给 keytest 验证 parse() 键名映射
  （KEY_A→"A"、KEY_ENTER 退出码 0）、事件文件大小自检、learnkeys 用法提示
  与 /dev/null 设备下配置骨架写出。
- 注意点：NUL 字节必须 printf 直写文件（命令替换会剥 NUL）。
- `test_package/MANIFEST.yml`：如实申报「上游测试 = 0」。
- esekeyd 守护进程本体需真实 /dev/input 设备与后台 fork，不纳入确定性断言；
  其配置解析路径通过「有效配置 + 坏设备」用例间接覆盖。

## W4 本机前置验证

| 检查 | 结果 |
|---|---|
| 源码 SHA256 复核 | 通过（= 58bdac99…，下载后 Get-FileHash 核验） |
| 补丁可用性 | 通过（干净解压目录 `git apply --check` → OK，并实际 apply 复核 Makefile.am/.in 两处修改生效） |
| Python 语法（conanfile.py ×2） | 通过（py_compile） |
| Shell 语法（test.sh） | 通过（bash -n） |
| YAML/JSON 结构（conandata/manifest ×2/MANIFEST/commands.json） | 通过 |
| **OHOS 交叉编译（真实）** | **通过**：DevEco OHOS SDK (openharmony) clang，`--target=aarch64-linux-ohos --sysroot=…`，手写最小 config.h 后 6 个 .c 全部编译通过，esekeyd/keytest/learnkeys 链接为 AArch64 ELF，readelf NEEDED 仅 libc.so |
| `conan create` | **未执行**（本机无 Conan） |
| 目标二进制运行 | **未执行**（本机无 OHOS 运行时；Windows 无法运行 aarch64-ohos ELF） |

交叉编译命令要点（证据可复现）：

```text
clang --target=aarch64-linux-ohos --sysroot=<sdk>/sysroot \
  -D_GNU_SOURCE -I<src> -I<src>/src -c <每个 .c>
clang --target=… --sysroot=… -o esekeyd esekeyd.o input.o parser.o
readelf -d esekeyd   # NEEDED: libc.so
```

> 说明：交叉编译验证源码/补丁/头文件兼容性，但不等于目标包可运行；
> `conan create`、test_package 待真机 shadow CI 执行，故状态 pending。

## 遗留与阻塞点

- 本机无 Conan，未执行 `conan create` / test_package（待真机 shadow CI）。
- 真机窗口未申请：本轮按任务要求仅做本机前置工作。
- 运行时提醒：esekeyd 部署需 /dev/input/event* 可读 + /proc/bus/input 可访问
  （自动探测才需要，可显式传设备路径绕开），真机仅验证非硬件路径。

## W5 真机 shadow CI 结果

### r1（失败，环境问题，非包问题）

| 项 | r1 |
|---|---|
| job 名 | esekeyd-1.2.7-20260929 |
| run 目录 | ohos-test-runs/codex-1.2.7-esekeyd-1.2.7-20260929-conan-20260929-101514-14037 |
| 排队等待 | lock.txt: wait_seconds=0 |
| exit code | 1 |
| 门禁 | G0/G0e/L0 pass；**KC fail** → L1/L2/L4/L5 全 blocked_by_KC |
| 报错原文 | `ci/conan/build_and_test.sh:980: permission denied: bash`、`stderr: :164: permission denied: git` |
| 根因 | job 的 zsh 环境 PATH（/bin:/usr/bin:…）不含 `/data/service/hnp/bin`，KC 门禁调 `bash ci/scripts/knowledge_check.sh`、G0e 调 `git ls-files` 时找不到可执行文件 |
| 解法 | 启动 runner 前置 `export PATH=/data/service/hnp/bin:$PATH`（环境供给，零基础设施改动）→ r2 |

传输走 scp + 设备端 find 清点 11 文件齐全；知识草稿 2 个已同步至 job repo 的
knowledge/drafts/。r1 证明包本体门禁（G0/G0e/L0：版本碰撞、commands.json、
目录结构）全部通过。

### r2（失败，E087 HMDFS 无执行位）

| 项 | r2 |
|---|---|
| run 目录 | …-conan-20260929-101815-16531 |
| 排队等待 | wait_seconds=0 |
| exit code | 1 |
| 门禁 | G0/G0e/L0/**KC** 全 pass；源码下载 + 补丁应用 OK；**conan create 失败** → L1 fail |
| 报错原文 | `/system/bin/sh: …/configure: Permission denied`、`ConanException: Error 126 while executing`（autotools.configure()） |
| 根因 | 构建目录在 HMDFS（/storage），脚本无执行位（E087），Autotools helper 直接 exec ./configure 报 126 |
| 解法 | build() 改为 `CONFIG_SHELL ./configure …`（bash 显式调用，rotix R5 同法），prefix='/' DESTDIR 风格，make/make install 用 self.run(env=conanbuild) → r3 |

r2 附带确认：mkparser 因补丁 0001 只链接不运行，规避了 HMDFS 上执行
构建期 ELF 的问题。

### r3（失败，cwd 指错目录）

| 项 | r3 |
|---|---|
| run 目录 | …-conan-20260929-102xxx |
| exit code | 1 |
| 报错原文 | `bash: ./configure: No such file or directory`（cwd=self.build_folder） |
| 根因 | basic_layout 的 `self.build_folder` 是 generators 目录（…/b/build-release），configure 在其上级的源码副本目录（…/b）——r2 日志中 Autotools helper 实际从 …/b/configure 执行 |
| 解法 | 配方自动探测 configure 所在目录（build_folder → source_folder 候选），configure/make/install 全部钉到该目录 → r4 |

### r4（失败，E011/E052 config.status 临时目录）

| 项 | r4 |
|---|---|
| run 目录 | …-conan-20260929-1029xx |
| exit code | 1 |
| 报错原文 | `config.status: creating src/Makefile` 后接 `./config.status: line 815: ./confG9Q2IC/out: Permission denied`（多轮 mv/rm 同报），随后 `sed: can't read Makefile`、`make: No targets specified and no makefile found` |
| 根因 | configure 探测全部通过（clang 识别、linux/input.h 检测 OK）；老 autoconf 的 config.status 主体用 `umask 077 && mktemp -d ./confXXXXXX` 建临时目录（E011/E052），HMDFS 权限语义下临时目录内写/mv/rm 全部 Permission denied → Makefile/config.h 没落盘 |
| 解法 | 补丁 0002：configure 内嵌 config.status 段两处 umask 077→000（rsyslog 8.2404.0 补丁 0001 同法，libestr/libfastjson CI 判例）→ r5 |

r4 附带确认：configure 探测阶段在真机全部通过（含 linux/input.h），且
`CONFIG_SHELL ./configure` + conf_dir 自动定位两项修复生效。

### r5（✅ 一次全绿）

| 项 | r5 |
|---|---|
| job 名 | esekeyd-1.2.7-20260929（隔离 job，--repo-source 复用设备 libltc job 的 repo） |
| run 目录 | ohos-test-runs/codex-1.2.7-esekeyd-1.2.7-20260929-conan-20260929-103547-40124 |
| 排队等待 | lock.txt: wait_seconds=1 |
| exit code | **0** |
| L0 / L1 / L4 / L5 | **pass / pass / pass / pass** |
| L1e | `[sabotage] bin/ moved away` → `Negative test confirmed — test genuinely depends on esekeyd` |
| L2 | **skip: esekeyd/keytest/learnkeys --version/--help failed**（non-blocking） |
| 上游测试 | 0/0（上游确无测试，MANIFEST.yml 已附清点证据） |
| test_package | **14/14 assertions PASS**（真机实跑） |
| 总评 | Pass rate: 100.0% (1/1)，`All packages built and tested successfully ✅` |

r5 实测记录（真机日志要点）：

- conan create：源码镜像下载、补丁 0001+0002 应用、`bash ./configure`（探测
  全过：clang 识别、linux/input.h presence/usability OK、ginstall/mkdir-p 命中
  profile PATH）、config.status 在 umask 000 下正常生成全部 Makefile、
  make -j1 编译三程序、make install DESTDIR 打包 bin/ + man + examples。
- L1e 破坏性反向验证：CI 把 bin/ 移走后重跑 test → FAIL → 确认测试真依赖产物。
- L2 skip 根因（非阻塞）：上游 CLI 无 `--version`/`--help` 长选项（getopt 短
  选项风格，esekeyd 无参数打印 Usage+版本 exit 1），E503（jshon）同族；与
  rotix r1 的 L2=skip 同判例，不为此扩大补丁面。
- 传输走 scp + 设备端 find 清点，敏感连接信息不入库。

### r5 后状态更新

版本级/软件级 manifest 状态 pending → **built**（真机 conan create +
test_package 通过）。`commands.json` 的 `binary` 保持 false（制品仓发布在
PR 合并后的 release 流水线，届时改 true）。

## W5 下一步真机/shadow CI 命令

```sh
# 隔离 job（真机，单包排队、错峰）
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex \
  --job esekeyd-1.2.7-<date> \
  --package archives/e/esekeyd/1.2.7 \
  --repo-source <existing-repo>

sh "$HOME/ohos-users/codex/esekeyd-1.2.7-<date>/run-conan-heavy.sh"
```

本机具备 OHOS conan 时的等价命令：

```bash
conan create archives/e/esekeyd/1.2.7 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

传输走 scp + 设备端 sha256 校验；敏感连接信息不入库。

## 知识草稿沉淀

本轮产出 2 条新知识草稿（`knowledge/drafts/`，.md + .kv 成对）：

- **DRAFT-esekeyd-1.2.7-generated-src-rule-build-host-prereq**：autotools
  生成源文件规则依赖构建机绝对路径且时间戳敏感（tarball 已含预生成结果时
  直接删规则）；自定义规则用 \$(SOURCES) 作编译输入破坏 VPATH，需改 \$<。
- **DRAFT-ohos-conan-autotools-helper-hmdfs-configure-126**：Autotools
  helper 直接 exec ./configure 在 HMDFS 报 126 → 手写 CONFIG_SHELL 调用；
  basic_layout 的 build_folder 是 generators 目录而非源码副本根，需
  conf_dir 探测；附真机 autotools 失败速查表（PATH/126/目录/umask/getcwd
  五类症状逐条路由到既有条目）。

查重结论（其余发现已有归属，不重复立条）：

| 本轮发现 | 既有条目 | 处置 |
|---|---|---|
| CI 门禁阶段 `permission denied: bash`（job PATH 缺 hnp/bin） | opencsg-1.8.2-shadow-ci-isolated-job-hnp-toolchain-path | 引用（增量：失败发生在 KC/G0e 门禁而非 build 阶段，写入新草稿速查表） |
| config.status umask 077 临时目录 | E011/E052/E129 + rsyslog 8.2404.0 补丁 0001 判例 | 引用（补丁 0002 同法） |
| 无 AC_CANONICAL_HOST 免 config.guess 之坑 | E007/E160 的反向确认 | 引用 |
| L2 冒烟 × esekeyd 无 --version/--help | E503（jshon 同族，rotix r1 已引用） | 引用；L2=skip(non-blocking) |

## 下一步（W6）

```bash
# 真机 shadow CI 通过后，提交前终检 + 一键提交
python3 scripts/ohc-run.py submit esekeyd 1.2.7
```

## issue 说明

任务下发时未提供 issue 编号；仓库内（archives、knowledge、git grep）
未找到 esekeyd 相关 issue 记录。按任务兜底要求继续完成本机前置适配，
**issue 编号待补**。

## 交付物

| 文件 | 说明 |
|---|---|
| conanfile.py | application 型配方（标准 autotools 流程，--sbindir 收进 bin） |
| conandata.yml | Ubuntu orig tarball URL + SHA-256 + 补丁声明 |
| patches/0001-makefile-vpath-and-no-parser-regen.patch | 移除 parser.c 生成规则 + mkparser VPATH 修复（portability） |
| test_package/ | conanfile.py + test.sh（14 断言）+ MANIFEST.yml |
| manifest.yaml（版本级/软件级） | status: pending + validation 记录 |
| commands.json | CLI 工具声明（R38，软件级） |
| README.md | 软件级说明 |
| notes.md | 本文件 |
