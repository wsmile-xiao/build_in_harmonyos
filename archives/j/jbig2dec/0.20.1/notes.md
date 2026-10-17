# jbig2dec 0.20.1 编译笔记（HarmonyOS PC · 标准 Conan autotools）

> 版本号说明：0.20.1 = 上游 0.20 + OHOS 适配修复后缀（R37，制品仓不支持同版本多 revision 并存）

## 定位
- 产出动态 libjbig2dec.so，供 dlopen 及作依赖。
- jbig2dec 是 JBIG2 图像压缩标准的解码器，主要用于 PDF 文档中的 JBIG2 图像解码。

## 关键适配

### 1. OHOS config.guess 不认 uname -s=HarmonyOS
- **问题**：设备的 config.guess 无法识别 `uname -s=HarmonyOS`，导致 configure 无法自动推断主机三元组。
- **修复**：按 E007 知识库规范，用补丁 `patches/0001-port-for-ohos.patch` 修改 config.guess（新增 HarmonyOS case 分支，输出 `aarch64-unknown-linux-ohos`）和 config.sub（新增 `linux-ohos*` / `-linux-ohos*` 到 maybe_os 列表和 OS 列表）。
- **铁律**：禁止用 `--build/--host` 绕过（E007 forbid_1_pattern），会导致 configure 误判为交叉编译，AC_RUN_IFELSE 全跳过，config.h 错误。

### 2. HMDFS TMPDIR 权限问题
- **问题**：HMDFS 默认 TMPDIR 下，configure 的 conftest 写 dummy.c 报 Permission denied，导致 configure 中止。
- **修复**：将 TMPDIR 重定向到 `~/.conan_build_tmp`（持久目录）。
- **关键细节**：不能使用 `build_folder/_tmp`，因为该目录会被 conan 在 test_package 阶段前清掉，而 `os.environ["TMPDIR"]` 会泄漏到同进程的 test_package，导致其 clang 找不到该 tmp 目录（No such file）。

### 3. configure 脚本 umask 077 问题
- **问题**：configure 脚本中 `umask 077` 会导致安装的文件权限过于严格。
- **修复**：递归扫描所有 configure 脚本，将 `umask 077` 替换为 `umask 022`。

### 4. 禁用 libpng 依赖
- 通过 `--without-libpng` 禁用可选的 libpng 依赖，减少适配复杂度。

### 5. 单线程编译
- 使用 `make -j1` 单线程编译，避免 HMDFS 上并发写入问题。

## 测试策略
- `build()` 执行上游 `make check`，通过 `TESTS=` 覆盖只运行 `test_sha1`、`test_huffman`、`test_arith` 3 个确定性测试二进制。
- **跳过 `test_jbig2dec.py` 的原因**：①该脚本依赖外部 `tests/` 样本集（不在发布包内，第 333 行全部 `continue` 跳过）；②脚本 `run()` 方法无 `return` 语句 → `sys.exit(not None)` 恒为退出码 1（上游 bug，任何平台都会失败）。
- test_package 直接链接 libjbig2dec，并调用 `jbig2_ctx_new`、`jbig2_data_in` 和 `jbig2_ctx_free`，满足 R34 反空壳要求。
- test.c 手动用 clang 编译，不依赖 CMake。

## 状态
built
