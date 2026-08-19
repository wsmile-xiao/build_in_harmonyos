# swftools 0.9.2 困难适配分析

> 状态：VERIFIED DRAFT
>
> 结构化条目：`knowledge/drafts/DRAFT-swftools-autotools-hmdfs-2168.kv`

Issue: #2168

Date: 2026-08-14

Submission path: A（基础适配）+ B（困难三方库适配分析）

## 1. 适配范围与困难度

swftools 0.9.2 发布于旧式 Autotools 生态，发布包包含生成后的 `configure` 和多层手写 `Makefile.in`。上游构建系统假定传统 Linux 文件系统、可直接执行的脚本、宽松的全局符号链接规则以及可向安装前缀写入文件；这些假设在 OHOS 交叉编译、HMDFS 工作目录和 Conan 隔离包目录中同时失效。

本次没有引入可选图像、字体、音频或 PDF 依赖，仅复用仓库已有的 `zlib/1.3.1`，目标是让 13 个核心命令形成可复现的 OHOS Conan 包，并通过消费者视角的端到端测试。适配共涉及四个源码补丁以及配方层面的 configure、构建、安装、补充打包和签名逻辑。

## 2. 构建与测试基线

- 源码归档：`swftools-0.9.2.tar.gz`
- SHA256：`bf6891bfc6bf535a1a99a485478f7896ebacbe3bbf545ba551298080a26f01f1`
- 构建系统：in-source Autotools；上游明确拒绝 `--srcdir`
- 必需依赖：`zlib/1.3.1`
- 目标配置：`--build=aarch64-unknown-linux-gnu --disable-lame`
- 构建并发：`make -j1`
- 产物：`wav2swf`、`png2swf`、`swfcombine`、`swfstrings`、`swfextract`、`swfdump`、`swfc`、`swfbbox`、`font2swf`、`swfrender`、`as3compile`、`swfbytes`、`ttftool`

官方 0.9.2 归档的顶层 `Makefile.in` 没有 `check` 或 `test` 目标，但子目录 Makefile 明确定义了 7 个测试目标：`lib/python` 的 `test1-test6` 和 `lib/action` 的 `test`。前者分别调用 `test_create.py`、`test_combine.py`、`test_simple.py`、`test_movie.py`、`test_image.py`、`test_sprite.py`，后者编译链接 `test.c`。

经对官方 MacPorts 归档清单核对，上述 6 个 Python 测试脚本和 `lib/action/test.c` 均未随 0.9.2 发布包携带；`lib/action` 测试还依赖未声明的旧版 t1lib、JPEG、FreeType。因此本轮区分“上游声明目标数”与“发布包可运行测试数”：`N_declared=7`，`N_runnable=0`，不将缺失文件伪造为上游通过。`test_package` 仍从消费者视角检查 13 个命令，并执行 `swfc -> SWF -> swfdump` 真实数据链路，新增测试为 `M=1`、通过率 `1/1`。

## 3. 关键问题、根因与修复

### 3.1 生成后的 configure 不能直接执行

- 现象：R2 在配方配置阶段报 `Permission denied`。
- 根因：源码位于 HMDFS/工作区时，归档中的 `configure` 可读但不具备可靠的直接执行语义。
- 修复：OHOS 分支显式通过 `sh configure` 调用，同时保留 Conan 生成的参数和环境。
- 边界：该处理只改变 OHOS 配置入口，不重生成 Autotools 文件，也不影响其他平台。

### 3.2 configure 临时目录在 HMDFS 下不可写

- 现象：R3 创建 `subs1.awk` 等临时文件时失败。
- 根因：旧 configure 以 `umask 077` 创建临时目录；HMDFS 权限映射使后续子进程无法按预期写入。
- 修复：`0001-configure.patch` 将临时目录放到 `${TMPDIR:-.}` 下；配方为 OHOS 创建专用 TMPDIR，并设置兼容的 `umask 002`。
- 边界：临时目录仍位于本次构建目录内，构建结束可整体回收，不向共享系统目录泄漏文件。

### 3.3 旧式 tentative definition 与现代编译器冲突

