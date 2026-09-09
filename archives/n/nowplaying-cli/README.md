# nowplaying-cli

`nowplaying-cli` 是一个命令行工具，用于**显示当前正在播放的乐曲信息**并**控制播放**
（播放/暂停/下一首/上一首/跳转等）。

- **上游**: [kirtan-shah/nowplaying-cli](https://github.com/kirtan-shah/nowplaying-cli)（macOS 专属，Objective-C + Foundation/AppKit/MediaRemote 私有框架）
- **OHOS 适配**: 纯 C++17 等价移植，基于 OpenHarmony 原生 AVSessionKit provider API（`libohavsession.so`）

## OHOS 等价移植说明

上游为 macOS 专属 Objective-C 工具，OHOS SDK 无 libobjc/libdispatch/Foundation，
源码级移植不可行（`env_unsupported`）。本包为**功能等价移植**：

| 版本 | 说明 |
|------|------|
| 2.1.0.1 | 纯 C++17 单二进制 CLI（provider 演示 + controller 桥接桩点） |

**API 缺口**：OHOS native SDK 的 `libohavsession.so`（115 符号）只有 provider 侧
（`OH_AVSession_Create`/`SetAVMetadata`/`SetPlaybackState`/`RegisterCommandCallback`）
+ AVCast 投屏控制器；**无** native 的 `AVSessionManager`/`OH_AVSessionController`/
`getAllSessionDescriptors`（该能力仅在 ETS/JS AVSessionKit）。因此 `get` 读取本
provider session 的元数据（`--demo` 演示链路），控制命令经 `ControllerBridge`
桩点分发（预留 ETS 桥接位置），CLI 接口与上游完全一致。

## 用法

```bash
nowplaying-cli get [字段...] [--json] [--demo]
nowplaying-cli get-raw [--demo]
nowplaying-cli play | pause | togglePlayPause | next | previous
nowplaying-cli seek <secs>
nowplaying-cli --help
```

## 参考

- 上游仓库: https://github.com/kirtan-shah/nowplaying-cli
- OHOS AVSessionKit (Native C API): SystemCapability.Multimedia.AVSession.Core