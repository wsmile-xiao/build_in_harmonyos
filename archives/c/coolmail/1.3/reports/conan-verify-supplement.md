# conan-verify 补充验证 — coolmail 1.3（application 型包的 G4/L2/L4/L5 人工补测）

> 依据：`HARMONYOS_SINGLE_DEVICE_WORKFLOW.md` 第 7.2 节 —— `package_type = "application"`
> 的纯可执行包在 `conan-verify` 中整组命中「无 cache 路径」定位缺陷，报告行会同时打印
> `✅ PASS` 与 `⏭️ 跳过`（以跳过为准），L2/L4/L5 必须人工补测。
> 本轮工具报告原文（`reports/conan-verify-report.md`）：
> `G4: ✅ PASS / ⚠️ 无法找到程序包 ID`、`L2/L4/L5: ✅ PASS / ⏭️ 跳过（无 cache 路径）`。

## 采信轮

| 项 | 值 |
|----|----|
| 配方 | `coolmail/1.3@ohpcd/stable` |
| 被验证 SHA | `09834f778507709a2c4947ec2674fcd118c49b7a` |
| profile | `ci/conan/profiles/ohos-aarch64`（`-pr:h`/`-pr:b` 同 profile） |
| 干净构建日志 | `reports/conan-create-log.md`（逐字留档；原始 `conan-create.log` 246 行 / 19535 字节 / sha256 `fe170907c6b7374306e6ba498f9acd1f2149ae83973ce549792f7967d8049424`，因仓库规则第 19 条 PR 禁入 `*.log` 而以 `.md` 留档） |
| 干净轮标记 | `Uncompressing`=1、`Apply patch`=2、`Calling build()`=1、`RUN: make`=1、`smoke test OK`=1 |
| 包目录 | `${CONAN_HOME:-$HOME/.conan2}/p/*/coolm*/p` |

> 关于工具报告里的日志路径：`reports/conan-verify-report.md` 的 `📄 日志:` 行由 `conan-verify` 自己写出，指向它的落盘名 `reports/conan-create.log`；该 `.log` 按仓库规则 `.gitcode/review-memory.md` 第 19 条（PR 禁入 `*.log`）不入 PR，正文逐字留档于本目录的 `reports/conan-create-log.md`。

定位包目录的命令（分片目录名是「名前 5 字符 + hash」，每轮重建，必须用 glob）：

```sh
PKG=$(ls -d "${CONAN_HOME:-$HOME/.conan2}"/p/*/coolm*/p | head -1)
```

## G4 产物完整性

```sh
find "$PKG" -type f -printf '%P\t%s bytes\n' | sort
```

```text
bin/coolmail                     51648 bytes
conaninfo.txt                      293 bytes
conanmanifest.txt                  285 bytes
licenses/COPYRIGHT                1065 bytes
share/X11/app-defaults/Coolmail    277 bytes
share/man/man1/coolmail.1         2649 bytes
```

与 `package_info()` 声明一致：`bindirs = ["bin"]`（产物 `bin/coolmail` 存在）、
`includedirs = []`、`libdirs = []`（包内确实无 `include/`、无 `lib/`，纯可执行包）、
`resdirs = ["share"]`（man page 与 X11 app-defaults 均在 `share/` 下）。

## L2 消费者/产物真实执行

`conan create` 的 test_package 段（干净轮日志原文，逐字见 `reports/conan-create-log.md`）：

```text
coolmail/1.3 (test package): RUN: /bin/sh .../test_package/test_coolmail.sh \
  /storage/.../p/b/coolm*/p /storage/.../p/b/coolm*/p/bin/coolmail \
  /storage/.../test_package/build-release <依赖 libdir 列表>
OK: packaged binary present and executable
OK: coolmail -h exited 0
OK: usage banner present
OK: documented options listed
OK: headless run exited 1 after loading the X11/Xt chain
OK: man page installed
OK: X11 app-defaults installed
coolmail smoke test OK (7 checks)
```

断言数由脚本运行期累加（`checks=$((checks + 1))`）并打印在末行，因此「7」与日志里
`OK:` 行数（实测 `grep -c 'OK:'` = 7）恒等，不会随脚本改动漂移。

### 独立手工补测：原始输出

```text
$ LD_LIBRARY_PATH=<每个依赖包的 libdir> "$PKG/bin/coolmail" -h    # 退出码 0
Usage:  coolmail [options]

OPTIONS:
  ...

$ (unset DISPLAY; LD_LIBRARY_PATH=<deps> "$PKG/bin/coolmail")     # 退出码 1
Error: Can't open display: 

$ (unset LD_LIBRARY_PATH; "$PKG/bin/coolmail" -h)                 # 退出码 127
Error loading shared library libXt.so.6: (needed by .../bin/coolmail)
Error loading shared library libX11.so.6: (needed by .../bin/coolmail)
Error relocating .../bin/coolmail: XtInitialize: symbol not found
  ...（另有 30+ 行 "Error relocating ...: <X11/Xt 符号> not found"）
```

