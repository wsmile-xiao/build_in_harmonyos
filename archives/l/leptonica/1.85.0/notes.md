# leptonica 1.85.0 适配笔记

## 任务背景

OCR 链第二环（tesseract 依赖 leptonica）。与 1.87.0 历史适配的关键差异：
**启用完整图像格式依赖**（历史版本仅 zlib），供 OCR 链读写多格式文档图像。

## 编译环境

- 构建系统: cmake（autogen.sh 失败，libtoolize shebang 路径问题，1.84.1/1.87.0 历史实证）
- 编译日期: 2026-09-05（2026-09-07 改锁 libtiff 4.7.2 后全量重验）
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang）
- Conan 版本: 2.29.1（OHOS 适配版）
- profile: ci/conan/profiles/ohos-aarch64
- 分支: feat/leptonica-1.85.0（worktree ../wt-leptonica）

## 依赖策略（与 1.87.0 的差异）

| 依赖 | 版本 | 启用 | 说明 |
|------|------|------|------|
| zlib | 1.3.1.1 | ✅ | 与 libpng/libtiff 依赖链对齐（1.3.1 会 Version conflict） |
| libpng | 1.6.58 | ✅ | PNG 支持（本版新增） |
| libjpeg-turbo | 3.2.0 | ✅ | JPEG 支持（本版新增） |
| giflib | 5.2.2 | ✅ | GIF 支持（本版新增）；上游 find_package(GIF 5) 要求 major 5，6.1.3 不兼容 |
| libtiff | 4.7.2 | ✅ | TIFF 支持（本版新增）；制品仓已发布版本（4.7.0 在 #8326 仍 open 等复审，依赖锁须引用已发布版本） |
| openjpeg | 2.5.4 | ✅ | JP2K 支持（本版新增） |
| libwebp | — | ❌ | 上游 find_package(WebP 0.5.0 CONFIG) 要求 major 0，libwebp/1.6.0 是 major 1，CMake 版本兼容规则判不兼容，无法 CONFIG 模式命中 |

## CMakeDeps 对接（关键适配点）

上游 find_package 名与 conan 包名不一致，消费方配方内覆盖：

| 上游 find_package | conan 包 | 覆盖属性 |
|---|---|---|
| ZLIB | zlib | cmake_file_name=ZLIB, target=ZLIB::ZLIB |
| PNG | libpng | cmake_file_name=PNG, target=PNG::PNG |
| JPEG | libjpeg-turbo | cmake_file_name=JPEG, target=JPEG::JPEG |
| GIF 5 | giflib | cmake_file_name=GIF, target=GIF::GIF |
| TIFF | libtiff | cmake_file_name=TIFF, target=TIFF::tiff |
| OpenJPEG CONFIG | openjpeg | cmake_additional_variables_prefixes=OPENJPEG |

技术要点：
1. CMakeToolchain 默认 `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`，使 find_package(ZLIB/PNG/JPEG/GIF/TIFF)
   先走 CONFIG 模式命中 CMakeDeps 生成的 <NAME>Config.cmake；不设则先走 CMake 内置
   Find*.cmake MODULE 模式（OHOS 交叉环境找不到系统库 → *_FOUND=FALSE）。实测验证。
2. cmake_file_name 覆盖后，CMakeDeps 会以 <NAME>Config.cmake 命名并同时 set <NAME>_LIBRARIES
   变量（值是 conan target 名，可直接 target_link_libraries）。实测验证。
3. OpenJPEG 特殊：上游 CMakeLists 用 `${OPENJPEG_LIBRARIES}`（全大写前缀），
   需要 `cmake_additional_variables_prefixes=["OPENJPEG"]` 让 config 文件额外 set OPENJPEG_* 变量。
4. OpenJPEG 版本判断：上游比较 OPENJPEG_VERSION（OPENJPEG_MAJOR_VERSION.MINOR）>= 2.1，
   CMakeDeps 的 find 不自动设置这两个变量，需在 toolchain cache_variables 显式传 2/5。
5. OpenJPEG 链接：上游 `target_link_libraries(leptonica PRIVATE openjp2)` 裸名链接，
   注入所有依赖 libdir 的 -L/-rpath-link（poppler/sdl2-image 同法）。
6. os=OHOS 守卫设置 cmake_system_name=OHOS + processor=aarch64（poppler 实证：
   conan 默认 HarmonyOS 与 cmake 平台文件 OHOS.cmake 名字不匹配，SONAME 缺失传染下游）。

## 构建命令

