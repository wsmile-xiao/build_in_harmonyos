# nowplaying-cli 2.1.0 适配笔记（HarmonyOS PC / OHOS aarch64）

## 编译环境

- 构建系统: **上游 Makefile（macOS 专用）**；本仓可移植分支**未使用 make**，由 `conanfile.py::build()`
  直接调用一次 `clang++`（单编译单元）。manifest 的 `build_system: makefile` 指上游声明的构建系统，
  实际执行方式见下方「构建」小节。
- 编译日期: 2026-09-14
- 编译器: clang 15.0.4（OHOS NDK 26.0.0.18，target `aarch64-unknown-linux-ohos`）
- 目标平台: arm64（OHOS 6.0 / HarmonyOS PC）
- 状态: built
- 版本: **2.1.0**（R37：首次适配上游版本 = X.Y.Z，不加适配修复后缀）

## 上游事实（已复核）

`kirtan-shah/nowplaying-cli` v2.1.0（tag `v2.1.0`，commit `8c8c1fa482`）是 **macOS 专属
Objective-C(++) 工具**，通过私有 `MediaRemote` 框架 + `Foundation`/`AppKit`/`Cocoa`
读取系统 “now playing” 并发送播放控制命令。

tag 归档构成（sha256 `c7c23564657bf5b5598bdf58f79e11c8dffbde909e364df4da7c3a49a26e3753`）：

```
Makefile                          # macOS only: -framework Cocoa/Foundation/AppKit/UniformTypeIdentifiers
src/nowplaying.mm                 # 594 行 Objective-C++（Foundation/AppKit/MediaRemote/dlopen/mach-o）
src/mediaremote-mini/**/*.m,*.h   # 7 个 .m + 6 个头（Objective-C，MediaRemote 适配层）
include/Enums.h  include/MRContent.h
scripts/mediaremote-mini.pl
README.md  LICENSE  screenshots/examples.png  .github/workflows/build.yml
```

## R47 语言预检结论（脚本留证）

```
python3 $SKILL_ROOT/scripts/ohc-run.py lang-preflight nowplaying-cli 2.1.0 \
    --src $HOME/tmp/npcli/nowplaying-cli-2.1.0
```

输出（原文）：

```json
{
  "detected_language": "mixed",
  "language_evidence": {
    "build_system": "make",
    "manifest": "顶层 Makefile（无更强 manifest）",
    "source_stats": "源文件 1 个（perl:1），主体占比 100%"
  },
  "notes": ["冲突: manifest=c 但统计 perl 占 100% → mixed"]
}
```

判定器只按扩展名统计，`.m/.mm`（Objective-C/Objective-C++）不在其扩展名表内、
`.h` 中立跳过，故把唯一的 `scripts/mediaremote-mini.pl` 统计成了主体，得到
`mixed`。**补充硬证据（判定器未涵盖的真实阻塞点）**：

```
$ clang --target=aarch64-linux-ohos --sysroot=<sysroot> -c probe.m
probe.m:1:9: fatal error: 'Foundation/Foundation.h' file not found
1 error generated.

$ ls <sysroot>/usr/lib/aarch64-linux-ohos | grep -iE 'objc|dispatch|foundation'   # 空
```

即：上游确实是 **Objective-C(++)**，且 OHOS sysroot 无 `libobjc`/`libdispatch`/`Foundation`。
**源码级直接编译不可行**，这是本包必须走「平台可移植分支」的根本原因。

## 适配路线选择（职业判断）

任务书允许两条路：`env_unsupported` 终态，或历史已验证的「原生 AVSession 等价移植」。
本包选择 **后者**，理由与依据：

1. **仓库先例**：同类「macOS 私有 API 驱动的 CLI」在本仓已有评审通过的既有模式 ——
   `archives/m/m1ddc/1.0.0.1`（Objective-C 单文件 CLI，`#ifdef __APPLE__` 双路径 +
   可移植分支 + 诚实失败），并沉淀为 `knowledge/drafts/DRAFT-m1ddc-apple-ddc-transport-boundary.*`
   （PR #7051，metrics_confidence 0.86）。
2. **仓库历史**：`archives/n/nowplaying-cli/2.1.0.1`（等价移植）已合并并发布到制品仓。
   本次为 **2.1.0**（首次适配上游版本，R37）。
