# plutobook 0.19.0 适配笔记（OHOS aarch64 · Conan Meson）

## 定位
- 上游：https://github.com/plutoprint/plutobook （tag v0.19.0，MIT）
- 构建系统：**Meson**（上游无 CMakeLists），C++20
- 产出：`libplutobook.so`（共享库）+ `html2pdf` / `html2png` 两个 CLI（→ 软件级 commands.json，R38）
- 依赖全部走 Conan 制品仓（无源码内嵌、无 wrap 下载）：`-Dwrap_mode=nodownload`

## 编译环境
- 编译器：OHOS SDK clang 15.0.4（`aarch64-unknown-linux-ohos-clang`）
- profile：WSL 交叉 profile `ohos-aarch64-wsl`（= `ci/conan/profiles/ohos-aarch64` 去掉设备路径 + 交叉工具链）
- 构建命令：`conan create . -pr:h=<wsl-profile> -pr:b=default -r=ohpcd --build=missing`
- 状态：**built**（aarch64-ohos conan create 通过；test_package 编译+链接通过，执行见 test-report.md）

## 关键适配（四段式：现象 → 根因 → 修复 → 复验）

### 1. meson 找不到 pkg-config（交叉构建特有）
- 现象：`Found pkg-config: NO` → 所有 `dependency()` 失败
- 根因：meson 在 **cross 构建**中要求 pkg-config 二进制显式给出（`Pkg-config binary missing from cross or native file`），
  而 conan `MesonToolchain` 的 `self.pkgconfig` 只来自 `tools.gnu:pkg_config` conf 或 `PKG_CONFIG` 环境变量（toolchain.py:296-298,492）
- 修复：WSL profile 增加 `tools.gnu:pkg_config=<pkg-config 绝对路径>`
- 复验：`Found pkg-config: YES` + 13 个依赖全部 `found: YES`

### 2. 上游要求 C++20，CI profile 是 17
- 现象：`-std=c++20` 缺失 → `std::span` 不可用
- 根因：`MesonToolchain.cpp_std` 取自 `settings.compiler.cppstd`（toolchain.py:165-168,559），会覆盖 meson 的 `default_options`
- 修复：配方 `tc.cpp_std = "c++20"`
- 复验：编译命令行出现 `-std=c++20`，`std::span` 相关文件编译通过

### 3. OHOS libc++ 缺 `<memory_resource>` / `std::pmr`（本次核心适配）
- 现象：`source/heapstring.h:13: fatal error: 'memory_resource' file not found`
- 根因（实测）：OHOS SDK 的 libc++ 被裁剪——
  - 无顶层 `<memory_resource>`，`std::pmr` 容器别名在 `<vector>/<map>/...` 中也不存在；
  - `<experimental/memory_resource>` 只有抽象基类 `memory_resource` + `polymorphic_allocator`，具体资源（monotonic/pool）未实现；
  - `libc++_shared.so` 无任何 pmr 符号，`get_default_resource()` 等仅在 `libc++experimental.a`；
  - 华为官方 FAQ 亦确认 HarmonyOS 不支持 `#include <memory_resource>` 与 `std::pmr::vector`
- 修复（补丁 0001+0002）：
  - 新增 `source/ohos_pmr_compat.h`：`namespace std { namespace pmr = experimental::pmr; }` +
    按标准语义实现 `monotonic_buffer_resource`（只增不减、析构/release 统一归还）；
  - `heapstring.h` 的 `#include <memory_resource>` 改为 `#include "ohos_pmr_compat.h"`
    （heapstring.h 被 globalstring.h/boxstyle.h 等传递包含，覆盖全部 pmr 使用文件）
  - 配方补 `tc.extra_ldflags.append("-lc++experimental")`（pmr 容器默认构造引用 `get_default_resource()`）
- 复验：65/65 源文件编译通过；链接通过；`libplutobook.so` 产出成功

### 4. `std::views` 不可用（libc++ 默认关闭 ranges）
- 现象：`error: no member named 'views' in namespace 'std'`（flexiblebox.cpp:316 / linelayout.cpp:240,327 / tablebox.cpp:538,561,1422）
- 根因：OHOS libc++ 的 `__config` 在未定义 `_LIBCPP_ENABLE_EXPERIMENTAL` 时定义
  `_LIBCPP_HAS_NO_INCOMPLETE_RANGES`（`__config:255-256`），`<ranges>` 整体不生效
