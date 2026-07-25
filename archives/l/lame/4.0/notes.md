# lame 4.0 编译笔记（HarmonyOS PC · 原生 conan create）

## 定位

LAME MP3 编码器，LGPL-2.0-or-later。提供 `libmp3lame`（供 FFmpeg `--enable-libmp3lame`
做 MP3 **编码**；MP3 解码 FFmpeg 自带）与 `bin/lame` 命令行工具。

## 与已有 lame/3.100 的关系

本仓已有 `archives/l/lame/3.100`（MR !3244 合入）。本版是**版本升级**，两点差异：

| | 3.100 | 4.0（本版） |
|---|---|---|
| 上游发布 | 2017 | 更新的正式版（SourceForge `lame/4.0/`） |
| frontend | `--disable-frontend`，只出库 | 保留，另出 `bin/lame` CLI（已配套软件级 `commands.json`，R38） |
| 三元组 | gnu 三元组 + uname-shim | musl 三元组（贴合设备真实 libc） |

若只需要 FFmpeg 的编码能力，3.100 已足够；本版的增量是更新的上游代码与可用的命令行工具。

## 关键适配

### 1. `--disable-decoder`：LAME 4.0 起 libmpg123 变成默认必需

4.0 把「external mpg123 解码器」改成默认开启，缺 libmpg123 时 configure **直接中止**
（`configure` 里 `as_fn_error $? "no, libmpg123 not found"`）——3.100 没有这个行为。

本包定位是提供 **MP3 编码**（FFmpeg 自带 MP3 解码器），故 `--disable-decoder` 关掉该路径，
避免为此再引入一个 libmpg123 依赖。代价：`bin/lame` 的解码（`--decode`）功能不可用。

### 2. 显式 `--build` / `--host` 用 musl 三元组

设备默认 TMPDIR 在 HMDFS 上，`config.guess` 的 mktemp 子目录里新建 `.c` 会 `Permission denied`
→ `cannot guess system type`。给出显式 `aarch64-unknown-linux-musl` 三元组即跳过 config.guess；
`build == host` 让 configure 走原生路径（运行期探针可用）而非 cross 模式。

### 3. `--disable-gtktest`

上游会探测 GTK（用于可选的 `mp3x` 分析器 GUI），设备无 GTK，显式关闭避免无谓探测告警。

## 真机验证结果（2026-07-25，设备 3QC0124C11000718）

裸 `conan create . -pr ohos-native` **rc=0，75s**，包体积 974K。

- `lib/libmp3lame.so.0`，SONAME `libmp3lame.so.0`，DT_NEEDED 仅 `libc.so`
- `.codesign` 段存在
- `include/lame/lame.h`、`bin/lame` 齐全

### test_package（真实 MP3 编码，非仅版本查询）

`lame_init` → `lame_set_in_samplerate(44100)` / `set_num_channels(2)` / `set_brate(128)`
→ `lame_init_params` → `lame_encode_buffer`（1152 样本非均匀立体声 PCM）→ `lame_encode_flush`：

```
lame: version=4.0  encode=417 bytes  flush=835 bytes  OK
```

断言：`lame_init_params` 返回 >= 0；编码与 flush 均非负且总字节数 > 0。
测试直接链 `-lmp3lame`（非 dlopen），故 CI 的 L1e 破坏性反向验证（移走 lib/ 与 include/）
会在编译/链接期失败，反向依赖成立。

## 状态

built —— 真机 `conan create` + 真实 MP3 编码 test_package 全绿。
