# E429 草稿：OHAudio 会选择实际回调帧长

## 现象

HarmonyOS OHAudio 流使用创建请求中的帧数作为实际回调帧数并不可靠。本次 HUAWEI MateBook Pro HAD-W24 真机运行中，流请求为 480 帧，OHAudio renderer 实际选择了 960 帧。对外接口若继续报告请求值，回调帧数、缓冲区大小和客户端看到的 bufferFrames 会不一致。

## 根因

创建参数表达的是请求值，不保证设备创建出的 renderer 或 capturer 使用相同的 callback quantum。实际值属于已创建流的运行时属性，应分别调用 OH_AudioRenderer_GetFrameSizeInCallback 或 OH_AudioCapturer_GetFrameSizeInCallback 查询。

## 推荐方案

1. 创建 renderer 或 capturer。
2. 对已创建的流调用对应的 GetFrameSizeInCallback API。
3. 检查 API 返回成功且实际帧数大于零；按实际帧数更新跨平台 API 的 bufferFrames。
4. 用实际帧数、通道数和样本宽度计算设备回调缓冲区，检查乘法溢出后再分配。
5. 让回调处理和统计使用设备实际交付的帧数。查询失败时拒绝启动该流，不要静默退回请求值。

## 验证

RtAudio 6.0.1.1 在 HarmonyOS AArch64 真机上请求 480 帧并查询到 960 帧的 OHAudio 回调量子。修复后的 backend 以查询值配置 callback buffers 和 bufferFrames；Conan create/test_package 在真机完成，U01–U27 与 H01–H02 共 29 项全部通过。设备运行记录为 1791874906628-91834。

## 适用范围与边界

适用于 HarmonyOS/OHOS 上以 OHAudio renderer 或 capturer 为后端的跨平台音频库。该经验只说明设备回调帧长可能不同于请求值；它不推断所有设备都会选择 960 帧，也不替代对采样率、通道数和格式的独立查询。

## 相关知识

E6400 草稿要求音频能力验证绑定到真实生产回调并观察非零 PCM；本条补充的是 stream 创建后查询设备实际 callback frame size 的缓冲区与帧数契约，两者覆盖不同问题。