另测 `coolmail -int 5 -f <不存在的邮箱>`（无 DISPLAY）退出码 1、输出同为
`Error: Can't open display:`（说明参数解析已通过、进入 Xt 初始化后才失败）。

最后一段（无 `LD_LIBRARY_PATH` 时 rc=127）是 R34 的正面证据：被测二进制**确实**动态
依赖 libXt/libX11（并进而依赖 libSM/libICE/libxcb/libXau/libXdmcp），test_package 的
7 项断言是在真实解析了整条动态链的前提下执行的，不是空跑。

## L4 安全属性

```sh
readelf -h "$PKG/bin/coolmail" | grep -E 'Type:|Machine:'
readelf -lW "$PKG/bin/coolmail" | grep -E 'GNU_STACK|GNU_RELRO'
readelf -dW "$PKG/bin/coolmail" | grep -E 'FLAGS|FLAGS_1'
```

```text
Type:    DYN (Position-Independent Executable file)
Machine: AArch64
GNU_RELRO  0x005420 ... R 0x1
GNU_STACK  0x000000 ... RW 0
FLAGS       BIND_NOW
FLAGS_1     Flags: NOW PIE
```

判据全部满足：`DYN`（PIE）+ `GNU_STACK RW`（NX）+ `GNU_RELRO` + `BIND_NOW` + `FLAGS_1 PIE`。

## L5 产物基线

同一提交（`09834f778507709a2c4947ec2674fcd118c49b7a`）两次独立干净构建。每轮构建前都按
workflow 第 7.2 节四步清缓存，并用 `p/cache.sqlite3` 的 `recipes`/`packages` 两表回查确认为空
（回查输出抄录在下面 round B 日志文件头部）；两轮各自留有完整日志：

| 轮次 | 触发方式 | 本轮日志（随 PR 入库） | 包目录（分片名每轮重建） | `bin/coolmail` sha256 |
|------|----------|------------------------|--------------------------|----------------------|
| A | `conan-verify` 内的干净 create | `reports/conan-create-log.md` | `p/b/coolm740ad9706c621/p` | `142905fd195502b2a3095ece4ef54d346554dcf487e1580ec7da151949cfe4cd` |
| B | 再次清缓存后的独立 `conan create` | `reports/conan-create-round-b-log.md` | `p/b/coolmb47b5db757ca3/p` | `142905fd195502b2a3095ece4ef54d346554dcf487e1580ec7da151949cfe4cd` |

两轮日志的干净轮标记均为 `Uncompressing`=1、`Apply patch`=2、`Calling build()`=1、`RUN: make`=1、
`smoke test OK`=1；A 轮日志 246 行 / 19535 字节 / sha256 `fe170907c6b7374306e6ba498f9acd1f2149ae83973ce549792f7967d8049424`，
B 轮日志 261 行 / 19427 字节 / sha256 `589bcdad6469cbc5684b992a179d0013e3b887a026eba2495f7fdb90820d6692`。

> 说明（如实记录）：上表的分片目录名只能作为「当时那一轮的定位记录」，**不可用
> `ls -d … | head -1` 事后重放**——分片目录名含 uuid4、每轮重建，该命令在任何时刻解析到的都只是
> 「当前存活」的那一个。存活情况：round A 的 `p/b/coolm740ad9706c621/p` 已被后续清缓存删除；
> round B 的 `p/b/coolmb47b5db757ca3/p` 与 W3 轮创建的 `p/b/coolm160e36b32f50f/p` **仍存活**。
> 本文件的四个逐产物 sha256 与聚合值 `6da67786…` 已在**这两个互相独立的存活包目录上分别复算、
> 结果相同**，即 L5 结论不依赖任何单一目录是否被回收。

四个真实产物在两轮中逐文件一致：

| 产物 | sha256（两轮相同） |
|------|-------------------|
| `bin/coolmail` | `142905fd195502b2a3095ece4ef54d346554dcf487e1580ec7da151949cfe4cd` |
| `share/man/man1/coolmail.1` | `f1f75d1b44761a442248c4bedc5be2dda66295ed5ce95514898df63819ac040d` |
| `share/X11/app-defaults/Coolmail` | `10cd5e31230a5a8cc56e7eadfcd0166ba909c809b27bf154a86ff7fcd7d7d403` |
| `licenses/COPYRIGHT` | `4b9cd262382a896a98f291e2e3b70a4bee0f75a47a9670ba3c4ee3481f00993a` |

