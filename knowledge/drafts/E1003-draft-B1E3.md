# E1003 (draft) MPD headless 消费者测试：null 输出零依赖播放闭环 + 协议状态机断言

> 状态：草稿（contributor B1E3，2026-10-01，mpd 0.24.12 路径C 适配 轮B）
> 对应 kv：E1003-draft-B1E3.kv

## 背景

mpd 0.24.12 是音乐播放守护进程，核心功能 = 协议 → 队列 → 解码 → 输出 的播放链路。OHOS headless 环境无 ALSA/JACK 音频设备，R40 实质验证不能依赖真实出声——需要一条零依赖、可闭环验证播放链路的路径。

## 关键事实（实证）

1. **null 输出插件无条件编译**（`src/output/plugins/meson.build` 的 `output_plugins_sources` 初始值），配置 `audio_output { type "null" name "X" }` 即可在 headless 环境使用，零新依赖
2. 播放闭环的**唯一可观测信号** = `status` 轮询的 `state` 迁移：`play` → `stop`
3. **协议坑**（两条都是直觉误用，实测报错）：
   - `play N` = **播放列表索引**（不是数据库 ID）；启动时列表为空 → `Bad song index`
   - `add <uri>` 用 **music_directory 相对路径**；`listall` 的 `0:` 前缀（数据库索引）不能传 add → `No such directory`
4. 稳定捕获状态窗口需 **≥2s 音频样本**（0.5s wav 过短，play 状态可能采不到）

## 测试模板（test_package C4 已落地）

1. `python3 wave` 生成 3s wav（440Hz，44100Hz mono）
2. 独立配置：port 6602 + 独立 music_dir/db/log；0.24 配置格式**无等号**（`name "value"`）；`mpd --no-daemon <conf>`（配置路径是位置参数，无 `--config`）
3. `python3 socket` 客户端：recv greeting → `listall` → `add <相对路径>` → `play 0` → 每 0.4s 轮询 `status`（20 次 ≈ 8s 窗口）
4. **仅 saw_play 与 saw_stop 均为真才通过**（play→stop 闭环证明）；失败输出 mpd 日志 tail

## 证据

- mpd 0.24.12 OHOS aarch64 真机实测 PASS（2026-10-01）：`state=play (0:3→3:3) → stop`，日志 `player: played "sample.wav"`
- 已固化入 `archives/m/mpd/0.24.12/test_package/test_mpd.sh` C4 段
