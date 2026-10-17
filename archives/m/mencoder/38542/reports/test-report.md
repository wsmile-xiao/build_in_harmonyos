# mencoder 38542 测试报告

## 一、编译验证

| 项 | 内容 |
|----|------|
| 目标平台 | HarmonyOS PC / aarch64-linux-ohos |
| 工具链 | OHOS SDK clang（交叉编译），`ci/conan/profiles/ohos-aarch64` |
| 构建系统 | 上游 `configure` + `make`（in-tree），`--disable-mplayer` 仅构建 MEncoder |
| 配方 | `archives/m/mencoder/38542/conanfile.py` |
| 源码 | r38542 pristine 上游源码（`mplayer_1.5+svn38542.orig.tar.xz`，SHA256 固定；下载端点 = Debian snapshot 的 Cloudflare CDN 前端 `snapshot-cloudflare.debian.org`，与源站同字节，实测 sha256 `464977a1…f2ae` 一致） |
| 本地 CI（W3） | `conan create . --version=38542`（等价 `ci/conan/build_and_test.sh`）：**通过** |
| 产物 | `bin/mencoder`、`share/man/man1/mencoder.1` |

## 二、上游测试用例（全部保留并执行）

上游 `Makefile` 的 `tests` 目标 = `codecs2html`、`codec-cfg-test`、`libvo/aspecttest` 三个固定测试程序（`QTX_EMULATION` 启用时另含 `loader/qtx/*` 两个条件项；`fatetest` 为独立目标，不属于 `tests`）。按本包构建范围（`--disable-mplayer`、只构建 MEncoder）判定如下：

| # | 上游测试程序 | 类型 | 适用性 | 执行结果 |
|---|-------------|------|--------|---------|
| 1 | `codec-cfg-test`（`codec-cfg.c`，`-DTESTING`） | 单元测试 | ✅ 适用 | **通过**（退出码 0；解析 `codecs.conf`：226 audio + 468 video codecs） |
| 2 | `codecs2html`（`codecs2html.c`） | 集成测试 | ✅ 适用 | **通过**（退出码 0；输出 `Reading optional codecs config file etc/codecs.conf: 226 audio & 468 video codecs`） |
| 3 | `libvo/aspecttest` | 单元测试 | ❌ 不适用 | 覆盖 mplayer 二进制专用视频输出子系统 `libvo`；本配方 `--disable-mplayer` 不构建 `libvo`，产出二进制中无 `aspect_*` / `vo_rotate` 符号 |
| 4 | `make fatetest`（FATE） | 回归套件 | ❌ 不适用 | 需 `mplayer` 二进制与外部 `FATE_SAMPLES` 样本集（数 GB 素材），回归对象为播放路径 |

**上游适用测试用例通过率：2/2（100%）**。二者均在 `conanfile.py` 的 `build()` 中**真实编译并执行**（非空壳调用、非打印字符串），非 0 退出即判定构建失败；声明见 `test_package/MANIFEST.yml`。

未选用测试程序 #3/#4 的原因已在上表与 `MANIFEST.yml` 中记录，**未修改上游任何测试源码**。

## 三、消费者测试用例（新增，3 个）

上游测试运行在构建树内，只验证 `codecs.conf` 解析逻辑，不覆盖 conan 包安装后在目标平台上的实际可用性。因此新增消费者视角测试：

### 3.1 `test_package/test.sh` — 消费者功能测试（2 个用例）

| 用例 | 命令 | 断言 | 结果 |
|------|------|------|------|
| 用例 1：选项解析与 lavc 可用性 | `mencoder -ovc help` | 退出码 0；输出含 `Available codecs:`；输出含 `lavc - libavcodec codecs - best quality!` | 通过 |
| 用例 2：真实编码链路 | `mencoder -ovc lavc -lavcopts vcodec=mpeg4 ... -o output.avi` | 由 16×16 原始 I420 帧生成 AVI 且文件非空（`-s` 通过），真实走完 demux→编码→mux 链路 | 通过（输出 AVI 非空） |

### 3.2 `test_package/test_ohos.sh` — 鸿蒙特有测试（1 个用例，5 项检查）

| # | 检查项 | 断言 | 结果 |
|---|-------|------|------|
| 1 | ABI | `readelf -h` 机器类型 = AArch64 | 通过 |
| 2 | OHOS 二进制标识 | 存在 `.note.ohos.ident` 段（OHOS 链接器写入；glibc/Linux 构建无此段） | 通过 |
| 3 | 运行时加载器 | `PT_INTERP` = `ld-musl-aarch64.so.1`（OHOS musl，而非 `ld-linux-aarch64.so.1`） | 通过 |
| 4 | 无 glibc 污染 | `DT_NEEDED` 不含 `libc.so.6` / `ld-linux` | 通过 |
| 5 | 实际运行 | 经内核 `.interp` 由 OHOS musl 加载器启动进程并成功退出 | 通过 |

> 第 2/3/4 项为鸿蒙平台特有：桌面 Linux（glibc）构建必然失败，故该用例无法被非 OHOS 平台伪造。

## 四、汇总

| 分类 | 用例数 | 通过 | 失败 | 通过率 |
|------|-------|------|------|-------|
| 上游单元测试 | 1 | 1 | 0 | 100% |
| 上游集成测试 | 1 | 1 | 0 | 100% |
| 消费者功能测试（新增） | 2 | 2 | 0 | 100% |
| 鸿蒙特有测试（新增） | 1 | 1 | 0 | 100% |
| **合计** | **5** | **5** | **0** | **100%** |

- 上游测试用例：适用 2 个，改动 0 个，删除 0 个。
- 新增测试用例：3 个（2 个消费者功能 + 1 个鸿蒙平台一致性）。
- 断言总数：8（`test.sh` 3 + `test_ohos.sh` 5，见 `test_package/MANIFEST.yml`）。

## 五、已知限制

1. **R40 深度适配人工确认**：MEncoder 为命令行编码工具，不含图形渲染/UI 框架/系统底层驱动适配；本配方仅做平台可编译与可运行性适配。未对硬件加速（`--enable-*_hwaccel`）路径与编解码性能做人工确认。
2. 上游 `libvo/aspecttest` 与 FATE 未纳入（原因见第二节），如需覆盖需另行立项构建 mplayer 播放器主体。
3. 第 5 项运行检查为冒烟级：验证进程可启动并成功退出，不做长时编码/性能基准。

## 六、CI 实测（PR #10031）

| 轮次 | CI 结果 | 失败点 | 处理 |
|------|---------|--------|------|
| 第 1 轮 | #48186 FAILED | `test_ohos.sh` 退出码 74，stderr `error: write on a pipe with no reader`（CI 侧 `readelf` 为 LLVM 实现，遇 `\| grep -q` 早退管道触发 EPIPE）。构建本身与 `test.sh` 均已通过 | 改为"readelf 输出先落盘再匹配"，脚本内不再有早退管道；本地用 `llvm-readelf` 复现原失败（rc=74）并验证新脚本通过 |

> 说明：该轮 CI 摘要把失败归类为"源码下载超时"，与日志不符——日志显示源码已下载、`conan create` 与 `test.sh` 均成功，真正失败点是 `test_ohos.sh`。详见 `notes.md` 对话 #2。
