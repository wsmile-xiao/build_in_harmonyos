# playumidi

FreeBSD USB-MIDI（`umidi(4)` / `uaudio` 驱动）RAW-MIDI 设备 `/dev/umidi*.*` 的
**简易 MIDI 文件播放器**，支持 SMF（Standard MIDI File）format 0 / 1，
自动识别 XG/GS/GM 模式并可在文件缺少 Reset 码时自动补发。

- 上游：OSDN 项目 `playumidi`（作者 Koine Yuusuke / koinec）
- 许可证：2-clause BSD
- 产物：命令行工具 `bin/playumidi`（+ 手册页 `share/man/man1/playumidi.1.gz`）

## 用法

```bash
playumidi [option] MIDIfile(.mid)
  -d device_name      使用 /dev/[device_name]X.Y（X/Y 自动搜索）
  -0 device_fullname  指定 Port-0 设备节点全名（如 /dev/null）
  -r                  不自动追加 XG/GS/GM RESET 事件
  -q                  安静模式
  -v                  详细模式
  -h                  帮助
```

## OpenHarmony 适配说明

| 项 | 上游 | OHOS 现状 | 适配 |
|----|------|-----------|------|
| 构建系统 | BSD make（`.ifdef`/`.else`/`.endif`） | 仅 GNU make 4.4.1 | 补丁改写为 GNU make 语法，WITH_* 由 `-DWITH_X` 改为 `WITH_X=1` |
| 安装 | `install(1)` | 无 `install` 可执行文件 | `mkdir` + `cp` + `chmod` |
| 目录项长度 | `dirent.d_namlen`（BSD 专有） | musl 无 `d_namlen` | 改用 `strlen(d_name)`（语义等价，无平台宏） |
| 运行设备 | `/dev/umidi*.*` | 无 FreeBSD uaudio/umidi 设备 | MIDI 解析链与设备无关，可用 `-0 /dev/null` 完整验证 |

> 本工具的设备控制层面向 FreeBSD 专有设备节点；在 OHOS 上默认执行会以
> `Can't Open RawMidi Device ... Exit.` 结束（无设备时的预期行为）。
> MIDI 文件解析、事件生成/解码、时序调度等与平台无关的部分已在 OHOS 上实测通过
> （见 `0.8.3/notes.md` 验证结果）。