- 现象：多个翻译单元链接时产生重复符号。
- 根因：头文件直接定义全局变量，依赖旧编译器默认 `-fcommon` 合并；现代 Clang/GCC 默认 `-fno-common`。
- 修复：`0003-fix-common-symbol-definitions.patch` 将头文件声明改为 `extern`，在对应 `.c` 文件保留唯一实体定义，并修复相关 include guard。
- 边界：不通过全局添加 `-fcommon` 掩盖源码缺陷，保持链接语义明确。

### 3.4 安装规则忽略 DESTDIR

- 现象：R4 编译成功，但 `make install` 尝试写入设备根目录的 `/bin` 和 `/share`。
- 根因：多层旧式 `Makefile.in` 拼接安装路径时未统一传播 `DESTDIR`。
- 修复：`0004-install-destdir.patch` 为顶层、`src`、`lib` 和 `swfs` 的程序、手册及数据安装补齐 `DESTDIR`。
- 边界：保留上游 `prefix`/`bindir`/`datadir` 语义，只增加标准 staged-install 前缀。

### 3.5 数据链接和非标准安装产物

- 现象：旧安装命令使用目标环境 `rm` 不支持的选项，并可能把 Conan 缓存绝对路径写入软链接；`swfbytes`、`ttftool` 构建后不由上游安装。
- 根因：安装脚本面向旧 GNU 用户态，且上游安装清单不完整。
- 修复：`0002-swfs-Makefile.in.patch` 使用可移植删除参数和相对软链接；配方从构建目录补充复制两个工具，再对 13 个 ELF 统一执行 OHOS 自签名。
- 边界：补充内容仅限上游实际生成的核心命令，不伪造可选功能产物。

## 4. 调试轮次与证据判定

| 轮次 | 结果 | 判定 |
|---|---|---|
| R2 | configure 直接执行权限失败 | 配方兼容问题，已修复 |
| R3 | configure 临时文件权限失败 | HMDFS 权限兼容问题，已修复 |
| R4 | 编译成功、安装写根目录失败 | 上游安装规则问题，已修复 |
| R5/R6 | `can't fork` / `Errno 12` | 设备遗留会话导致的资源耗尽，不归因于库代码 |
| R7 | G0、L0/L1/L2/L4/L5 和端到端测试全部通过 | 适配有效 |

R5/R6 后先清理无关遗留 SSH 会话并恢复设备资源，再使用相同代码运行 R7。R7 成功说明这两次失败属于执行环境资源故障，未通过修改库配方规避或掩盖。

## 5. 可复用判断与建议

1. 对 HMDFS 上的旧 Autotools 包，先分别检查脚本执行权限、configure 临时目录权限和 staged install，三者是独立故障面。
2. 遇到重复全局符号，应优先修复声明/定义关系，不应把 `-fcommon` 作为默认长期方案。
3. 验证 `DESTDIR` 时必须覆盖递归子目录和数据安装规则；顶层接受变量不代表子 Makefile 实际使用。
4. 对旧式 Autotools 项目，必须同时记录 Makefile 声明的测试目标和发布归档实际携带的测试文件；缺失脚本或依赖时单独标记不可运行，并用真实生产者/消费者数据链路补充验证。
5. shadow CI 的 `fork`/内存错误需要先用设备资源指标和干净重跑分类；只有相同环境下可复现的失败才进入库代码修复。

这些建议来自 swftools 的实际证据，但可迁移到同类旧 Autotools CLI 项目。本 PR 只新增与 swftools #2168 直接相关的草稿，不修改正式知识图谱、索引或其他库内容。

## 6. 最终 R7 结果

- 代码提交：`62dba31e0de7a5c620b725b4eaf3e7dc789eb0d9`
- 单包汇总：`Total: 1`，`Success: 1`，`Failed: 0`
- 测试输出：`swftools end-to-end smoke test passed`
- 标准 run：`/storage/Users/currentUser/ohos-test-runs/codex-swftools-issue2168-shadow-ci-r7-20260814-215337-18784`
- recipe revision：`a1f4bd8e1c55a6d884a0469da3efae86`
- package ID：`d19813127f0ec2ca84c0b48cbd85080965097448`
- package revision：`2102587fdcd1a5acf5da7fb5a20d0cdf`

本报告作为路径 B 的困难适配分析材料提交；路径 B 是否计分以评审委员会最终认定为准。适配包本身同时满足路径 A 的基本交付要求。
