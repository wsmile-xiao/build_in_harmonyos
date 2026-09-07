# E554 — 音频解码 CLI 的可审计合成 Fixture 与无声卡文件输出验证

## 1. 使用说明

本条目解决一类问题：音频解码/转码 CLI（如 madplay）在无物理音频设备的自动化环境（OHOS CI、headless 容器）中，默认播放路径因 `/dev/dsp`（OSS）、ALSA 等设备节点不存在而失败，导致无法运行任何真实解码验证。

使用方法：不依赖默认播放路径，改用**程序化生成 fixture + 文件 sink 输出**的组合，让被测程序执行同一条真实解码管线（demux → MPEG 帧同步 → requantize → synth → PCM），输出到 wave/hex/raw 文件，再对产物做结构化校验。

本文中的 madplay 0.15.2b 实例只是该模式的**首个成功案例**，方法本身适用于任何满足以下条件的 CLI。

## 2. 适用范围

- 音频解码 CLI（madplay、mpg123-decoder 类、ffmpeg 音频流解码等）
- 音频转码 CLI
- OHOS 或其他无声卡 CI 环境
- 无法访问 OSS/ALSA/物理设备的自动化环境（headless 容器、远程构建机）
- 支持 WAVE/RAW/PCM/文本采样等文件 sink 的程序

## 3. 不适用范围

- 必须验证真实扬声器播放质量的测试（主观/客观听感评测）
- 必须验证音频设备驱动行为的测试（设备节点 ioctl、驱动延迟、混音器）
- fixture 无法程序化生成、或许可来源无法确认的场景（此时应转为人工验证或显式记录平台限制）
- 仅编译链接验证（compile/link 成功不代表解码正确）
- 仅 `--help` / `--version` smoke（不触发解码路径）

## 4. 输入定义

| 项 | 值 | 说明 |
|---|---|---|
| 容器 | 裸 MPEG 音频流 | 无 ID3v2 前缀、无容器封装 |
| 编码参数 | MPEG-1 Layer III, 128 kbps, mono, 44100 Hz | 由 4 字节帧头逐位定义 |
| 帧长 | 417 字节/帧 | floor(144 × 128000 / 44100) |
| 帧数 | 25 | conanfile.py FRAMES=25 |
| 生成方式 | gen_fixture.c 纯算术生成 | 全零 side info + part2_3_length=0 → libmad requantize 为静音 PCM |
| 总大小 | 25 × 417 = 10425 字节 | sha256: c07e6c0e…4e0c5 |
| 可审计性 | 无外部音频数据 | 来源即 MPEG 帧头定义，可逐位复核 |

## 5. 输出定义

**wave sink**（`madplay -o wave:out.wav`）：

| 字段 | 期望值 | 校验点 |
|---|---|---|
| RIFF/WAVE magic | `RIFF`…`WAVE` `fmt ` `data` | 容器结构 |
| 格式标签 | 1（PCM） | 未压缩整数样本 |
| 声道 | 1（mono） | 与输入一致 |
| 采样率 | 44100 Hz | 与输入一致 |
| 位深 | 16-bit | madplay wave 默认 |
| PCM 字节 | 57600 | 25×1152×2 |
| 样本数 | 28800 = 25×1152 | **按编码帧数计算** |
| 文件大小 | 57644 = 44 + 57600 | 头 + 数据 |
| dither 容差 | max&#124;sample&#124; ≤ 2 | 实测直方图 {0:15161, ±1:9343, ±2:4296}，峰值 −84.3 dB |

**hex sink**（`madplay -o hex:out.hex`）: header 行 `# 1 channel, 44100 Hz, 24-bit samples`、28800 个样本、max&#124;sample&#124; ≤ 2（直方图 {0:17998, ±1:9002, ±2:1800}，24-bit 峰值 −132.5 dB）。跨运行 sha256 完全一致（out.wav ≡ out2.wav，out.hex ≡ out2.hex），证明解码输出确定性。

## 6. 通用处理算法

1. **确认默认路径依赖物理音频设备**：实际运行默认播放命令，记录 stderr 与退出码（madplay：`audio: /dev/dsp: No such file or directory`，exit 4，OSS 后端；`/dev/snd`、`audiodp` 存在但 Permission denied）。
2. **程序化生成最小、合法、确定、可审计的音频 fixture**：由编码帧头算术构造（如 MPEG-1 Layer III 全零 side info），不使用来源不明二进制样本。
3. **使用文件 sink 执行同一条真实解码路径**：`-o wave:FILE` / `-o hex:FILE`，让 demux→帧同步→requantize→synth→PCM 全链路真实运行。
4. **校验容器 magic、格式、声道、采样率、位深**：RIFF/WAVE/fmt/data、PCM=1、mono、44100 Hz、16-bit。
5. **按编码帧数计算预期 PCM 样本数**：25 帧 × 1152 样本/帧 = 28800，不允许 "输出文件存在" 替代。
6. **对 dither/rounding 使用有实测依据的有限容差**：|x| ≤ 2（依据:实测直方图全在 ±2 内，见第 5 节）。
7. **使用第二种输出形式交叉验证**：hex 输出与 wave 输出的样本数一致（28800 = 28800），参数一致（mono/44100），排除单一 sink 恰好掩盖解码错误的可能。
8. **增加不存在文件、截断或垃圾输入负向测试**：不存在文件 → exit 4 + `No such file or directory`（注意：音频设备错误先于文件打开发生，需加 `-T` 隔离真实退出码）；垃圾输入 → `error: frame 0: lost synchronization`、`0 frames decoded`、wave 产物仅 44 字节头（无 PCM payload）。
9. **失败时保留命令、输出、退出码和生成物诊断**：命令、完整 stdout/stderr、exit code、产物大小/哈希全部落盘到 logs/。
10. **不能把 `--help`、`--version` 或“输出文件存在”作为解码成功**。

