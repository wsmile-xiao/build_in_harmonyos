# Adaptation Notes - asymptote 3.12 (OpenHarmony PC / HarmonyOS aarch64)

## Overview
Asymptote is a powerful descriptive vector graphics language for technical
drawing.  Labels and equations are typeset by LaTeX, producing high-quality
PostScript/PDF output.

- Official source: https://asymptote.sourceforge.io/
- Product: `asy` executable (vector graphics compiler — no linkable library)
- Build system: autotools (configure + make)
- 类型: 命令行工具（tool），需声明 commands.json (R38)

## Source
- URL: https://sourceforge.net/projects/asymptote/files/3.12/asymptote-3.12.src.tgz/download
- sha256: `eaec1e97463ef213a393c388d466a73478b0818f9403c962b91240659c9b8f1b`
- tar_format: tar.gz

## Dependencies（依赖清单）
启用的依赖（conan requirements，全部来自 ohpcd 制品仓，W0/R36）：
| 依赖 | 版本 | 说明 |
|------|------|------|
| gsl | 2.8 | 特殊函数支持，**必须启用**（旧分支因当时未发布而禁用，本次已发布必须启用）；ohpcd 仅发布共享版（libgsl.so），gsl 非系统同名库，保持 Conan 管理动态链接 |
| zlib | 1.3.1.1 | configure 硬性依赖（AC_CHECK_LIB z deflate），**必须启用**，R26 静态 |
| gc | 8.2.12 | Boehm 垃圾回收，conan 包（见下）|
| readline | 8.3 | 交互历史，R26 静态；传递依赖 ncurses/6.6 静态 |
| ncurses | 6.6 | readline 传递依赖（R26 静态）|

禁用的组件（configure 参数，均在 notes 记录原因）：
- **OpenGL (--disable-gl)**：OHOS 工具链无 libGL/libglfw，SHIMLIBS 依赖它们
- **Vulkan (--disable-vulkan)**：OHOS 工具链无 vulkan SDK/头文件（VMA 组件无法编译）
- **ffmpeg**：本版本 configure 无 ffmpeg 选项，未启用
- **LSP**：**保持启用**（LspCpp 在树内构建成功）

## 关键适配决策

### 1. Boehm GC：bundled 8.2.8 链接失败 → conan gc/8.2.12
- 源码自带 bundled gc（gc/ 子目录，8.2.8）。尝试 enable-gc 失败：
  - OHOS sysroot libc（`aarch64-linux-ohos`）**没有**
    `pthread_setcancelstate` / `pthread_cancel` 符号
    （运行库 /system/lib64/libc.so 中为 weak 符号，但链接期 sysroot libc.so
    不含），bundled gc 的 pthread_support.o / alloc.o 引用它们 → 链接失败
    `undefined symbol: pthread_setcancelstate`。
  - 改用 conan gc/8.2.12：其静态 libgc.a **不含**这些引用，链接通过。
  - 实现：patch 001 将 Makefile 的 `GCLIB = @GCLIB@` 改为 `GCLIB ?= @GCLIB@`，
    新增 `GCINCLUDE ?= -I$(GC)/include`；conanfile build()/package() 用
    `make GCLIB=<gc包>/lib/libgc.a GCINCLUDE="-I<gc包>/include -Igc/include"`
    传入。bundled gc 源码保留（LspCpp 的 Boehm-GC wrapper 头需要）。
- LspCpp 的 cmake 需要 zlib 定位：conanfile generate() 设置
  CMAKE_PREFIX_PATH/ZLIB_ROOT 指向 zlib 包（LspCpp 的 ixwebsocket 用
  find_package(ZLIB)）。

### 2. config.guess / config.status 的 HMDFS 临时目录问题
- config.guess 无法识别 `HarmonyOS`（uname -s=HarmonyOS）→ 必须
  `--build=aarch64-unknown-linux-gnu`（patch 无此改动，configure 参数传入）。
- configure / gc/configure 的临时目录 `(umask 077 && mktemp -d)` 在 HMDFS
  上 Permission denied（subs1.awk 无法写入）→ patch 002/004 将 umask 077
  改为 022（与旧分支 001-config-status-readable-temp.patch 同因）。

### 3. 版本号为空修复（tarball 构建）
- Makefile.in 中 `revision = ""` 是**字面双引号**，导致
  `ifeq ($(revision),) revision = @VERSION@` fallback 不生效；
  version.txt/revision.cc 生成空版本 → `asy --version` 显示
  "Asymptote version []"。patch 001 将 `revision = ""` 改为 `revision =`。