- 修复：配方 `tc.extra_cxxflags.append("-D_LIBCPP_ENABLE_EXPERIMENTAL")`（仅 libc++ 生效）
- 复验：`std::views::reverse` 编译+链接通过（最小样例 + 全量构建均通过）

### 5. 上游 meson 需要 cairo 的 4 个子特性 .pc 与 libturbojpeg.pc
- 现象：`dependency('cairo-pdf')` 等 required 但 Conan 只生成 `cairo.pc`
- 根因：Conan `PkgConfigDeps` 每包只按 `pkg_config_name` 生成一个 .pc；包内自带的 `.pc` 写死 `prefix=/` 不能直接用
- 修复：`generate()` 转发生成 `cairo-pdf/cairo-png/cairo-ft/cairo-fc/libturbojpeg` 的 .pc
  （只写 Requires、版本从被转发者继承；知识条目 **E348**，pango/1.56.4 同款手法）
- 复验：meson 输出 `cairo-pdf/png/ft/fc found: YES 1.18.4`、`libturbojpeg found: YES 3.2.0`

### 6. 顶层依赖版本必须与 cairo 链路一致
- 现象：`Version conflict: Conflict between expat/2.8.2.1 and expat/2.8.2.1.1`
- 根因：`fontconfig/2.18.1.1` 精确锁定 `expat/2.8.2.1`；`cairo/1.18.4` 锁定 pixman/libpng/freetype/fontconfig/zlib
- 修复：顶层逐字对齐（expat/2.8.2.1、freetype/2.14.3、fontconfig/2.18.1.1、harfbuzz/14.3.0、cairo/1.18.4、icu4c/77）
- 复验：依赖图无冲突，11 个依赖全部命中制品仓预编译包

### 7. 设备侧 CI：meson 归档器缺失 + ELF 签名（CI #42771 实测）
- 现象（设备 CI 首次构建）：`../meson.build:1:0: ERROR: Unknown linker(s): [['llvm-ar']]`，
  `Running llvm-ar --version gave "[Errno 2] No such file or directory: 'llvm-ar'"`
- 根因：conan 的 `MesonToolchain` 不会把 `tools.build:compiler_executables` 里的 ar/ranlib 写进
  `conan_meson_*.ini`；CI profile 只声明了 c/cpp（`/data/service/hnp/bin/clang`），meson 便按
  裸名 `llvm-ar` 探测归档器，而设备构建环境的 PATH 中没有它（知识条目 **E481**）
- 修复：`generate()` 调用 `_inject_meson_archiver()`——从 c 编译器同目录推导
  `llvm-ar`/`llvm-ranlib` 全路径，回退 `shutil.which("llvm-ar")`/`shutil.which("ar")`，
  写入 `conan_meson_native.ini`/`conan_meson_cross.ini` 的 `[binaries]` 段（不污染 PATH；
  cairo/1.18.4 同款手法）。本机复验：生成的 ini 中 `ar = <SDK>/native/llvm/bin/llvm-ar`
- 另修：`package()` 增加 `_sign_elfs()`——meson install 重写 rpath 会破坏链接器自签，
  未签名的 `.so`/可执行文件在设备上无法 dlopen/exec（E481、cairo 同款）；本机无
  `binary-sign-tool` 时自动跳过，由设备侧 CI 完成签名

### 8. 上游 C API 的可选字符串参数不能传 NULL（设备 CI 实测）
- 现象（设备 CI 第 2 轮）：test_package 执行到 `plutobook_load_html(book, html, len, NULL, NULL, NULL)`
  直接 `Signal 11 (core dumped)`（conan 报 `Error 139`）；分步 STEP 诊断定位到 STEP 6 load_html
- 根因：上游 C 封装 `source/plutobook.cc:645` 把 `const char*` 参数**原样**转 `std::string_view`，
  而 `std::string_view(nullptr)` 会走 `char_traits::length(nullptr)` → `strlen(NULL)` → SIGSEGV。
  头文件注释虽写 "optional"，但实际**必须传空串**，NULL 不被支持
