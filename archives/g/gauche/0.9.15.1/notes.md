# Gauche 0.9.15 编译笔记

## 编译状态
built (Conan 配方验证全门禁通过 G0-G4+L2/L4/L5)

## 编译日期
2026-05-27（探索编译）/ 2026-08-09（Conan 配方适配完成）

## 平台
aarch64-unknown-linux-ohos

## 遇到的问题

### 1. E007: config.guess 无法识别 HarmonyOS
- **症状**: `configure: error: cannot guess build type`
- **根因**: GNU config.guess 不包含 HarmonyOS/__OHOS__ 检测分支
- **解决方案**: 修改 config.guess 和 config.sub，添加 OHOS 支持
- **补丁**: 0013-config.guess.patch, 0014-config.sub.patch, 0030-gc-config.guess.patch, 0031-gc-config.sub.patch

### 2. config.status 临时目录创建失败
- **症状**: `can't create ./confXXXXXX/subs1.awk: Permission denied`
- **根因**: HMDFS 文件系统对临时目录创建有特殊限制，umask 077 导致权限问题
- **解决方案**: 修改 `configure.ac` 源码输入中的 Autoconf 临时目录宏为 umask 002，并重新生成 configure（补丁 0046/0047）。

### 3. pthread_cancel 和 pthread_setcancelstate 缺失
- **症状**: `undefined reference to pthread_cancel, pthread_setcancelstate`
- **根因**: HarmonyOS musl libc 不实现 pthread 线程取消功能
- **解决方案**: Conan 工具链注入 Boehm GC 上游已有的 `GC_NO_PTHREAD_CANCEL` 功能宏，禁用可选的 pthread-cancellation 路径，不在源码补丁中硬编码平台宏。

### 4. GC Warning: PT_GNU_RELRO segment
- **症状**: Boehm GC 警告 `Failed to find PT_GNU_RELRO segment inside PT_LOAD region`
- **根因**: HarmonyOS ELF 文件结构与传统 Linux 不同
- **解决方案**: 可忽略，不影响功能

## Conan 配方关键决策

### 动态构建（非 --disable-shared）
Gauche 的内嵌 Boehm GC 需要生成 `libgc_pic.a`（PIC 归档）供 libgauche 链接。
`--disable-shared` 会使 `libgc_pic.a` 为空，导致 GC_* 符号未定义。
因此 `generate()` 中不加 `--disable-shared`，保持默认动态构建。

### ext/doc/static 跳过
- **ext 跳过**: ext 目录扩展模块在 OHOS 上无法正确加载 Gauche `Scm_*` 符号；recipe 只调用上游 gc/src/lib 核心子目录目标。
- **doc 跳过**: 文档依赖完整扩展树；核心发布不构建或安装文档。
- **static 跳过**: 静态库构建依赖 ext（需要 gauche.uvector 等）；核心发布仅打包共享 `libgauche`。
- **安装方式**: 上游 install 目标会在 HMDFS 构建路径运行新生成的 gosh；recipe 使用 Conan 文件 API 复制已完成的核心产物，避免该路径的动态加载限制。

### copy-port 替换（补丁 0045）
`ext` 目录跳过后，`util.scm` 的 `do-copy` 不能依赖来自扩展目录的 `gauche.uvector`。
补丁 0045 改用核心运行时提供的 `read-byte`/`write-byte` 逐字节复制，保持任意文件内容的二进制完整性。

### package_info 头文件路径
Gauche 的头文件安装在 `lib/gauche-0.98/0.9.15/include/`（autotools
GAUCHE_HEADER_INSTALL_DIR），而非顶层 `include/`。
`package_info()` 中 `cpp_info.includedirs` 指向该嵌套路径。

### test_package require traits（关键修复）
Conan 2.29 的 test_package 阶段，`requires` 默认 `headers=False, libs=False`
（假设 test_package 只运行测试二进制文件，不编译新的二进制文件）。
这导致 CMakeDeps 清空 `INCLUDE_DIRS` 和 `LIBS`，test_package 编译失败
（`'gauche.h' file not found`）。
**修复**: test_package 的 `requirements()` 中显式声明
`self.requires(self.tested_reference_str, headers=True, libs=True)`。

## 验证结果
- conan create 成功 ✓
- test_package (test_gauche) 通过 ✓
- `gosh -e "(display (gauche-version))(newline)"` → `0.9.15` ✓
- `gosh -e "(display (+ 1 2 3))(newline)"` → `6` ✓
- gosh 需 `LD_LIBRARY_PATH` 运行（RPATH 指向 `//lib/...`，prefix=/ 导致）

## 知识提取
1. HarmonyOS 不支持 pthread_cancel 等线程取消功能
2. HMDFS 文件系统对临时目录创建有特殊限制（umask 077→002）
3. Gauche 的扩展模块依赖动态链接，OHOS 上需跳过 ext 目录
4. **R6 铁律遵守**: 删除生成文件补丁（2026-05-28）
5. Conan 2.29 test_package require traits 默认 headers=False/libs=False，
   编译型 test_package 需显式 headers=True, libs=True

---

## 补丁清理记录 (R6 铁律遵守)

**删除的生成文件补丁（16 个）**：
- 0001: .patch-ai-review.txt（AI 判断文件）
- 0015-0019: doc/*.1（man page，编译生成）
- 0023-0029: ext/gauche/*.sci（Scheme 编译产物）
- 0036: src/features.flags（configure 生成）
- 0042-0043: src/gauche-config_threads.h, gauche-priv-configP.h（configure 生成）

**保留的源文件补丁（27 个）**：
- 核心源文件修改（config.guess, config.sub, configure.ac, gc/configure.ac, gc_priv.h 等）
- C 源文件（.c, .h）
- Scheme 源文件（.scm）
- 脚本源文件（gc/configure.gnu-gauche）

---

**Conan 配方验证完成**: 2026-08-13
**最终状态**: built

- `finish` 的 W3 本地 CI 验证于 2026-08-13 11:31 成功，自动生成
  `.ci-result.json`（exit code 0）。
- GNU Make 在 HMDFS 上需使用 `--jobserver-style=pipe`，以避免默认 FIFO
  jobserver 创建被拒绝后退化为串行构建。
- `package_info()` 为已打包的 Scheme 标准库提供 `GAUCHE_LOAD_PATH`。
---

**编译结束**: 2026-08-13 11:31
**最终状态**: built
