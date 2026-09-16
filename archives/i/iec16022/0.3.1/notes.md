# iec16022 0.3.1 适配笔记

- 适配路径: 路径 B（贡献创新）/ B 类难度库 — 知识库拓展
- 范围: 本轮只改 `archives/i/iec16022/`，以及 `knowledge/drafts/` 中与本库直接相关的草稿

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | iec16022 |
| 上游版本 | 0.3.1（tag `v0.3.1`） |
| 许可证 | GPL-2.0-or-later |
| 上游仓库 | https://github.com/rdoeffinger/iec16022 |
| 源码 | https://github.com/rdoeffinger/iec16022/releases/download/v0.3.1/iec16022-0.3.1.tar.xz |
| sha256 | `5a83dbab402390695367cf1ea456140e51ff68171cbc0352ceba4be227715e07` |
| 功能 | DataMatrix（IEC 16022 / ECC200）二维条码生成库 + 命令行工具 |

产物：`libiec16022`（`iec16022ecc200` / `image` / `reedsol` 三个模块）与 `bin/iec16022`。

## 编译环境

- 构建系统: autotools（官方 release 包已自带生成的 `configure` + `Makefile.in`）
- 目标平台: HarmonyOS PC (OHOS) aarch64，conan profile `ohos-aarch64`
- 编译器: clang 15.0.4（OHOS SDK）
- 状态: built（真机 shadow CI 全绿；制品仓 release 上传未执行，故按 R29 记 built 而非 published）

## 编译步骤

1. `conan create` 拉取官方 release 包（tar.xz）并解压到 source 目录。
2. 应用 `patches/` 下三个补丁（config.guess / config.sub / configure）。
3. `configure`：由 `AutotoolsToolchain` 注入 CC/CFLAGS/LDFLAGS；`PkgConfigDeps`
   生成 `popt.pc` 供 configure 的 `PKG_CHECK_MODULES([POPT], [popt])` 检测。
4. `make -j1`。
5. `make check -j1` 运行上游端到端测试（L1）。
6. `make install` → 打包 `lib/`、`include/`、`bin/`，许可证入 `licenses/`。

## 依赖

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| popt | 1.16 | 运行时（静态） | CLI 选项解析；configure.ac 硬性要求，缺失即 `Missing library: popt not found` |
| zlib | — | 不需要 | `image.c` 的 zlib 分支由 `#ifdef USEZLIB` 关闭（源码中已注释掉 `#define USEZLIB`） |
| libm | — | 不需要 | 源码未使用任何 math 函数，无需 `-lm` |