3. **任务书交付物清单**明确要求产出 `archives/n/nowplaying-cli/2.1.0/` 完整归档 + PR +
   CI 验证，且对「确实无上游可编译源码」情形要求「在 conanfile/notes 内明确说明并保证
   CI clean 环境可复现」——本包按此执行。

> **与历史 2.1.0.1 的差异（R15：历史仅供参考不盲从）**：2.1.0.1 丢弃了上游源码、
> 自造 demo 数据并在默认路径回落到硬编码 `DemoMetadata()`。本 2.1.0 **下载并保留上游
> 官方源码**，用补丁把上游原版**逐字保留**在 `__APPLE__` 分支，可移植分支 **不伪造任何
> now-playing 数据**（查询路径返回与上游「无 now-playing 记录」时相同的输出）。

## API 缺口（实测）

- `libohavsession.so` 导出 **115** 个符号：全部为 provider 侧（`OH_AVSession_Create/
  Activate/Deactivate/Destroy/SetAVMetadata/SetPlaybackState/SetPlaybackPosition/
  RegisterCommandCallback`）+ AVCast 投屏控制器（`OH_AVCastController_*`）。
- **不存在** native 的 `OH_AVSessionManager` / `OH_AVSessionController` /
  `getAllSessionDescriptors` / `getAVMetadata`（该能力仅在 ETS/JS `@ohos.multimedia.avsession`）。
- `native_avmetadata.h` 只有 builder setter，**无 metadata getter**；`OH_AVSession_AVPlaybackState`
  为回调侧的只读对象 —— native 侧无法做系统级 now-playing 查询。
- 实测 `OH_AVSession_Create(SESSION_TYPE_AUDIO, …)` 在 HarmonyOS PC 上 **rc=0 成功**
  （provider 路径真实可用），因此控制命令有真实原生代码路径。

## 移植实现（patches/0001-portable-nonapple.patch）

`src/nowplaying.mm` 被拆为：

```
#if defined(__APPLE__)
   <上游原版 594 行，逐字未改>
#else /* !__APPLE__ : portable OpenHarmony implementation */
   <可移植 C++17 实现>
#endif
```

可移植分支**对齐上游 CLI 的子命令集合、`get` 字段行为与退出码**；下列差异是
**已知且显式记录**的（不宣称逐字节一致），并已同步到 `README.md` 的
「Differences from upstream」表与 PR 正文：

| # | 上游实测行为 | 本可移植分支 | 性质 |
|---|-------------|-------------|------|
| a | `main()`：`strcmp(argv[1],"seek")==0 && argc==3`；**参数个数 ≠ 3 时落入 help 并 `return 0`**；`argc==3` 时 `strtod` 失败才 `return 1` | **已对齐**：仅 `argc==3` 视为 seek，参数个数不符时回退 help + `return 0`；`argc==3` 且非数字时 `stderr` + `return 1` | 已消除差异 |
| a2 | `argc==3` 时仅校验 `*end != '\0'`；`seek inf`/`nan`/`1e999`/负数/超大值都会原样传给 `MRMediaRemoteSetElapsedTime(double)` | **更严格**：本分支需把秒转换为整型毫秒，故先用 `std::isfinite` 与上界 `9.0e15`（并拒绝负数）过滤，命中即 `Invalid seek time` + `return 1`（避免浮点→整型越界转换 UB） | **已记录差异**（安全加固） |
| b | `printJSON` 用 `NSJSONWritingPrettyPrinted`（多行、Cocoa 风格） | `get --json` 用 2 空格缩进 + `" : "` 分隔的多行 JSON（对齐风格）；**Cocoa 序列化器的精确空白与键序不保证逐字节一致**；空记录 `get-raw` 输出 `{}` | 已记录差异 |
| c | `printHelp()` 为**固定字面量** `nowplaying-cli …`（4 段） | **已对齐**：`--help` / 无参数 / 未知命令输出与上游相同的固定字面量帮助；平台说明与版本移到 `--version`（额外子命令，非 `--help` 内容） | 已消除差异（`--version` 为新增） |
| d | `cmdTranslate`：`next`/`previous`/`togglePlayPause` 是三个**不同**的 MediaRemote 命令 | native provider API **没有**独立的队列控制命令，三者均向 CLI 自有的 AVSession 会话发布 `PLAYING` 状态 | **已记录差异**（平台能力缺口） |