## 7. fail-closed 安全边界

- 禁止跳过真实解码（只跑 -T 标签解析即宣告成功）
- 禁止伪造音频设备成功（如伪造 /dev/dsp 节点绕过失败）
- 禁止使用来源不明或许可不清的二进制 fixture
- 禁止只检查退出码
- 禁止只检查输出文件存在
- 禁止对带 dither 的静音输出机械要求逐样本全零
- 禁止吞掉负向测试错误（如 `|| true`、只断言 exit != 0 不看产物）
- 无法确认音频参数时必须失败并输出诊断

## 8. madplay 0.15.2b 完整实例

**环境**：HarmonyOS PC aarch64（本机即目标环境），madplay 二进制来自 Conan 缓存（MAD 0.16.4 / libid3tag 0.16.3，338368 字节）。

**Fixture 生成器**：`archives/m/madplay/0.15.2b/test_package/gen_fixture.c`（62 行，纯算术生成）。
**测试**：`test_package/test_madplay.py`（check_wave/check_hex_dump）、`test_package/conanfile.py`（FRAMES=25，7 项检查）。

**默认播放真实失败**（真实运行，非构造）：

```
$ madplay fixture.mp3
MPEG Audio Decoder 0.15.2 (beta) - Copyright (C) 2000-2004 Robert Leslie et al.
audio: /dev/dsp: No such file or directory
exit code: 4
```

**文件 sink 真实成功**：

```
$ madplay -o wave:out.wav fixture.mp3   → exit 0, 57644 bytes
$ madplay -o hex:out.hex  fixture.mp3   → exit 0, 22912 bytes
```

## 9. 验证命令与结果

```
gen_fixture fixture.mp3 25
madplay -o wave:out.wav fixture.mp3
madplay -o hex:out.hex fixture.mp3
python3 -c "import sys; sys.path.insert(0, 'archives/m/madplay/0.15.2b/test_package'); from test_madplay import check_wave, check_hex_dump; check_wave('out.wav', 25); check_hex_dump('out.hex', 25)"   # 全部断言通过（无输出即成功）
```

| 检查项 | 结果 |
|---|---|
| wave 大小 57644 = 44 + 25×1152×2 | ✅ |
| RIFF/WAVE/fmt/data magic | ✅ |
| PCM=1, mono, 44100 Hz, 16-bit | ✅ |
| PCM 样本数 28800 = 25×1152 | ✅ |
| wave dither max&#124;x&#124;≤2（histogram 全在 ±2） | ✅ |
| hex header `1 channel, 44100 Hz, 24-bit samples` | ✅ |
| hex 样本数 28800, max&#124;x&#124;≤2 | ✅ |
| 跨运行 sha256 一致（out.wav≡out2.wav, out.hex≡out2.hex） | ✅ |
| 官方 check_wave / check_hex_dump PASS | ✅ |
| 负向：不存在文件 exit 4 + No such file or directory | ✅ |
| 负向：垃圾输入 0 frames decoded + 44 字节 header-only wave | ✅ |

## 10. 与相似知识条目的区别

| 条目 | 相似点 | 区别（本条目新增） |
|---|---|---|
| E285（OpenAL 无声卡 Null/loopback） | 同为无声卡环境验证 | E285 是**库的后端裁剪+loopback API 验证**；本条目是 **CLI 程序 fixture 生成 + 文件 sink 解码验证**，不涉及后端配置，且加入帧数→样本数、dither 容差、双 sink 交叉验证 |
| E287（AFL/fuzz corpus 替代测试框架） | 同为替代验证素材 | E287 用上游 fuzz 语料做输入覆盖；本条目明确**拒绝来源不明语料**，要求算术生成、可逐位审计 |
| E472（SDL dummy drivers headless-run） | 同为 headless 运行可执行测试 | E472 解决**签名+运行**的 L0d 门禁；本条目解决**解码正确性验证**，产出 PCM 结构校验方法论 |

E285/E287/E472 均已在本地正式 graph 与 upstream/main（knowledge/graph/E285.kv、E287.kv、E472.kv）；逐条比对确认，现有条目均未覆盖「程序化生成确定性 fixture + 文件 sink 真实解码 + 帧数→样本数与 dither 容差校验」这一组合，E554 存在真实知识缺口。

## 11. libid3tag 制品仓 L0 阻塞不属于本知识问题的说明

当前线上 CI 因 libid3tag/0.16.3 制品仓查询失败停在 L0（`registry_unreachable` / `system acceleration policy not enabled`）。这是**基础设施错误**，与“无声卡环境下如何验证音频解码”是两个正交问题：

- L0 阻塞影响的是**依赖获取**，其修复途径是制品仓可用性，与本条目的验证方法论无关；
- 本条目知识来源是**本机（HarmonyOS PC aarch64）上的真实运行证据**，madplay 二进制来自本地 Conan 缓存，不依赖线上 CI；
- 因此 L0 错误未写入本条目的 error_signature、root_cause 或推荐方案；知识不因 CI 状态而成立或失效。

## 关联条目

- 相关: E285（无声卡音频库后端裁剪）、E287（fuzz corpus 替代验证）、E472（SDL dummy driver headless-run）——均已在本地正式 graph 与 upstream/main