> `popt/1.16` 已在制品仓发布（`archives/p/popt/1.16`），本库只声明依赖，不含依赖适配。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type` / `unable to guess system type` | 官方 `config.guess`（2022-01-09）没有 HarmonyOS 分支，`uname -s == HarmonyOS` 无匹配（E007） | 补丁 0001：在 case 表加 `*:HarmonyOS:*:*` 分支，输出 `aarch64-unknown-linux-ohos` |
| 2 | `Invalid configuration 'aarch64-linux-ohos': OS 'ohos' not recognized` | `config.sub` 不认识 `ohos` 操作系统（E072/E205） | 补丁 0002：加 `ohos-linux` 三元组与 `ohos*` OS 家族 |
| 3 | `Invalid configuration 'aarch64-linux-ohos': Kernel 'linux' not known to work with OS 'ohos'` | 仅补 OS 家族不够，还要过 kernel-OS 组合校验（E122） | 补丁 0002：在 kernel-OS 校验列表补 `linux-ohos*` |
| 4 | `config.status: can't create ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 强制目录 setgid，`umask 077 && mktemp -d` 建出属主不可写的 `drwx--S---`（E011/E114） | 补丁 0003：configure 临时目录 umask 077 → 002（保留 build 目录内建目录，避免多 worker 争用固定路径） |
| 5 | `configure: error: C compiler cannot create executables` | HarmonyOS `/tmp` 只读，TMPDIR 未设置时编译器把临时文件写 `/tmp` 被拒（E002） | 配方 `generate()` 中建 `build/tmp` 并把 `TMPDIR` 指向它（build scope） |
| 6 | `make: jobserver mkfifo: Operation not permitted` | `make -j>1` 需要 jobserver FIFO，HMDFS 拒绝（E074） | 所有 make 调用固定 `-j1` |
| 7 | 真机：`RUN: ".../configure" ...` → `Permission denied`，`ConanException: Error 126`（`autotools.configure()` 帧） | 鸿蒙拒绝以 shebang 方式启动脚本，`Autotools.configure()` 直接把 configure 当作命令执行即被拒；`CONFIG_SHELL` 无效——它是 Autoconf **启动后**才读的，救不了第一个进程（E232） | 配方 `build()`：以 `settings_build.os == "OHOS"` 判定原生构建机，用 `/system/bin/sh <configure> <autotools._configure_args>` 显式启动，其余平台保持 `autotools.configure()` |
| 8 | 真机：`test-driver: test/./testsuite.sh: /bin/sh: bad interpreter: Permission denied`（exit 126） | 同上——automake 测试驱动直接 exec 测试脚本，shebang 路径被内核/SELinux 拒绝；改 shebang 为 `/bin/sh` 同样被拒，说明与解释器路径无关 | `make check` 传 `LOG_COMPILER=/system/bin/sh`，让驱动以 `sh script` 形式调用，脚本 shebang 不再参与（仓库已有 14 个配方如此处理） |
| 9 | 真机：`diff: testsuite-example.text: No such file or directory`（6 种格式全部 FAIL） | `conan create` 是 out-of-tree(VPATH) 构建，`make check` 在 build 目录运行脚本，而参考产物只存在于源码 `test/`；脚本用裸文件名引用 | 补丁 0004：改为 `${srcdir:-.}/testsuite-example.*`。automake 确实会向测试环境导出 `srcdir`（指向源码目录）；`:-.` 使 in-source 构建行为不变 |

### 关于 --build/--host

没有使用 `--build/--host` 绕过 triplet 检测。按 E007 的结论，那样会把
`cross_compiling` 置为 `yes`，使全部 `AC_RUN_IFELSE` 探测被跳过，`config.h`
与实际运行环境不符。本库通过补丁让 configure 在 `aarch64-unknown-linux-ohos`
三元组下原生判定，所有探测正常执行。

### 关于 problem 7 的判定条件（为什么用 settings_build）

E232 特别强调：必须以 `settings_build.os`（执行构建的机器）而非 `settings.os`
（目标平台）来判定。二者在 Windows/Linux 交叉编译到 OHOS 时会分化——那种场景下
目标 `os=OHOS` 成立，但构建机上并不存在 `/system/bin/sh`。本配方据此只在原生
鸿蒙构建机上走显式 shell 分支。

### 关于 problem 8（为什么最终没有改 shebang）

先尝试过补丁把 `test/testsuite.sh` 的 `#!/bin/bash` 改成 `#!/bin/sh`：错误从
`/bin/bash: bad interpreter: No such file or directory` 变成
`/bin/sh: bad interpreter: Permission denied`。这说明鸿蒙拒绝的是**shebang 这种
机制本身**，而非某个解释器路径缺失，所以改 shebang 无法解决。改用
`LOG_COMPILER` 后由驱动把脚本作为参数交给 shell，才真正绕开该机制，且**无需修改
上游任何测试文件**。该补丁已删除，最终补丁集保持为 4 个。

### 关于 problem 9（为什么改测试脚本而不是复制夹具）

也可以选择在 `build()` 里把源码 `test/*.example.*` 复制进 build 目录，但那样
（a）要在配方里硬编码夹具清单，（b）丢失了 upstream 用例“在源码树里比参考产物”
的原意。`${srcdir:-.}` 只改脚本对参考产物的定位方式，保持上游测试语义与断言
强度不变，且对 in-source 构建完全透明。

### 关于 configure 临时目录补丁

