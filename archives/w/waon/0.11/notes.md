# waon 0.11 — HarmonyOS PC 适配笔记

任务：#11804（主活动「开源鸿蒙PC专项积分赛」）· 分支 `feat/waon-0.11` · 认领人 `iKalous_OscarP`

## 上游

- 仓库：https://github.com/kichiki/WaoN ，tag `v0.11`（版本号 0.11 与 tag 一一对应，未用 master 顶替）
- 源码：`https://codeload.github.com/kichiki/WaoN/tar.gz/refs/tags/v0.11`
  sha256 `75d5c1721632afee55a54bcbba1a444e53b03f4224b03da29317e98aa223c30b`
  （与 `github.com/.../archive/refs/tags/v0.11.tar.gz` 本地对拍同 sha256）
- 许可 GPL-2.0-or-later；C 语言，7 个 `.c`（main/notes/midi/analyse/fft/hc/snd），非自举工程（无 configure/CMake，只有手写 Makefile）

## 交付面

只交付 `waon`（离线 WAV→MIDI 转写器）。上游另外两个目标在本平台无法构建：

- `gwaon` 需要 GTK2、`pv` 需要 libao/jack，制品仓 0 命中；
- 取舍与 wildmidi 0.4.6 先例一致（关掉平台跑不起来的可选目标，交付可用子集）。

产物只有 `bin/waon`，无 lib/include，因此按 CLI 走 `commands.json`（软件级）。

## 依赖

| 依赖 | 版本 | 制品仓 |
|---|---|---|
| fftw | 3.3.11 | 已发布（拉二进制，未从源码构建） |
| libsndfile | 1.2.2 | 已发布（同上） |

## 补丁（1 个，patches/0001-…）

`patches/0001-makefile-waon-honor-environment-flags.patch`（portability，4 处最小改动）：

1. `CC = gcc` → `CC ?= gcc`：硬赋值会盖掉 conan 导出的交叉编译器；
2. `CFLAGS = \` → `CFLAGS ?= \`，并删掉 **x86 专属的 `-march=pentium`**（aarch64 clang 直接 `unknown argument`）；
3. `LDFLAGS= \` → `LDFLAGS ?= \`，并删掉 `-L/usr/local/lib`（宿主路径，OHOS 上不存在）；
4. 链接行 `$(CC) $(CFLAGS) -o waon $(OBJS) $(LDFLAGS)` → 追加 `$(LIBS)`。

第 4 点是本轮的真坑：conan 的 `AutotoolsDeps` 把依赖**库**放进 `LIBS`（实测
`-lsndfile -lfftw3 -lfftw3_threads -lm`），把 `-L` 放进 `LDFLAGS`，把 `-I` 放进 `CFLAGS`。
上游链接行不引用 `$(LIBS)`，于是编译全过、链接报一串 `undefined symbol: fftw_malloc / sf_open`。
设备侧生成的 `conanautotoolsdeps.sh` 原文可见：
`export LIBS="${LIBS:-}${LIBS:+ }-lsndfile -lfftw3 -lfftw3_threads -lm"`。

## 平台侧另两个坑（配方里已注释）

- `tools.files.get()` 在这台真机上失败：`ERROR: waon/0.11: Error in source() ... Unzip failed`
  （错误正文为空）。已排除「解压器坏了」：`unzip -qq/-o` 在 stdout 重定向和管道两种情形都
  rc=0（harmonybrew Info-ZIP 6.00），`bash -c 'tar x -f x.tar.gz -C out --no-same-owner'`
  也 rc=0（PATH 里的 tar 是 toybox 0.8.12）。具体触发点在 conan 的解压分支里，未定位。
  改成 `download()`（带 sha256 校验）+ python `tarfile` 解包，不依赖外部解压器，
  设备与 CI 走同一条路径；GitHub 归档多一层 `WaoN-0.11/` 目录，手工上移一层。
- `waon --help` / `--version` 打完就 `exit(1)`（`main.c` 里 `print_usage()/print_version()` 后固定退出）。
  这是上游既有行为，消费者测试按事实断言，不改上游。

## 真机验证（HarmonyOS PC，aarch64）

私有缓存 `CONAN_HOME=~/work/psj/ch-waon11804`，共享 `~/.conan2` 只读；配方按字节精确推送
（base64 + 两端 md5 对拍，10 个文件全等）。

```
conan create archives/w/waon/0.11 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

- `CREATE_EXIT:0`（2026-10-03 05:3x +08）
- 依赖二进制从 `ohpcd` 制品仓下载成功（fftw/3.3.11、libsndfile/1.2.2）
- 上游测试：**0/0**（上游无任何自动化测试，判据见 `test_package/MANIFEST.yml`）
- 消费者测试（鸿蒙特有）：**15/15，100%**，输出摘录：

```
[info] note-on=1 note-off=1 pitch range=[69,69]
15/15 checks passed
```

测试做法：`test_package/test_waon.c` 现场合成 440 Hz 单声道 PCM WAV（0.7 s，44 byte 头 +
数据长度自校验）与 440/660 Hz 立体声 WAV，调用**打包后的** `waon` 真机转 MIDI，
再逐字节解析 SMF（含 running status、meta 事件）断言：
MThd/MTrk 头、note-on/note-off 计数、A440→MIDI 音角落在 67..71（实测恰为 69）、
`--version` 横幅含 `WaoN` 与 `0.11`、缺输入文件必须以非零退出。

## 门禁自查
- L0a–L0e：`test_package/` 有 `.c` 源文件、`test()` 有 `self.run`、有 `MANIFEST.yml` ✔
- L0f：`patches` 用 list 格式 ✔
- L0j/R37：制品仓无 `waon/0.11`（领前 `precheck` 与认领后各查一次）✔
- L0k/R38：产物含 `bin/` → `archives/w/waon/commands.json`（type=tool、name=waon、versions 含 0.11）✔
- L0m/R39：目录 `archives/w/waon/0.11`，`name`/`version` 与目录一致 ✔
- L0n/R40：分支 `feat/waon-0.11`，与 taskBranch 逐字一致 ✔
- rule5：改动只在 `archives/w/waon/**` ✔

## 已知限制

- `pv` / `gwaon` 未交付（平台缺 libao/jack/GTK2 制品）。
- 分析参数全部沿用上游默认值即通过验证，未对复杂复调调参。
- 本品是离线文件转写：不需要网络、套接字或 FIFO，因此鸿蒙安全框架对
  `mkfifo(2)`、文件系统型 `AF_UNIX bind()` 的拦截以及只读的 `/tmp` 都不影响它。
