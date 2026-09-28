# ttygif

把 [ttyrec](https://github.com/ttyrec/ttyrec) 终端录像回放成**动画 GIF** 的命令行工具。

## 是什么

ttygif 1.5.0 读取一个 ttyrec 录像文件，按录像里的时间戳逐帧回放到终端，
每帧用 `xwd -id $WINDOWID -out <scratch>/<n>.xwd` 抓一次终端窗口，
最后用 `convert -loop 0 -delay … <帧序列> -layers Optimize tty.gif`
把这些帧拼成动画 GIF 写到当前目录。

上游 <https://github.com/icholy/ttygif> 后来把该项目重写成了 Go；
**本归档的是 tag `1.5.0` 的 C 实现**（4 个 `.c` + 4 个头，实测 `.go` 文件数 0），
两者不是同一套代码，不要拿 Go 版的构建方式来套。

## 功能概述

- 逐帧回放 ttyrec 录像并保留原始帧间隔
- `-s/--speed <倍数>` 缩放回放速度（只作用于帧间隔，不作用于末帧停留时间）
- `-f/--fullscreen` 保留窗口边框（仅 Darwin 路径使用）
- `-h/--help`、`-v/--version` 打印用法与版本
- `TTYGIF_DEBUG=1` 只打印将要执行的抓帧/合成命令而不执行（上游自带的调试开关）
- 自动跳过停留时间过短的中间帧（`skip_limit` / `skip_threshold`）

## 运行依赖（外部命令）

ttygif 不参与链接任何第三方库，但**运行期**要 shell out 两个外部命令：

| 命令 | 用途 | 本平台可得性 |
|---|---|---|
| `convert`（ImageMagick） | 把抓到的帧合成动画 GIF | Conan 依赖 `imagemagick/7.1.2.29`（`run=True`）已提供 |
| `xwd`（X11 应用） | 逐帧抓取终端窗口 | **本仓尚无可用的 conan 包**（见下） |

关于 `xwd`：`archives/x/xwd/1.0.9/` 只落了 `manifest.yaml`/`notes.md`/`patches/`，
**没有 `conanfile.py`**，制品仓里也取不到（`conan download xwd --only-recipe -r=ohpcd`
→ `Recipe 'xwd' not found`）。按 R36/PF4「依赖必须先发布、不得在配方 PR 里捎带适配依赖」，
本包不把它写成 conan 依赖，而是如实声明为**外部命令依赖**：抓屏那半边要能跑，
需要宿主提供 `xwd` 以及一个活的 X display（`DISPLAY` + 真实 `WINDOWID`）。

关于 `convert` 的可达性：已发布的 `imagemagick` 配方只声明了 components、
没有 `cpp_info.bindirs`，因此即便 `run=True`，Conan 的 `VirtualRunEnv` 也不会把它的
`bin/` 注入 `PATH`（本任务实测：`conan install --requires=imagemagick/7.1.2.29
-g VirtualRunEnv` 生成的 `conanrun.sh` 里只有 libpng 的 bindir）。
所以消费者在 PATH 里要能拿到 `convert`（例如直接引用
`<imagemagick package_folder>/bin/convert`），否则 ttygif 会在合成阶段失败。

## OHOS 适配要点

1. **`/tmp` 只读**：上游在 `main()` 最开头无条件 `mkdtemp("/tmp/ttygif.XXXXXX")`，
   鸿蒙 PC 上这一步必失败（`touch /tmp/x` → `Read-only file system`），
   于是**任何调用都在处理命令行参数之前就退出**，连 `ttygif --version` 都返回非零。
   `patches/0001` 让暂存目录优先取 `TMPDIR`（知识条目 E002 给的正解），
   `TMPDIR` 未设置时仍回落 `/tmp`，Linux/macOS 行为不变。
2. **无头环境取不到版本号**：`-h`/`-v` 的判定原本排在 `WINDOWID` 检查之后，
   没有 X 窗口就连用法/版本都打印不出来。`patches/0001` 把这一段提到所有
   显示相关初始化之前，CI 的 L2 冒烟探针因此有稳定读数。
3. **版本自述与 tag 不一致**：tag `1.5.0` 的 Makefile 里仍写 `VERSION = '"1.4.0"'`，
   `ttygif -v` 打印的是这个宏。`patches/0002` 对齐到 `1.5.0`。
4. **裸 Makefile 的变量语义**：`CC = gcc` 是裸赋值 ⇒ 环境变量 `CC` 被吞，
   只有 `make CC=…` 命令行赋值能覆盖；`CFLAGS += …` ⇒ 一旦命令行给 `CFLAGS`
   就整体丢弃（连带丢 `-DVERSION`）。配方只覆盖 `CC`，编译器路径取自
   Conan conf（R33）。
5. **不用 `make install`**：它把默认 PREFIX 烧进安装规则，且 `install -m755`
   依赖的 chmod 语义在 HMDFS 上会被归一化掉（E046，M18「烧路径」家族），
   `package()` 直接 copy 产物。
6. **已排除的假线索**：Makefile 用 `UNAME := $(shell uname)` 且只对
   `Darwin`/`Linux` 两个取值加宏，本机 `uname` 返回 `HarmonyOS` ⇒
   `-DOS_DARWIN`/`-DOS_LINUX` 都不定义。看起来像平台不兼容，实测
   **全树 `OS_LINUX` 引用次数为 0**、只有 3 处 `#ifdef OS_DARWIN`，
   默认编译路径就是 Linux 行为。不要为此打补丁、不要加 `-DOS_LINUX`
   "对齐"、更不要据此判"无法适配"。

## 依赖关系

- 链接期：无（纯 C + libc）
- 构建期：clang（Conan conf 注入）、GNU make
- Conan 依赖：`imagemagick/7.1.2.29`（`headers=False, libs=False, run=True`，运行期工具）
- 外部命令：`xwd`（抓帧，本平台无 conan 包）、`convert`（合成 GIF）

## 验证

见 `1.5.0/reports/`：

- `test-report.md` —— 五维测试账本（上游清点 / 构建 / 执行 / 未执行项 / 消费者）
- `upstream-test-scan.txt` —— 上游测试手工等价清点证据（框架自带的
  `ci/tools/extract_upstream_tests.sh` 硬编码只读的 `/tmp`，本平台跑不动）
- `w3-local-ci.log`、`conan-verify.log` —— 本地门禁真日志

## 参考资料

- 上游仓库：<https://github.com/icholy/ttygif>
- 源码归档：<https://codeload.github.com/icholy/ttygif/tar.gz/refs/tags/1.5.0>
  （tag 不带 `v` 前缀；`refs/tags/v1.5.0` 实测 404）
- ttyrec 格式：`ttyrec.h` 中 `struct header { struct timeval tv; int len; }`，
  小端 3×int32 头 + `len` 字节负载
- 许可证：`LICENSE` 为 MIT；`io.c`/`ttygif.c` 另带 ttyrec 的 BSD-4-Clause
  版权头（含广告条款），再分发时需注意