### 4. make 的 FIFO jobserver 在 OHOS 不可用
- 使用 `make --jobserver-style=pipe -j4`（旧分支同款）。

### 5. OHOS python3 os.posix_spawn 不搜索 PATH
- gen_preprocessed_depfile.py 用 `os.posix_spawn('clang++', ...)` 失败
  （OHOS 上 posix_spawn 不按 PATH 查找可执行文件）。conan 环境中
  AutotoolsToolchain 将 CC/CXX 设为完整路径（/data/service/hnp/bin/clang++），
  make 的 $(CXX) 为完整路径即可。

### 6. 文档构建跳过（无 pdflatex/makeinfo/Ghostscript）
- patch 001（Makefile.in sty 目标）+ patch 003（doc/Makefile.in：
  man/install-man/install 跳过 LaTeX PDF/info）：
  - 无 pdflatex → 跳过 asy-latex.pdf / latexusage.pdf
  - 无 makeinfo → 跳过 png info 文档
  - install-man 用 `$(wildcard $(DOCFILES))` 避免安装不存在的 pdf
  - 空 SHIMLIBS 时 install-asy 加条件判断（install-sh 空参报错）

### 7. gsl 动态库运行时路径
- conan gsl 只产出共享库（libgsl.so）。configure 的 conftest 运行时需
  LD_LIBRARY_PATH 指向 gsl lib；conanfile generate() 用
  `Environment()` + `prepend_path("LD_LIBRARY_PATH", ...)` 解决。

### 8. conan 依赖传播
- 依赖的 -I/-L/-l 与 pkg-config 通过 `AutotoolsDeps` + `PkgConfigDeps`
  注入 configure/make（否则 gsl/readline/ncurses 检测失败）。
- ncurses 包仅提供 libncursesw：pkg-config 的 ncursesw.pc 经
  PkgConfigDeps 生成，configure 的 `-lncurses` 检测靠 readline 的
  Requires.private 传递；conftest 链接时 AutotoolsDeps 提供
  -lncursesw（探索阶段曾手工软链 libncurses.a 解决，conan 环境由
  AutotoolsDeps 直接给出 ncursesw）。

## make check 结果
- functional（tests/）：**104 PASSED / 0 FAILED**（覆盖数值、变换、绘图核心）
- gs/（Ghostscript 渲染）：失败 = 环境无 Ghostscript
- errortests：失败 = conan gc 在 OHOS ELF 打印 `GC Warning: Failed to find
  PT_GNU_RELRO segment inside PT_LOAD region` 到 stderr，污染与预期 .errors
  的对比（平台环境差异，非功能缺陷）
- deconstruct：失败 = 需要 latex（系统无 pdflatex）
- 详见 reports/test-report.md

## Conan 配方要点
- package_type = "application"（纯可执行，非库）
- requirements: gsl/2.8, zlib/1.3.1.1, gc/8.2.12, readline/8.3
- R26：zlib/readline/ncurses 静态（系统同名库，default_options shared=False +
  --enable-static/--disable-shared）；**gsl 保持共享**（非系统同名库，ohpcd 仅发布
  共享版，CI 需下载预编译包而非源码构建）
- R32：settings.os 判断用 `in ("Linux", "OHOS")`
- R33：编译器从 conan toolchain（CC/CXX 完整路径）获取，不裸用 shell 变量
- R34：test_package 实际调用 asy --version + 渲染 EPS
- R38：commands.json（软件级 archives/a/asymptote/commands.json）

## 遗留问题
- 系统无 LaTeX/Ghostscript：asy 的 LaTeX 标签渲染、GS 渲染测试不可用
  （影响文档与部分测试，不影响核心 asy 编译/无标签渲染）
- conan gc 的 PT_GNU_RELRO 警告输出到 stderr（无害，但影响 errortests 对比）

## 版本历史
- 本次为首次适配发布（3.12），对比旧分支 origin/asymptote-3.12：
  - 旧分支 --disable-gsl/--disable-gc（当时未发布）；本次 gsl/2.8、gc/8.2.12
    已发布，**均启用**
  - 旧分支 --disable-ffmpeg/--disable-lsp；本次 LSP 保持启用
  - 新增 gc 外部覆盖、版本号修复、文档跳过补丁（refresh-patch --auto 生成）

---

**编译结束**: 2026-08-16
**最终状态**: published（conan-verify 8 道门禁通过）