包内容聚合：命令固定在包目录内执行、用相对路径，并**排除**每轮重建的
`conaninfo.txt` 与 `conanmanifest.txt`（`conanmanifest.txt` 首行是打包时间戳，含它必然跨轮漂移）：

```sh
# 对每个仍存活的包目录分别执行（用文档原命令，相对路径在包目录内）：
for PKG in "${CONAN_HOME:-$HOME/.conan2}"/p/b/coolmb47b5db757ca3/p \
           "${CONAN_HOME:-$HOME/.conan2}"/p/b/coolm160e36b32f50f/p ; do
  ( cd "$PKG" && find . -type f ! -name conaninfo.txt ! -name conanmanifest.txt \
      | sed 's|^\./||' | sort | xargs sha256sum | sha256sum )
done
# 两个独立目录均输出同一值：
#   6da677862c721dfd7b06794c0c5c9ec6db12f07bb7bd1d3963786f2023651c7d
```

结论：产物可复现（上游未使用 `__DATE__`/`__TIME__`，构建目录差异不进入产物）；
L5 的稳定基线取上表四个逐文件 sha256（已在上述两个独立存活包目录上复算一致），聚合值 `6da67786…` 仅作辅助。

## W3 本地 CI 模拟结果（`reports/w3-local-ci-log.md`）

| 门禁 | 结果 | 证据行 |
|------|------|--------|
| G0 知识图谱完整性 | pass | `[ok] G0: Knowledge graph integrity check passed (540 entries)` |
| G0e 根目录白名单 | pass | `[ok] G0e: Root directory whitelist passed` |
| L0i 依赖已发布（R36） | pass | `[ok] dependency in registry: libxt/1.3.1` |
| L0j 版本冲突（R37） | pass | `[ok] version not in registry yet (first publish)` |
| L0k commands.json（R38） | pass | `[ok] commands.json valid (type=tool)` |
| L0m 目录结构（R39） | pass | `[ok] L0m: directory structure valid` |
| KC1–KC5 知识库质量 | pass | 草稿泄漏/占位符/字段格式/index.tsv 一致性全部 OK |
| L1a/L1b test_package 已执行 | pass | `[ok] L1a: test_package was executed by conan create` |
| **L1e 破坏性反向验证（R34）** | pass | `[sabotage] bin/ moved away` → `[ok] L1e: Negative test confirmed — test genuinely depends on coolmail` |
| L5 产物基线 | pass | `[ok] L5: bin/ has content` |
| L2 冒烟 | **skip** | `[warn] L2: coolmail --version/--help failed (non-blocking)` |
| L4 补丁危险函数扫描 | **warn** | `[warn] L4: Dangerous functions found in patches: patches/0001-coolmail.c.patch` |

- L1e 证明 test_package 的 7 项断言**真实依赖被测包产物**（把 `p/bin/` 移走后测试失败），
  不是空跑。
- **L2 skip 属框架已知缺陷**（workflow 第 17 节：W3 的 L2 探针只试 GNU 长选项
  `--version`/`--help` 并要求输出可识别）：coolmail 是 1995 年的程序，只支持单横线选项，
  `-h` 打印 usage 并 `exit(0)`，而 `--version`/`--help` 会被当作未知参数处理——
  因此 L2 恒 skip。已按第 7.2 节人工补测（见本文「L2 消费者/产物真实执行」小节：
  `-h` 退出码 0 + usage 文本 + 无 DISPLAY 的 Xt 诊断 + 无 `LD_LIBRARY_PATH` 时 rc=127 反证）。
- **L4 warn 为上游代码固有形态**：命中项是补丁里的 `strcat`（上游 `coolmail.c:107`
  原本就在用，补丁只是替换了它的实参来源），属非阻塞告警，语义上不构成安全回归。
  该扫描面还会命中工具自己在包目录内建的补丁备份副本（`patches/.patch-backup-<时间戳>/`，
  由 `refresh-patch` 每轮新建且从不清理）；本文件引用的这一轮 W3 日志中
  `grep -c patch-backup` = 0（备份目录已在扫描前清除）。本 PR 不含 `feedback/` 改动，
  该工具行为只在本文件内说明，不外链到 PR 之外的路径。

## X11 依赖选择证据：为何移除上游 Makefile 的 `-lXext`

上游 `Makefile:39` 写的是 `LIBS = $(LIB_DIRS) -lXt -lX11 -lm -lXext`。在本依赖图下加入
libXext 不可行，证据分三层，全部随 PR 入库：