命令行为速查：

| 命令 | 本分支输出/退出码 |
|------|------------------|
| `get [keys...]` | 每个键一行，值为字面量 null（无原生系统级查询）；exit 0 |
| `get --json [keys...]` | 多行 JSON 对象，每键值为 null；exit 0 |
| `get-raw` | `{}`（无记录）；exit 0 |
| `play/pause/togglePlayPause/next/previous` | 原生 AVSession provider：`OH_AVSession_SetPlaybackState`；成功 exit 0，服务不可用则如实报错 exit 1 |
| `seek <secs>`（argc==3 且有限、非负、≤9.0e15） | `OH_AVSession_SetPlaybackPosition`（ms）；成功 exit 0，不可用则如实报错 exit 1 |
| `seek <非数字/NaN/Inf/负数/超界>`（argc==3） | stderr `Invalid seek time: …` + usage，exit 1 |
| `seek`（argc≠3）/ `--help` / 无参数 / 未知命令 | 打印上游帮助文本，exit 0（同上游） |
| `--version` | 打印版本 + 平台说明；exit 0（**新增子命令**，上游无） |

## 构建

```bash
# 探索性直接编译（与 conanfile.py::build() 等价）
SYSROOT=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot
clang++ -std=c++17 -O2 -x c++ src/nowplaying.mm -o nowplaying-cli \
    -L$SYSROOT/usr/lib/aarch64-linux-ohos -lohavsession

# Conan 验证（ohos-aarch64 profile）
conan create archives/n/nowplaying-cli/2.1.0 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable
```

产物：`nowplaying-cli`（arm64 ELF，~31 KB，动态链接系统 `libohavsession.so`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `'Foundation/Foundation.h' file not found` | OHOS 无 Objective-C 运行时/Foundation | 补丁把 macOS 实现保留在 `__APPLE__`，非 Apple 平台提供可移植 C++ 实现 |
| 2 | 上游 Makefile 用 `-framework Cocoa/Foundation/AppKit` | macOS 专用构建 | 可移植分支只需编译单个 TU，recipe 直接用 `clang++` 调用（对齐 m1ddc 先例） |
| 3 | 链接 `-lohavsession` 路径 | 非默认库搜索路径 | 由编译器 realpath 推导 sysroot（`…/native/llvm/bin/clang++ → …/native/sysroot`），加 `-L<sysroot>/usr/lib/aarch64-linux-ohos`（未依赖 shell 环境变量，R33） |
| 4 | `src/nowplaying.mm` 默认按 Objective-C++ 编译 | 扩展名 `.mm` | 编译时显式 `-x c++`（`__APPLE__` 分支被预处理排除后为纯 C++17） |

## 验证结果

```
$ ./nowplaying-cli --help                 # 上游固定帮助文本, exit 0
$ ./nowplaying-cli --version              # nowplaying-cli 2.1.0 (OpenHarmony port), exit 0
$ ./nowplaying-cli get title album artist # 三行字面量 null, exit 0
$ ./nowplaying-cli get --json title artist # 多行 JSON, 每键 null, exit 0
$ ./nowplaying-cli get-raw                # {}, exit 0
$ ./nowplaying-cli play                   # exit 0（原生 AVSession provider 路径）
$ ./nowplaying-cli seek 60                # exit 0
$ ./nowplaying-cli seek not-a-number      # exit 1 + "Invalid seek time"
$ ./nowplaying-cli seek 60 70             # 帮助文本, exit 0（对齐上游 argc≠3 分支）
$ ./nowplaying-cli unknown-cmd            # 帮助文本, exit 0（同上游）
```

W3 本地 `conan create` 与 CI 结论见 `reports/` 与终态 `result.json`。

## 依赖版本

- 无 Conan 依赖；仅链接 OHOS native SDK 系统库 `libohavsession.so`
  （SystemCapability.Multimedia.AVSession.Core）。
- cmake 4.1.2、clang 15.0.4、conan 2.29.1。

## 上游测试

上游 v2.1.0 **无任何测试**（归档无测试框架/目录/源码，Makefile 无 check/test 目标）。
详见 `test_package/MANIFEST.yml` 的审计记录（discovered=0 / executed=0）。test_package
以已安装二进制的 15 项确定性行为断言接入（R34/R51）。
---

**编译结束**: 2026-09-14 14:22
**最终状态**: built