补丁 0003 只放宽 `umask`（`077` → `002`），仍保留 autoconf 默认的
`mktemp -d "./confXXXXXX"`（在 build 目录内创建）。这是本项目多个已合入 autotools
包的既有做法（参照 aaphoto 0003-configure.patch）。未改成固定路径
（如 `${HOME}/tmp/confXXXXXX`），因为那样会让多个并发 conan 构建争用同一个
固定目录名。

## 源码修改（补丁）

| 补丁 | 修改文件 | 修改内容 |
|------|----------|----------|
| 0001-config.guess-harmonyos.patch | `config.guess` | 增加 `*:HarmonyOS:*:*` 系统识别分支（输出 `*-unknown-linux-ohos`），并顺带把 `set_cc_for_build` 与主探测里的 `umask 077` 放宽为 `002`（同为 HMDFS 权限问题） |
| 0002-config.sub-ohos.patch | `config.sub` | 增加 `ohos-linux` 三元组、`ohos*` OS 家族、`linux-ohos*` kernel-OS 组合 |
| 0003-configure-tmpdir-hmdfs.patch | `configure` | config.status 临时目录创建逻辑 `umask 077` → `002` |
| 0004-test-testsuite-vpath-srcdir.patch | `test/testsuite.sh` | 参考产物改由 `${srcdir:-.}/testsuite-example.*` 定位，兼容 out-of-tree(VPATH) 构建 |

补丁均为「修改已有文件」的 diff，不含新增文件；全部只改生成脚本与测试脚本，
未触碰 C 源码、未改任何断言。

## 上游测试（L1）

`test/testsuite.sh` 是唯一的上游测试，用同一 payload 生成六种输出格式，再与
`test/` 下随源码发布的参考产物逐字节 `diff`：

| 用例 | 格式 | 参考产物 |
|------|------|----------|
| Text test | `-f Text` | `test/testsuite-example.text` |
| EPS test | `-f EPS` | `test/testsuite-example.eps` |
| PNG test | `-f PNG` | `test/testsuite-example.png` |
| Bin test | `-f Bin` | `test/testsuite-example.bin` |
| Hex test | `-f Hex` | `test/testsuite-example.hex` |
| UTF-8 test | `-f utf8` | `test/testsuite-example.utf8` |

脚本返回非零即整个 `make check` 失败（`rm testsuite-test.*; exit $FAILED`），
因此在 `build()` 中调用 `make check` 是有效质量门禁。共 6 个 diff 用例。

**真机实测结果（shadow CI，L1）**：`PASS: ./testsuite.sh`，
`# TOTAL: 1 / # PASS: 1 / # FAIL: 0 / # ERROR: 0`——六种输出格式在 OHOS aarch64 上
与上游参考产物**逐字节一致**。上游 6/6 通过，无跳过、无豁免。

> 记录区分：**上游收集** 6 个 diff 用例（automake 记为 1 个 `testsuite.sh` 用例），
> 全部为纯本地编码/比对，无外网、无外部命令、无 root 依赖。真机已实际执行并通过。
> 离线复核：在设备上把参考产物放入脚本工作目录后直接运行 `sh testsuite.sh`，
> 六个格式单独打印 "… test passed"、退出码 0，与 shadow CI 结论一致。

## test_package（消费者视角）

`test_package/test_iec16022.c` 只包含安装后的公开头文件并链接装好的
`libiec16022`，覆盖 7 组、共 **40 处断言**：

1. 内嵌参考表自检（32 行非 NULL、长度足够）——防止夹具数组写法错误变成段错误。
2. 自动选尺寸编码结果与上游参考矩阵 `test/testsuite-example.text` 逐模块一致
   （32x32 = 1024 个模块全等），并校验 62 数据码字 / 36 ECC 码字容量。
3. ECC200 结构：左列 + `y==0` 行为实体 L finder，对边为交替 timing 轨道。
4. 指定尺寸编码（10x10 / 16x16 / 32x32 / 64x64）与非法尺寸 13x13 被拒绝。
5. 超出 `MAXBARCODE` 的载荷被拒绝。
6. ISO/IEC 16022 Annex R 官方校验向量（`142 164 186` → `114 25 5 88 102`）。
7. GS1 标志（`IEC16022_FLAG_GS1`）确实改变输出符号。
8. PNG 渲染：签名、IHDR、尺寸 = W+2/H+2、位深 1。

