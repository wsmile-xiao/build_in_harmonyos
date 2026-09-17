- **三方库名称**：mencoder（MPlayer 的命令行视频编码器 MEncoder）
- **上游版本**：r38542（MPlayer SVN trunk 固定 revision，发行版版本号 1.5+svn38542）
- **上游仓库地址**：https://www.mplayerhq.hu/ （SVN: svn://svn.mplayerhq.hu/mplayer/trunk，rev 38542）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 1 | 上游 `Makefile` 的 `tests` 目标含 `codec-cfg-test`（由 `codec-cfg.c` 以 `-DTESTING` 构建），解析并校验 `codecs.conf` 全部条目（468 video + 226 audio），解析失败即非 0 退出 |
| 集成测试 | 1 | 上游 `Makefile` 的 `tests` 目标含 `codecs2html`（`codecs2html.c`），经 codec-cfg 解析器读取 `codecs.conf` 并渲染为 HTML 编解码器矩阵 |
| 其他测试 | 2 | 上游 `tests` 目标另含 `libvo/aspecttest`（覆盖 mplayer 视频输出子系统 libvo）与 `make fatetest`（FATE 回归套件）。二者均不适用于本包，详见下方"上游测试用例修改说明" |
| **合计** | **4** | 其中**适用并被执行 2 个**（unit 1 + integration 1），其余 2 个非本包适用范围 |

### 是否存在对上游测试用例的修改？

否

如果存在修改，请说明修改内容及原因：

未修改任何上游测试用例源码。上游 `tests` 目标中 2 个不适用于本包的程序，系在构建期**不选取**（而非改动其源码）：

| 上游测试程序 | 不选取原因 |
|-------------|-----------|
| `libvo/aspecttest` | 覆盖 mplayer 二进制专用的视频输出子系统 `libvo`。本配方以 `--disable-mplayer` 只构建 MEncoder，`libvo` 不参与构建与链接——产出的 `mencoder` 二进制中不含 `aspect_*` / `vo_rotate` 符号，该测试程序在本配置下无被测对象 |
| `make fatetest`（FATE） | 需要 `mplayer` 二进制与外部 `FATE_SAMPLES` 样本集（网络下载数 GB 素材），且回归对象为 mplayer 播放路径；本配方只构建 MEncoder |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试（上游） | 1 | 一致 | 保留上游 `codec-cfg-test`，构建期编译并实际执行，非 0 退出即判定失败 |
| 集成测试（上游） | 1 | 一致 | 保留上游 `codecs2html`，构建期编译并实际执行 |
| 集成测试（消费者，新增） | 2 | +2 | `test_package/test.sh`：① MEncoder 选项解析与 `lavc` 编解码器可用性；② 真实编码链路（原始 I420 帧 → MPEG-4 AVI 输出） |
| 鸿蒙特有测试（新增） | 1 | +1 | `test_package/test_ohos.sh`：OHOS 平台一致性（AArch64 ABI、`.note.ohos.ident`、musl 加载器、无 glibc 依赖、实际运行） |
| **合计** | **5** | **+3** | 上游适用用例 2 个全部保留并执行；新增 3 个消费者/平台测试用例 |

---

## 上游测试用例修改说明

**未修改上游测试用例**（0 个修改 / 0 个删除）。上游 `tests` 目标（= `codecs2html`、`codec-cfg-test`、`libvo/aspecttest` 三个固定程序，`QTX_EMULATION` 启用时另含 `loader/qtx/*` 两个条件项）中，2 个适用项（`codec-cfg-test`、`codecs2html`）保留并在 `conanfile.py` 的 `build()` 中编译执行；1 个（`libvo/aspecttest`）因不属于本包构建范围（`--disable-mplayer`，不构建 `libvo` 视频输出子系统）不选取；独立目标 `make fatetest`（FATE）需 `mplayer` 二进制与外部数 GB 样本集，同样不适用。以上均未改动其源码。

执行方式（`conanfile.py` `build()` 内）：

```bash
make -j<N> codec-cfg-test codecs2html
./codec-cfg-test    # 解析 codecs.conf：468 video + 226 audio codecs，退出码 0
./codecs2html       # codecs.conf → HTML 矩阵，退出码 0
```

## 补全测试用例说明

上游测试在**构建树内**运行，只验证 `codecs.conf` 解析逻辑，不验证 conan 包**安装后**在目标平台上的实际可用性。因此补全以下测试用例（新增 2 个文件、3 个用例）：

### 1. 消费者功能集成测试 — `test_package/test.sh`（新增 2 个用例）

| 用例 | 覆盖场景 | 验证目标 |
|------|---------|---------|
| 用例 1：选项解析与编解码器可用性 | 消费者视角的 CLI 契约 | `mencoder -ovc help` 退出码 0，输出包含 `Available codecs:` 与 `lavc - libavcodec codecs - best quality!`，证明安装后的二进制可执行且 lavc 编解码器已编入 |
| 用例 2：真实编码链路 | 端到端编码功能（不止 CLI 打印） | 生成 16×16 原始 I420 帧，`mencoder -ovc lavc -lavcopts vcodec=mpeg4 ...` 编码为 AVI，断言输出文件非空（真实走完 demux→编码→mux 链路） |

### 2. 鸿蒙特有测试 — `test_package/test_ohos.sh`（新增 1 个用例）

针对 HarmonyOS PC（arm64）平台一致性，5 项检查：

