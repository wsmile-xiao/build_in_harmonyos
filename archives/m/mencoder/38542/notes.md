# mencoder 38542 适配笔记

## 源码来源

- **官方仓库**: `svn://svn.mplayerhq.hu/mplayer/trunk`（MPlayer 官方 SVN）
- **固定 revision**: `38542`（2024-08-12）
- **实际下载源**: `https://snapshot-cloudflare.debian.org/archive/debian/20240606T144219Z/pool/main/m/mplayer/mplayer_1.5+svn38542.orig.tar.xz`
  - 该端点与 `snapshot.debian.org` 同源同字节（Debian snapshot 服务的 Cloudflare CDN 前端，实测两者 sha256 一致：`464977a1…f2ae`）。首轮 PR CI（#48173）从源站 `snapshot.debian.org` 直连下载在超时预算内失败（CI 归类：网络问题/源码下载超时），故改用 CDN 端点——路径、内容、sha256 完全不变，仅分发通道变化。
  - 该文件是 Debian 官方归档中的 **pristine orig tarball**：内容即 `svn export -r 38542 svn://svn.mplayerhq.hu/mplayer/trunk` 的原始导出物（单根目录 `mplayer-1.5+svn38542/`，**不含** `debian/` 打包目录、**不含**任何发行版补丁）。
  - SHA256 固定：`464977a109321c4d9c6e8c7f6281f1b0756551f85e3e4f808c9bee45d266f2ae`（与配方 `conandata.yml` 一致）。
  - 配方在 `source()` 中直接 `get()` 下载并解包，构建全程由 HTTP 归档驱动，可离线复现（源码已落盘缓存）。
- **未使用 `svn://` 直连的原因**: CI 执行环境不提供 `svn` 客户端（实测 `sh: svn: inaccessible or not found`），`svn export` 方案在 CI 不可复现（会直接构建失败）。改用同一 revision 的 Debian 归档原始导出物，源码内容与 `svn export -r 38542` 等价且来源权威（Debian 官方归档）。
- **FFmpeg 依赖**: 官方 `ffmpeg-6.1.6.tar.xz`（SHA256 `d4fcb164028dd3beee5d92c0ac72e46aac6973c75ea12dc14de07bf8f407370a`）

## 编译环境
- 构建系统: 自定义 configure + Makefile（in-tree）
- 编译日期: 2026-09-15
- 编译器: HarmonyOS aarch64 clang（OHOS SDK，交叉编译）
- 状态: built

## 编译步骤
1. 下载并解包 r38542 pristine 上游源码（SHA256 校验）与官方 FFmpeg 6.1.6 源码。
2. FFmpeg 采用 `--disable-autodetect --disable-everything` + 按需 `--enable-*` 配置，避免网络对象在 MEncoder 禁用网络时参与链接。
3. MEncoder 使用 `./configure --disable-mplayer --disable-gui --disable-x11 --disable-networking` 等无图形、无网络选项配置。
4. `make` 完成 aarch64 HarmonyOS 构建。
5. **构建期执行上游测试**（见下）。

## 上游测试

上游 `Makefile` 的 `tests` 目标 = `codecs2html`、`codec-cfg-test`、`libvo/aspecttest` 三个固定测试程序（`QTX_EMULATION` 启用时另含 `loader/qtx/list`、`loader/qtx/qtxload` 两个条件项；`fatetest` 是独立目标，不属于 `tests`）。按本包范围（`--disable-mplayer`，只构建 MEncoder）判定如下：

| 上游测试 | 处理 | 说明 |
|---------|------|------|
| `codec-cfg-test`（`codec-cfg.c`，`-DTESTING`） | ✅ 执行 | `make codec-cfg-test && ./codec-cfg-test`；解析校验 `codecs.conf`（226 audio + 468 video），退出码 0 |
| `codecs2html`（`codecs2html.c`） | ✅ 执行 | `make codecs2html && ./codecs2html`；输出 codec 矩阵，退出码 0 |
| `libvo/aspecttest` | ❌ 不适用 | 覆盖 mplayer 二进制专用视频输出子系统 `libvo`；本配置不构建 `libvo`，`mencoder` 二进制中无 `aspect_*` / `vo_rotate` 符号 |
| `make fatetest`（FATE） | ❌ 不适用 | 需 `mplayer` 二进制 + 外部 `FATE_SAMPLES` 样本集（数 GB），回归对象为播放路径 |

