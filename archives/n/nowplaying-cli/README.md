# nowplaying-cli

`nowplaying-cli` 是一个命令行工具，用于**显示当前正在播放的乐曲信息**并**控制播放**
（播放/暂停/下一首/上一首/跳转等）。

- **上游**: [kirtan-shah/nowplaying-cli](https://github.com/kirtan-shah/nowplaying-cli)
  （macOS 专属，Objective-C(++) + Foundation/AppKit/Cocoa + 私有 MediaRemote 框架）
- **OHOS 适配**: 保留上游源码，应用 `patches/0001-portable-nonapple.patch` 提供
  非 Apple 平台的可移植 C++ 分支，映射到 OpenHarmony 原生 AVSessionKit（provider 侧）。

## OHOS 适配说明

上游依赖 macOS 私有框架：OpenHarmony native SDK 既无 Objective-C 运行时/Foundation
（实测 clang 首错 `'Foundation/Foundation.h' file not found`），也无 MediaRemote。
因此本包不删上游代码，而是用补丁把 `src/nowplaying.mm` 拆成
`#if defined(__APPLE__)`（上游原版逐字保留）与可移植分支；后者**对齐上游的子命令集合、
`get` 字段行为与退出码**（差异见下方专表）并映射到原生 AVSessionKit。

| 版本 | 说明 |
|------|------|
| 2.1.0 | 上游源码 + 可移植分支（`__APPLE__` 双路径）：子命令/`get` 行为/退出码对齐上游（差异见专表），控制命令走原生 AVSession provider，查询路径返回上游「无 now-playing 记录」时的相同输出，**不伪造数据** |
| 2.1.0.1 | 早期等价移植（历史版本，自造 demo 数据；保留供引用） |

**API 缺口（实测）**：OHOS native `libohavsession.so`（115 个导出符号）只有 provider 侧
（`OH_AVSession_Create/SetAVMetadata/SetPlaybackState/RegisterCommandCallback`）+ AVCast
投屏控制器；**无** native 的 `OH_AVSessionManager`/`OH_AVSessionController`/
`getAllSessionDescriptors`，也无 metadata getter（该能力仅在 ETS/JS AVSessionKit）。
因此：`get`/`get-raw` 返回上游「无 now-playing 记录」时的相同输出（每个键一行字面量 null
、`get-raw` 为 `{}`）；控制命令经原生 AVSession provider 会话
（`OH_AVSession_SetPlaybackState/SetPlaybackPosition`）执行，服务不可用时如实报错退出 1。

## 用法

```bash
nowplaying-cli [get [字段...] [--json]]     # 每字段一行；--json 输出 JSON 对象
nowplaying-cli get-raw                      # 完整记录 JSON（无记录时为 {}）
nowplaying-cli play | pause | togglePlayPause | next | previous
nowplaying-cli seek <secs>
nowplaying-cli --help | --version
```

退出码：`0` 成功（含上游的 help 回退分支），`1` 参数错误或能力不可用。

## Differences from upstream

可移植分支**不声称**与上游逐字节一致；以下是已核对并显式记录的差异：

| # | 上游行为（实测 `src/nowplaying.mm`） | 本分支行为 | 性质 |
|---|---|---|---|
| a | `seek` 仅在 `argc==3` 时生效；参数个数不符时回退 help 并 `return 0`；`argc==3` 时 `strtod` 解析失败才 `return 1` | 与上游相同（已对齐） | 无差异 |
| a2 | `argc==3` 时仅校验尾部字符；`inf`/`nan`/`1e999`/负数/超大值原样传给 `MRMediaRemoteSetElapsedTime(double)` | **更严格**：需转换为整型毫秒，故先用 `std::isfinite` + 上界 `9.0e15`（并拒绝负数）过滤，命中即 `Invalid seek time` + exit 1（避免浮点→整型越界转换） | 已记录（安全加固） |
| b | `printJSON` 使用 `NSJSONWritingPrettyPrinted` | `get --json` 输出 2 空格缩进、`" : "` 分隔的多行 JSON；**Cocoa 序列化器的精确空白与键序未逐字节复刻**；无记录时 `get-raw` 输出 `{}` | 已记录 |
| c | `printHelp()` 为固定字面量（4 段，程序名固定为 `nowplaying-cli`） | `--help` / 无参数 / 未知命令输出同一固定字面量帮助（已对齐）；平台说明与版本信息放在 `--version` | 已对齐 |
| d | `next` / `previous` / `togglePlayPause` 是三个不同的私有 MediaRemote 命令 | native provider API 无独立队列控制命令，三者均向 CLI 自有的 AVSession 会话发布 `PLAYING` 状态 | 平台能力缺口（已记录） |

此外 **`--version` 为本分支新增**（上游无该子命令，未知参数会回退打印帮助）。

## 参考

- 上游仓库: https://github.com/kirtan-shah/nowplaying-cli
- OHOS AVSessionKit (Native C API): SystemCapability.Multimedia.AVSession.Core
- 同类先例: `archives/m/m1ddc`（macOS 私有 API CLI 的可移植双路径模式）