| # | 检查项 | 断言 |
|---|-------|------|
| 1 | ABI | `readelf -h` 机器类型为 AArch64 |
| 2 | OHOS 二进制标识 | 存在链接器写入的 `.note.ohos.ident` 段（glibc/Linux 构建无此段） |
| 3 | 运行时加载器 | `PT_INTERP` 为 `ld-musl-aarch64.so.1`（OHOS musl，而非 glibc 的 `ld-linux-aarch64.so.1`） |
| 4 | 无 glibc 污染 | `DT_NEEDED` 中不含 `libc.so.6` / `ld-linux` |
| 5 | 实际运行 | 经内核 `.interp` 以 OHOS musl 加载器启动进程并成功退出（证明加载器与动态依赖在运行时确实可解析） |

> 该测试为鸿蒙平台特有：桌面 Linux/glibc 构建必然在第 2、3、4 项失败，无法通过。

## 验证结果

### 编译验证

- 编译环境：HarmonyOS PC worker（aarch64-linux-ohos，OHOS SDK clang 交叉编译），Conan 2.x `conan create`，profile `ci/conan/profiles/ohos-aarch64`
- 编译命令：`conan create . --version=38542`（等价 CI `ci/conan/build_and_test.sh`）
- 编译结果：**通过**（含上游测试程序编译与执行、test_package 消费者测试）

### 测试通过率

| 测试用例 | 类型 | 结果 |
|---------|------|------|
| `codec-cfg-test`（上游） | 单元测试 | 通过（退出码 0，解析 468 video + 226 audio codecs） |
| `codecs2html`（上游） | 集成测试 | 通过（退出码 0） |
| `test.sh` 用例 1：选项解析与 lavc 可用性（新增） | 集成测试 | 通过 |
| `test.sh` 用例 2：I420 → MPEG-4 AVI 真实编码（新增） | 集成测试 | 通过（输出 AVI 非空） |
| `test_ohos.sh`：OHOS 平台一致性 5 项（新增） | 鸿蒙特有测试 | 通过 |
| **合计** | | **5/5 通过（100%）** |

上游适用测试用例通过率：2/2（100%）；补全测试用例通过率：3/3（100%）。

### CI 实测（PR 校验流水线）

| 轮次 | 结果 | 定位与处理 |
|------|------|-----------|
| 第 1 轮 | FAILED | 流水线摘要归类为"源码下载超时"，但逐行日志显示：源码下载、`conan create`、上游测试与 `test.sh` **均已通过**，真正失败点是 `test_ohos.sh` 以退出码 74 退出（stderr `error: write on a pipe with no reader`）。根因：CI 侧 `readelf` 解析为 **LLVM 实现**（`llvm-readelf`），而脚本使用 `readelf ... \| grep -q PATTERN`——`grep -q` 命中后立即退出并关闭读端，LLVM readelf 继续写剩余输出时遇 EPIPE，报该消息并以 74（EX_IOERR）退出；本地为 GNU binutils readelf，静默忽略 EPIPE，故本地 W3 通过而 CI 失败。已本地复现（`llvm-readelf -sW <bin> 2>err \| grep -q UND` → rc=74 + 同一消息） | 已改为**输出先落盘再匹配**（`readelf ... > file` + `grep -q PAT file`），脚本内不再存在早退管道，并为每项检查补充显式失败信息 |

## 补充说明

1. **源码可追溯性（对应审核意见 P1）**：源码已从发行版再打包源码切换为 **r38542 固定 revision 的 pristine 上游源码**——`mplayer_1.5+svn38542.orig.tar.xz`（Debian 官方归档，即 `svn export -r 38542 svn://svn.mplayerhq.hu/mplayer/trunk` 的原始导出物），`conandata.yml` 中 URL 与 SHA256 均已固定；下载与解包在 `conanfile.py` 的 `source()` 中完成，构建完全由 HTTP 归档驱动。下载端点为 Debian snapshot 服务的 **Cloudflare CDN 前端**（`snapshot-cloudflare.debian.org`，与 `snapshot.debian.org` 同源同字节，sha256 一致）——首轮 PR CI（#48173）流水线摘要归类为"网络问题/源码下载超时"（该轮失败点未经逐行日志确认），改用 CDN 端点后路径、内容、sha256 均不变，且下载更快；本地 `conan create` 已实测从该端点下载并校验通过。
   - 未直接使用 `svn://` 拉取的原因：CI 执行环境不提供 `svn` 客户端（`sh: svn: inaccessible or not found`），SVN 方案在 CI 不可复现，故改用同一 revision 的权威归档。
2. **上游测试纳入构建期（对应审核意见 P3）**：此前配方未执行上游测试；现已在 `build()` 中编译并执行上游 `tests` 目标中适用于本包的程序（`codec-cfg-test`、`codecs2html`），并在 `test_package/MANIFEST.yml` 中声明上游测试来源与不适用项及原因。上游测试为**真实编译执行**，非空壳调用。
3. **已知限制（R40 深度适配人工确认）**：MEncoder 为命令行编码工具，不涉及图形渲染/UI 框架/系统底层驱动的深度适配，本配方仅做平台可编译与可运行性适配（`--disable-mplayer`、静态系统同名库、OHOS 交叉编译三元组）；未对其多媒体编解码性能与硬件加速路径做人工确认，如需可另行专门评估。