- 两个适用测试均在 `conanfile.py` 的 `build()` 中**真实编译并执行**（非空壳调用、非打印字符串），非 0 退出即判定构建失败。
- 声明（含不适用项及原因）见 `test_package/MANIFEST.yml`。
- **未修改上游任何测试源码**。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 内嵌 FFmpeg master 与 r38542 不兼容 | `AVCodec.sample_fmts` 等旧 API 在 FFmpeg 新主线已删除 | 固定使用已发布且可获取的 FFmpeg 6.1.6 |
| 2 | 链接出现 FFmpeg 网络符号未定义 | MEncoder 禁用网络但旧 FFmpeg `libavformat.a` 仍残留网络对象 | 清理旧 FFmpeg 组件并单独配置 `--disable-network` 后重建 |
| 3 | Conan `self.run` 环境参数报错 | Conan 2.29 要求 `env` 使用列表格式 | 使用 `env=["CC=...", "CXX=...", ...]` |
| 4 | `svn export` 方案在 CI 不可复现 | CI 环境无 `svn` 客户端 | 改用同一 revision 的 Debian 官方归档 pristine 导出物（HTTP + SHA256 固定） |
| 5 | 消费者测试脚本 `test_package/test.sh` 未被 `test()` 调用 | `test_package/conanfile.py` 的 `test()` 未引用该脚本 | 在 `test()` 中显式执行 `bash test.sh` 与 `bash test_ohos.sh` |

## 源码修改

无平台宏补丁（`patches/` 为空）。Conan 配方在构建阶段固定 FFmpeg 版本并禁用无关功能。

## 依赖版本

- ffmpeg/6.1.6（源码依赖，官方源）

## 验证结果

```text
make codec-cfg-test codecs2html         PASS（上游测试编译）
./codec-cfg-test                        PASS（上游测试，退出码 0；226 audio + 468 video codecs）
./codecs2html                           PASS（上游测试，退出码 0）
消费者测试 test_package/test.sh          PASS（选项解析与 lavc 可用性 + I420→MPEG-4 AVI 真实编码）
鸿蒙特有测试 test_package/test_ohos.sh    PASS（AArch64 ABI + .note.ohos.ident + musl 加载器 + 无 glibc 依赖 + 实际运行，5/5）
conan create（W3 本地 CI 模拟）           PASS
```

## 注意事项

- MEncoder r38542 的版本输出为 `UNKNOWN-15.0.4`，这是上游版本字符串机制在无 SVN 元数据源码树中的表现（构建期通过 `svn info` 探测 SVN 修订号失败所致），不影响可执行文件及功能。
- 该包仅交付 MEncoder 命令行工具，不启用 MPlayer、GUI、X11 和网络功能。

## 对话记录

### 对话 #1（2026-09-15）：PR 审核意见修复（P1/P3）

| 审核意见 | 等级 | 处理 |
|---------|------|------|
| 源码 URL 指向发行版再打包源码，不可复现、不符合 R39 | Critical (P1) | 已改为 **r38542 pristine 上游源码**：发行版官方归档的 orig tarball（`svn export -r 38542` 的原始导出物，不含打包目录与补丁），URL + SHA256 固定，`source()` 直接下载解包；弃用原 Parabola 再打包源码 |
| `test_package/test.c` 仅执行 `-ovc help`，未验证真实编码能力 | High (P3) | 已补全：① 构建期执行上游 `tests` 目标中适用的 2 个测试程序（`codec-cfg-test`、`codecs2html`，真实编译执行）；② 新增消费者功能测试 `test_package/test.sh`（选项解析 + I420→MPEG-4 AVI 真实编码链路）；③ 新增鸿蒙平台一致性测试 `test_package/test_ohos.sh`（5 项）；并修复 `test.sh` 未被 `test()` 调用的缺陷 |

- 验证：`conan create`（W3 本地 CI 模拟）通过，L0/L1/L4/L5 全绿；上游测试 2/2、新增测试 3/3 全部通过。

### 对话 #2（2026-09-15）：CI 第 1 轮失败修复（llvm-readelf 早退管道）

| 现象 | 根因 | 处理 |
|------|------|------|
| CI #48186 中 `test_ohos.sh` 以退出码 74 失败，stderr 仅一行 `error: write on a pipe with no reader` | CI 侧 `readelf` 解析到 **LLVM 实现**（HNP 环境同时提供 `llvm-readelf`，在测试环境 PATH 中遮蔽 GNU binutils）：`readelf ... \| grep -q PATTERN` 中 `grep -q` 命中后立即退出并关闭读端，LLVM readelf 继续写剩余输出时遇 EPIPE，报该消息并以 74（EX_IOERR）退出。本地为 GNU binutils readelf，静默忽略 EPIPE，故本地 W3 通过而 CI 失败 | `test_package/test_ohos.sh` 改为**输出先落盘再匹配**（`readelf ... > file` + `grep -q PAT file`），脚本内不再存在 `readelf \| grep` 早退管道；各检查补显式失败信息；第 5 项追加断言 `-ovc help` 输出含真实编码后端 `lavc` |

- 复现命令（本地，确认根因）：`llvm-readelf -sW <mencoder> 2>err.txt | grep -q UND` → 管道 `rc=74`，`err.txt` 首行即 `error: write on a pipe with no reader`。
- CI 判读提示：该轮 CI 摘要把失败归类为"源码下载超时"，与日志不符——日志显示源码已下载、构建与 `test.sh` 均通过，真正失败点是 `test_ohos.sh`；修复后重跑验证。
---

**编译结束**: 2026-09-15 19:07
**最终状态**: built