**① 一手实测日志**：`reports/libxext-package-id-probe-log.md`（逐字留档；原始 `libxext-package-id-probe.log` 128 行，sha256
`cd759ab2b4ec85000431f8288053a4ee74b2e1070b318059c42510abedd5acaa`），由最小探针配方
`reports/libxext-package-id-probe-conanfile.py` 复现（该文件即探针本体，可直接重建）：

```sh
mkdir probe && cp reports/libxext-package-id-probe-conanfile.py probe/conanfile.py
conan install probe \
    -pr:h=<本 worktree 绝对路径>/ci/conan/profiles/ohos-aarch64 \
    --build=never -of probe/out          # 退出码 1
```

> profile 必须写绝对路径（或 `./` 开头的相对路径）：Conan 的 `get_profile_path()` 对不以
> `./`/`..` 开头的相对路径会**先**在 `$CONAN_HOME/profiles/` 下查找同名文件，本机存在陈旧副本
> `$CONAN_HOME/profiles/ci/conan/profiles/ohos-aarch64`（134 字节，2026-08-28，缺 `os.version`），
> 因此裸写 `-pr:h=ci/conan/profiles/ohos-aarch64` 会报 `settings.os.version value not defined`
> （实测退出码 6）而不是本探针预期的退出码 1。

日志关键段（原样摘录，`...` 处为省略的 profile 回显与图节点列表）：

```text
ERROR: Missing binary: libxext/6.4.0.1:eab79208a9437a856077cc57885309d75bdb4a31

libxext/6.4.0.1: WARN: Can't find a 'libxext/6.4.0.1' package binary
'eab79208a9437a856077cc57885309d75bdb4a31' for the configuration:
[settings]
arch=armv8
build_type=Release
compiler=clang
...
[requires]
libx11/1.8.Z
```

即 `libxext` 系列的已发布 binary 是按 `libx11/6.4.0` 计算的 package_id（`eab79208…`），
与 `libxt/1.3.1` 所需的 `libx11/1.8.13` 组合不匹配；而 `libxext/6.4.0` 又把 `libx11/6.4.0`
钉死（与 libxt 冲突）。`libx11/1.8.Z` 不是脱敏或笔误，是 Conan 2.29.1 `_VersionRepr.minor()`
对区间解析后的真实渲染（同样形态见 `reports/conan-create-log.md` 的 `requires:` 行）。

**② 仓库内配方互证**（不依赖本次实测即可核对）：
`archives/l/libxext/6.4.0.1/conanfile.py` 与 `archives/l/libxext/6.4.0/conanfile.py` 的
`requirements()` 都写 `self.requires("libx11/6.4.0")`。

**③ 源码确实不需要 Xext**：

```sh
nm -D --undefined-only "$PKG/bin/coolmail" | grep -i 'XShape\|XShm\|Xext\|XSecurity\|Xdbe\|Xag\|XSync'
# 唯一命中是 XSync —— 它是 Xlib 的函数（libX11 的 X11/Xlib.h:3419 声明），不是 Xext API；
# XShapeQueryExtension / XShmCreateImage 等 Xext 入口在产物中一个都没有。
```

源码侧同样只有注释提到 Xmu/Xext（`system/X11/display_list.c:20-21` 是被注释掉的
`#include <X11/Xmu/Xmu.h>`）。结论：上游 `-lXext` 是多余链接，移除它不改变任何行为，
配方因此在 `build()` 的 `LIBS` 中去掉该标志（不改上游 Makefile）。

（`eab79208…` 这个 package_id 依赖远端 registry 索引，本地缓存中无 libxext 包目录，
因此不能离线复算；本 PR 以①的原始日志 + ②的配方源码作为证据。）

## 未覆盖范围（如实记录）

- **X server 不可用**：设备镜像内无 `Xorg`/`Xvfb`/`Xwayland` 可执行文件
  （`command -v` 全部为空），`DISPLAY` 未设置，`/tmp/.X11-unix` 不存在；
  制品仓亦未发布 OHOS `xorg-server`（`conan list xorg-server/* -r=ohpcd` → 0 条）。
  因此窗口创建、3D 动画、邮箱状态轮询与点击启动邮件阅读器这几条路径
  **无法在本环境运行**，只有命令行路径（`-h`）与 Xt 初始化失败路径被真实执行。
- **digitized audio 未编译**：上游 OSS 后端（`#ifdef linux` + `<linux/soundcard.h>`）
  在 OHOS SDK 下无头文件、设备无 `/dev/mixer`、`/dev/dsp`，按上游 README 记载关闭；
  `-af`/`-vol` 选项因此不可用（上游无 AUDIO 构建的固有行为）。
- **上游测试**：不存在（Makefile 无 `check`/`test` 目标，`make -n check` 报
  `No rule to make target 'check'`），详见 `test_package/MANIFEST.yml`。