- 修复：test_package 改传 `""`（本机 x86_64-ohos 复现验证：`string_view(nullptr)` rc=139）
- 复验：设备 CI 重新构建（本轮修复后由 CI 执行运行时断言）

## 补丁说明

### 0001-source-heapstring.h.patch
一行 include 替换：`<memory_resource>` → `"ohos_pmr_compat.h"`。无平台宏。

### 0002-source-ohos_pmr_compat.h.patch
新增兼容头 `source/ohos_pmr_compat.h`：为 OHOS 裁剪版 libc++ 补齐
`std::pmr` 别名与 `monotonic_buffer_resource`（标准语义实现，非空壳）。
仅依赖 OHOS libc++ 已提供的 `<experimental/*>` 容器别名与 header-only 的 `memory_resource` 基类。

## 依赖版本（全部制品仓已发布）
cairo/1.18.4、harfbuzz/14.3.0、freetype/2.14.3、fontconfig/2.18.1.1、expat/2.8.2.1、icu4c/77、
curl/8.15.0（→openssl/3.5.6.1）、libjpeg-turbo/3.2.0、libwebp/1.6.0；
传递：pixman/0.46.4、libpng/1.6.58、zlib/1.3.1.1

## 上游测试
上游 0.19.0 **无自动化测试入口**：tarball 内无 `tests/` 目录，`meson.build` 无 `test()`，
`meson_options.txt:9` 的 `tests` 选项是残留。test_package 为自建消费者测试（R34）。

## 验证结果
```
conan create . -pr:h=<ohos-aarch64-wsl> -pr:b=default -r=ohpcd --build=missing
→ create_rc=0；65/65 源文件编译；libplutobook.so.0.19.0 + html2pdf + html2png 打包成功
→ test_package：CMake 配置/编译/链接通过（aarch64-ohos）
```
日志：`/mnt/e/dsh working/tasks/plutobook-0.19.0-2026-09-08/logs/030-conan-create-aarch64.log`

## 注意事项
- 产物含可执行文件 → 软件级 `commands.json` 已声明（R38）
- 本机 WSL 无法执行 aarch64 产物（无 aarch64 musl loader）；执行通道见 `reports/test-report.md`

## 关于 conan-verify G2 的环境说明（必读）

本机（WSL2 x86_64 交叉编译）跑 `conan-verify` 时，G2 门禁固定用设备 profile
（`ci/conan/profiles/ohos-aarch64`，编译器 `/data/service/hnp/bin/clang`），或 host==build 同名 profile。
归档内 `reports/conan-verify-report.md` 记录的实际报错为：

```
G2: ❌ FAIL — Unknown compiler(s): [['/data/service/hnp/bin/clang']]
```

其机制是：设备编译器路径在 WSL 不存在 / host==build 时 conan 按 native 构建处理，meson 需**执行**
aarch64 sanity check（在更早的同构运行 `logs/070`、`logs/081` 中可见
`Could not invoke sanity check executable ... Possibly wrong architecture`），**必然失败**。
这是环境边界，不是配方缺陷。等价验证与 CI 分工如下（**权威证据为 `reports/w3-local-ci.log`**）：

| 验证 | 结果 | 证据 |
|---|---|---|
| `conan create -pr:h=ohos-aarch64-wsl -pr:b=default -r=ohpcd --build=missing` | **rc=0**（65/65 源文件、打包成功） | `reports/w3-local-ci.log`（12:31:40，最终配方版）；早期运行见 `logs/110`/`111` |
| 本地 CI 模拟（L0/L1/L4/L5） | **全 pass**（L2 skip 为交叉环境限制，非阻塞） | `logs/120-local-ci-after-fixes.log` |
| W3 `.ci-result.json` | `exit_code=0`（finish 自动写入） | `archives/p/plutobook/0.19.0/.ci-result.json` |
| conan-verify G0/G1 | PASS | `logs/021-conan-verify.log` |
| conan-verify G2 | 环境受限（设备原生 profile） | `reports/conan-verify-report.md` |
| 设备原生 verify | 由 CI 在鸿蒙电脑执行（计分通道） | CI 流水线 |
---

**编译结束**: 2026-09-09 00:58
**最终状态**: built
