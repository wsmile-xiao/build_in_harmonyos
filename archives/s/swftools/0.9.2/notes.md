# swftools 0.9.2 HarmonyOS 前置适配记录

## 本轮状态

- Issue: `#2168`
- 分支: `feat/swftools-0.9.2-2168`
- 阶段: 前置适配、单包真机 shadow CI 已完成，按审核意见补充测试证据
- 复验策略: 代码提交和最终文档 HEAD 分别使用同一 runner 做单包验证
- 结果: 13 个核心命令完成 OHOS 构建、打包与签名，`test_package` 端到端用例通过

## W0 依赖检查

上游 `configure.in` 明确要求 zlib，缺少时会终止配置。本轮选用仓库已有的 `zlib/1.3.1`：

```text
conan download "zlib/1.3.1" -r=ohpcd --only-recipe
recipe revision: 2ee7c0eeb8f4dfef8982d0c5c1551a61
result: pass
```

JPEG、GIF、FreeType、Fontconfig、FFTW、LAME、PDFlib/Poppler、zziplib、Avifile 以及 Python/Ruby 绑定均为可选能力。本 PR 不混入这些依赖的适配，并通过 configure 缓存变量关闭自动探测；首轮产物聚焦 13 个不依赖上述可选库的命令。

## 源码与构建系统

- 源码: `https://distfiles.macports.org/swftools/swftools-0.9.2.tar.gz`
- SHA256: `bf6891bfc6bf535a1a99a485478f7896ebacbe3bbf545ba551298080a26f01f1`
- 构建系统: 旧式 Autotools，发布包包含 `configure`、`configure.in` 和手写 `Makefile.in`
- 构建方式: 上游明确拒绝 `--srcdir`，必须 in-source 构建
- HarmonyOS 参数: `--build=aarch64-unknown-linux-gnu --disable-lame`
- 编译并发: `make -j1`

首轮预期安装命令：

```text
wav2swf png2swf swfcombine swfstrings swfextract swfdump swfc
swfbbox font2swf swfrender as3compile swfbytes ttftool
```

其中 `swfbytes` 和 `ttftool` 会被上游构建但不会被 `make install` 安装，配方在 `package()` 中补充复制。OHOS 包装阶段对全部 13 个 ELF 执行自签名，供原生 `test_package` 运行。

## 补丁说明

1. `0001-configure.patch`: 将 Autoconf 临时目录放到 `${TMPDIR:-.}` 下，规避 HMDFS 上 `umask 077` 临时目录不可写问题。
2. `0002-swfs-Makefile.in.patch`: 移除 `rm` 不支持的 `-o -L` 参数，并把数据文件软链接改为相对目标，避免 Conan 缓存绝对路径进入包。
3. `0003-fix-common-symbol-definitions.patch`: 把头文件中的 tentative definitions 改为 `extern`，在对应 `.c` 文件保留唯一实体定义，同时修复 `swfc-history.h` include guard。该补丁适配 Clang/GCC 默认 `-fno-common` 的现代行为。
4. `0004-install-destdir.patch`: 为顶层、`src`、`lib` 和 `swfs` 安装规则补齐 `DESTDIR`，防止旧式 Makefile 把产物写到设备根目录的 `/bin`、`/share` 和 `/man`。

## 上游测试分析

官方 `swftools-0.9.2.tar.gz` 的顶层 `Makefile.in` 没有 `check` 或 `test` 目标，但两个子目录的 `Makefile.in` 明确定义了 7 个上游测试目标：

- `lib/python/Makefile.in:test` 聚合 `test1-test6`，分别调用 `test_create.py`、`test_combine.py`、`test_simple.py`、`test_movie.py`、`test_image.py` 和 `test_sprite.py`。
- `lib/action/Makefile.in:test` 是编译链接自检，依赖 `test.c` 以及未声明的旧版 t1lib、JPEG、FreeType。

经核对，0.9.2 官方发布归档不携带上述 6 个 `test_*.py` 脚本，也不携带 `lib/action/test.c`；因此上游声明目标数为 7，但发布包中可实际运行的上游测试数为 0。这里的 `0` 是“可运行测试数”，不是“没有测试定义”，不能执行 `make check` 或伪造上游通过率。

本 PR 的 `test_package` 从消费者视角执行真实端到端流程：检查 13 个命令存在，运行 `swfc --version`，用 `swfc` 编译最小 `.sc` 为 SWF，再由 `swfdump` 解析并断言版本和帧数。测试口径为：上游声明目标 `N_declared=7`，发布包可运行上游测试 `N_runnable=0`，新增消费者测试 `M=1`，新增测试通过率 `1/1`。

## 本机验证

本机前置检查覆盖源码哈希、W0 远端配方、四个补丁顺序应用、Conan 配方加载/导出、依赖图和 Python 测试脚本语法。本机没有可替代 OHOS 目标环境的 C 工具链，因此编译和运行结论只引用真机 shadow CI，不以宿主机结果代替。

## 真机 / Shadow CI 结果

R7 在提交 `62dba31e0de7a5c620b725b4eaf3e7dc789eb0d9` 上只运行 `archives/s/swftools/0.9.2`，结果如下：

```text
G0: PASS
L0/L1/L2/L4/L5: PASS
Build Summary: Total 1, Success 1, Failed 0
test_package: swftools end-to-end smoke test passed
```

标准 runner 记录：

```text
/storage/Users/currentUser/ohos-test-runs/
  codex-swftools-issue2168-shadow-ci-r7-20260814-215337-18784
```

R2-R4 暴露并修复了旧 `configure` 执行方式、HMDFS 临时目录权限和安装规则忽略 `DESTDIR` 的问题。R5/R6 是设备资源耗尽导致的外部失败；清理遗留会话并恢复设备资源后，相同代码在 R7 通过。详细根因、适配边界和复用建议见 `knowledge/drafts/DRAFT-swftools-autotools-hmdfs-2168.md`。

## 最终状态

- 适配状态: `built`
- Shadow CI: 全部步骤通过，Conan 单包构建 `1/1`，消费者测试 `1/1`
- 上游测试: 声明 `7` 个目标，但官方 0.9.2 发布包缺少测试脚本/源码，可运行 `0` 个
- 待办: PR 审核与合入
- 阻塞点: 无库内适配阻塞；上游测试缺失属于发布包边界，已在测试报告和 MANIFEST 中记录