参考矩阵由 `test/testsuite-example.text` 生成后内嵌为
`test_package/fixture_upstream.h`，因此断言不依赖上游源码目录。

**真机实测结果**：`test iec16022 0.3.1: 40 checks, 0 failed / RESULT: PASS`。
CI 的 L1e 破坏性反向验证（移走 `bin/`、`lib/`、`include/` 后再跑）确认
`test genuinely depends on iec16022`，即该测试并非空壳（R34）。

## 本机前置验证

| 项目 | 结果 |
|------|------|
| 源码归档 SHA256 复核 | ✅ 与 `conandata.yml` 一致（两个独立镜像交叉核对） |
| 补丁对 pristine 归档干净应用 | ✅ 四个补丁 `patch -p1 --dry-run` 全部 clean |
| `config.guess` 功能验证 | ✅ 以模拟 `uname -s=HarmonyOS` 实测输出 `aarch64-unknown-linux-ohos`；未打补丁时报 `unable to guess system type` |
| `config.sub` 功能验证 | ✅ `aarch64-linux-ohos` / `aarch64-unknown-linux-ohos` / `x86_64-linux-ohos` 均被接受（打补丁前报 `OS 'ohos' not recognized`） |
| 参考产物一致性 | ✅ `testsuite-example.text` 按 CLI 打印顺序还原出的位图，与 `testsuite-example.bin` 逐字节相同（确认矩阵方向与 `lenp/maxp/eccp` 语义） |
| 内嵌夹具完整性 | ✅ 32 个字符串元素与 `testsuite-example.text` 逐行一致（独立脚本核对，防漏逗号） |
| 交叉编译 | ✅ 用 OHOS SDK clang 15 按上游原样 `AM_CFLAGS` 编译三个库源文件，**零告警**；CLI（含 popt.h）亦通过 |
| test_package 编译链接 | ✅ 用声明的 include 根编译并链接安装后的静态库成功，`NEEDED` 仅 `libc.so` |
| Python/YAML 语法检查 | ✅ `conanfile.py`、`test_package/conanfile.py` 通过 `py_compile`；全部 YAML 通过 `yaml.safe_load` |
| `git diff --check` | ✅ 无空白错误 |
| 变更范围 | ✅ 仅 `archives/i/iec16022/` |
| 真机 shadow CI | ✅ 全绿（详见下节） |

## 真机 shadow CI（已执行）

隔离 job：`iec16022-0.3.1-shadow-20260914-013426`（设备无 `git`，按指南用设备上
已有仓库作 `--repo-source`；包目录经 tar + base64 传输，设备端 sha256 与本地一致）。
执行入口：`$HOME/bin/ohos-test-runner.sh ... -- zsh ci/conan/build_and_test.sh archives/i/iec16022/0.3.1`。

```text
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=pass: iec16022 --help OK
L4_RESULT=warn: dangerous functions in patches
L5_RESULT=pass: bin/ has content
exit code: 0
Success: 1  Failed: 0  Pass rate: 100.0% (1/1)
```

| 证据 | 结果 |
|------|------|
| L0 依赖可用性（L0i, R36） | `[ok] dependency in registry: popt/1.16` |
| L0 版本占用（L0j, R37） | `[ok] version not in registry yet (first publish)` |
| L0 commands.json（L0k, R38） | `[ok] commands.json valid (type=tool)` |
| L0 目录结构（L0m） | `[ok] L0m: directory structure valid` |
| 上游官方测试（L1） | `PASS: ./testsuite.sh`；`TOTAL 1 / PASS 1 / FAIL 0 / ERROR 0` |
| test_package（L1） | `40 checks, 0 failed` → `RESULT: PASS` |
| L1e 破坏性反向验证（R34） | `Negative test confirmed — test genuinely depends on iec16022`（移走 bin/、lib/、include/ 后仍失败） |
| L2 冒烟 | `[ok] L2: iec16022 --help OK`（本 CLI 无 `--version`，故走 `--help` 路径） |
| L5 产物基线 | `[ok] L5: bin/ has content` |
| L4 补丁危险函数 | `warn`（**误报**，见下） |