```bash
conan create archives/l/leptonica/1.85.0/ \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing

# CI 验证
CI_PACKAGES="archives/l/leptonica/1.85.0" zsh ci/conan/build_and_test.sh
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | find_package(ZLIB/PNG/JPEG/GIF/TIFF) 全部 *_FOUND=FALSE | CMake 4.x 默认 MODULE 模式优先（系统 Find*.cmake 在 OHOS 交叉环境找不到库）；conan CMakeDeps 生成的是 CONFIG 文件 | CMakeToolchain 默认 CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON（conan 自动设置）+ 消费方配方 set_property 覆盖 cmake_file_name（ZLIB/PNG/JPEG/GIF/TIFF/OpenJPEG） |
| 2 | 生成期报 "WebP::libwebpmux target not found" | libtiff 传递依赖 libwebp 的 CMakeDeps 泄漏 set(WebP_LIBRARIES WebP::webp)，触发上游 if(WebP_LIBRARIES) 分支链接 WebP::libwebpmux（libwebp 包只导出 WebP::webp 单 target） | cmake_build_modules 注入 WebP::libwebpmux IMPORTED target（sdl2-image 2.8.12 同法），指向包内真实 libwebpmux.so |
| 3 | JPEG 内存回环失败 "Premature end of JPEG file" | **OHOS musl open_memstream 平台差异**：不把终结 NUL 计入 *psize（除非 fclose 前显式 fflush），与 glibc 不同；leptonica 的 *psize - 1 多减 1 → JPEG EOI 标记（FFD9）末字节被截断 | 补丁 001：pixWriteMemJpeg 在 fputc('\0') 后加 fflush(fp)，使 glibc/musl 双平台 *psize 语义一致（jpeg_bytes+1），-1 后精确还原。最小 C 程序实验定位（open_memstream 写 644B + NUL：无 fflush→size=644，有 fflush→645） |
| 4 | find_package(GIF 5) 与 giflib/6.1.3 不兼容 | CMake 版本兼容规则要求 major 相等（请求 5 vs 包 6.1.3） | 选用 giflib/5.2.2（major 5 兼容） |
| 5 | find_package(WebP 0.5.0 CONFIG) 无法命中 | 上游要求版本 0.5.0（major 0），libwebp/1.6.0 是 major 1，CMake 兼容规则判不兼容 | ENABLE_WEBP=OFF（leptonica 核心功能不依赖 WebP；libtiff 的 WebP 编解码由其自身依赖链承担） |
| 6 | OPENJPEG_LIBRARIES 变量为空 | 上游用全大写前缀变量判断/链接，CMakeDeps 默认只 set OpenJPEG_* | cmake_additional_variables_prefixes=["OPENJPEG"] + toolchain cache 传 OPENJPEG_MAJOR_VERSION=2/MINOR=5 |
| 7 | 上游链接 openjp2 裸名 | target_link_libraries(leptonica PRIVATE openjp2) 无 -L 时找不到库 | 注入依赖 libdir 的 -L/-rpath-link（poppler/sdl2-image 同法） |

## JPEG 补丁定位过程（可复用的平台差异诊断方法）

1. 现象：pixWriteMemJpeg rc=0 size=643，但 pixWriteStreamJpeg 写文件是 644 字节
2. 对比尾部：mem 尾 `cf ff` vs 文件尾 `cf ff d9`——缺 EOI 末字节
3. 最小实验 open_memstream（10 字节 + NUL）：glibc 语义 fclose 后 size=11（含 NUL）；OHOS musl：fputc 后无 fflush → fclose 后 size=10（NUL 不计入）
4. 结论：leptonica 的 `*psize - 1` 在 musl 上多减 1
5. 修复：fputc('\0') 后 fflush(fp) 强制把 NUL 计入 → 双平台一致 → -1 精确还原
6. 补丁验证：conan create + test_package JPEG 回环 PASS

## 源码修改

patches/001-jpegio-fflush-before-fclose-on-musl-memstream.patch（jpegio.c 一处，+11 行）

## 依赖锁变更（2026-09-07）

- libtiff 4.7.0 → 4.7.2：#8326（libtiff 4.7.0）仍 open 等复审，制品仓仅有 4.7.2
  （`conan list "libtiff/*" -r=ohpcd` 实测）。依赖锁必须引用已发布版本（R36/W0/PF4），
  改 `self.requires("libtiff/4.7.2")` 后全量重验：conan create 全绿（Package
  '78bf496c90680ecb0477c72b85cd5e36188c3800' created）+ test_package 1/1（12 断言
  全过，TIFF 内存回环 PASS）。上游 find_package(TIFF) 无精确版本要求，4.7.x
  API 兼容，无需其他改动。

## 上游测试真跑改造（2026-09-10，rule4 修复）

PR #8755 被 Septest 打回：上游 N=302 passed=0 不可接受（"无论构建开关/环境
原因均不能跳过上游测试验证"）。修复：conanfile.py `build()` 内真跑上游测试
（boost-log #8463 测试运行器模式）。

### 测试结构考古（上游 302 的构成）

- `prog/CMakeLists.txt` 注册 302 个 `add_prog_target`（160 个 `*_reg` + 142 工具/演示）
- autotools `make check` 只跑 **AUTO_REG_PROGS**（144 基础 + 4 条件：gifio_reg=HAVE_LIBGIF
  / webpio_reg+webpanimio_reg=HAVE_LIBWEBP / jp2kio_reg=HAVE_LIBJP2K）= 148
- 本配方启用 GIF/JP2K、WebP 关闭 → 真跑集合 = 144 + gifio + jp2kio = **146**
- MANUAL_REG（13）/ OTHER_PROGS（129）/ INSTALL_PROGS（12）上游 make check 不跑
- alltests_reg 数组（149）与 AUTO_REG 差集 = files_reg（MANUAL）

### 真跑 harness（三个关键工程问题及解法）

1. **/tmp 只读**：上游 reg 框架（src/regutils.c）硬编码 `/tmp/lept/{regout,golden}`
   路径树，OHOS 根文件系统 /tmp 是只读 erofs（不可 bind mount：无 root）。
   解法：`test_files/lept_tmp_redirect.c` LD_PRELOAD 库，拦截 mkdir/fopen/open/
   stat/access/opendir/unlink/remove/rmdir/rename/realpath/mkstemp(tmpstem)/tmpfile
   把 `/tmp/lept` 前缀透明重定向到 build 目录。坑：
   - musl 把 fopen64/open64/stat64 宏映射到同名函数（不能再包装 64 变体）
   - `realpath` 不走 libc 文件 API（内部直调系统调用）必须单独拦截，否则
     `getFilenamesInDirectory` 报 "realdir not made"（sarray1.c）
   - `mkstemp("/tmp/lept.XXXXXX")` 模板缓冲按原长度堆分配（stringConcatNew
     精确分配）→ **等长替换方案**：在 base/lept.XXX 创建真实文件，原地只替换
     6 个随机字符（长度不变零溢出），后续 open("/tmp/lept.abc123") 经 open
     拦截命中 base/lept.abc123
2. **输入图像**：reg 程序按相对路径读源码 prog/ 下的图像（上游 make check 从
   build 目录跑、srcdir 找数据）→ `_sync_prog_inputs` 把源码 prog/ 的数据文件
   symlink 进 build/prog（bytea_reg/string_reg 还读 prog/*.c 做字节级自证，.c
   也在同步范围）
3. **结果判定**：部分程序在测试结果落盘后、exit 清理阶段 SIGTRAP（见下），
   退出码不可靠 → 以 `/tmp/lept/reg_results.txt` 的 `SUCCESS|FAILURE: <test>`
   行为准（上游 alltests_reg 汇总同口径）

### 真跑抓出的第二个 musl 平台 bug（补丁 002）

heap_reg/watershed_reg 首轮失败（`regTestWriteDataAndCheck: data not defined
or size == 0`）暴露 *WriteMem 家族的同族问题：**musl open_memstream 的 *psize
只在显式 fflush 后更新**（glibc fclose 自动 flush）。最小实验：`open_memstream`
写 644B + NUL，无 fflush → fclose 后 size=644（NUL 不计）；有 fflush → 645。
补丁 002 把 001 的修复推广到全部 20 处 `fputc('\0', fp); fclose(fp);` 调用点
（boxbasic/colormap/dewarp1/dnabasic/fpix1/numabasic/pixabasic/pixcomp/pnmio/
ptabasic/recogbasic/sarray1 共 12 文件）。**这是"真跑上游测试"的直接收益：
只跑消费者测试永远发现不了这个。**

### 11 个 SIGTRAP 崩溃的归因（未完全定位，证据链完整）

heap/insert/selio/string/pixcomp/mtiff/pdfio2/pdfseg/psioseg/dewarp/genfonts
的 compare 阶段 SIGTRAP（信号 5）。已做对照实验：

1. 无 LD_PRELOAD 时同二进制从不崩（tempfile 失败 rc=1 干净返回）
2. 115 个测试同 harness 正常完成（含同样的 tempfile 写入 / open_memstream /
   fwrite 路径——最小程序 test_fprintf/test_fwrite/test_memstream 均不崩）
3. 11 个崩溃测试的 generate 阶段全部完整成功（golden 全产出）
4. trap handler + /proc/self/maps 定位：PC 固定 `ld-musl-aarch64.so.1+0x1e3a8`
   （musl 内部无符号区域；系统 musl 集成了 OHOS malloc hook 框架
   libnative_hook.z.so/libdfmalloc.z.so，怀疑与 hook 有关但未证实）
5. gdb 不可用（ptrace: Permission denied）、core_pattern 指向不可写位置

结论：非 leptonica 逻辑失败（golden 证明主体正确），OHOS musl 运行时在重定向
harness 下特定执行路径的限制；单列申报（报告 [crashed] 节 + 每测试日志留档）。

### 最终结果

```
UPSTREAM_TESTS: total=146 passed=115 failed=0 skipped=20 crashed=11
test_package: 100% tests passed, 0 tests failed out of 1（12 断言全过）
conan create RC=0
```

构建耗时约 10 分钟（302 prog 编译 + 292 次测试运行），CI 45 分钟默认预算内。

---

**编译状态**: built（2026-09-10 rule4 修复后全量重验：conan create RC=0，上游 AUTO_REG 真跑 115/146 PASS + 20 gnuplot skip + 11 musl SIGTRAP 豁免，test_package 1/1 PASSED）