**L4 告警属误报**：CI 的正则 `(strcpy|sprintf|gets|strcat)\b` 命中了
`0001-config.guess-harmonyos.patch` 上下文行里的英文单词 "tar**gets**"
（该行是上游 NetBSD 注释）。补丁新增行不含任何危险函数，L4 为 warn 级、不阻断构建。

> 真机执行过程中还排除了两类**环境**问题（与包本身无关，仅记录以便复现）：
> ① 设备登录 shell 的 `PATH` 不含 `/data/service/hnp/bin`，会使 `git` 落到他人 uid
> 的 wrapper 上（`permission denied`）、`bash` 找不到，从而误报 KC/G0e 失败——需把
> 该目录加回 `PATH`；② 设备 `/tmp` 只读，用 heredoc 写远程脚本会静默产出 0 字节文件，
> 需改用 tar/base64 传输。

## 复现命令（真机 shadow CI）

```sh
# 1) 建隔离 job（设备无 git 时用已有仓库作 --repo-source）
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex --job iec16022-0.3.1-<timestamp> \
  --package archives/i/iec16022/0.3.1 \
  --repo-source "$HOME/ohos-users/codex/<existing-job>/repo/build_in_harmonyos"

# 2) 传输包目录后先核对文件清单（16 个文件）
find archives/i/iec16022/0.3.1 -maxdepth 3 -type f | sort

# 3) 用仓库自带 runner 执行（PATH 需含 /data/service/hnp/bin）
sh "$HOME/ohos-users/codex/<job>/run-conan-heavy.sh"
```

重点记录：`exit code`、L0/L1/L2/L4/L5、上游 `make check` 的 6 个 diff 用例结果、
`test_package` 的 40 个断言结果。

## 路径 B / B 类候选知识草稿

本轮沉淀 2 条可复用草稿（均为真机 shadow CI 暴露、本机阶段无法发现的问题）：

- `knowledge/drafts/E577-draft-1EC1.kv` / `.md`
  — **Automake 测试驱动无法以 shebang 启动测试脚本**：OHOS 拒绝"经 shebang 启动脚本"
  这一机制本身（改 shebang 为 `/bin/sh` 仍 `Permission denied`），正解是
  `make check LOG_COMPILER=/system/bin/sh`；并显式区分于 E228（libtool 无扩展名 wrapper，
  且禁止对混合测试集无条件套用）、E087（chmod 不生效）、E165（shebang 目标不存在）。
- `knowledge/drafts/E578-draft-1EC1.kv` / `.md`
  — **out-of-tree(VPATH) 构建下测试脚本按裸文件名找不到参考产物**：夹具随源码发布、
  只在源码 `test/`，脚本用裸文件名引用导致 `make check` 六种格式全失败；正解是用
  `${srcdir:-.}` 定位（automake 会导出 `srcdir`，`:-.` 使 in-source 构建行为不变）。
  与 E519（同机制但在 install/packaging）、E552（夹具真的缺失）分界。

> 编号已按两口径取并集核查（跨 worktree 文件形态扫描 + 主线整词文本引用扫描），
> E577/E578 均零命中；详见草稿内「编号说明」节。最终分类以评审为准。

## 注意事项
- 首次真机执行外来二进制可能触发安全确认（E054）；如出现 `Permission denied`
  且手工执行一次后恢复正常，即属该机制，不要误判为库缺陷。
- 本包同时产物为库和 CLI，软件级 `commands.json` 已声明为 `tool`（R38）。
- `reports/`、`ci-metadata.json` 等 CI 生成物不提交。
- 真机上 `path` 环境务必包含 `/data/service/hnp/bin`（提供真正的 git/bash），
  否则 CI 的 G0e/KC 门禁会因找不到工具而误报失败。
- 静态链接的 `bin/iec16022` 不依赖 popt/libiec16022 运行时 `.so`；库消费者按
  `<prefix>/include/iec16022` 作为头文件根（与上游 `libiec16022.pc` 一致）。
