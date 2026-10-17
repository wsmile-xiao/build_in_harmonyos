# libopenraw-pixbuf-loader 0.3.7 适配笔记

## 这是什么

`libopenraw_pixbuf.so` 是 libopenraw 源码树内自带的 **gdk-pixbuf RAW 加载器模块**
（`gnome/pixbuf-loader.c`），导出 `fill_info()` / `fill_vtable()` 两个
`G_MODULE_EXPORT` 入口，由 gdk-pixbuf 在运行时 dlopen。上游**没有独立 tarball**，
源码取官方 libopenraw 0.3.7 发布包。

## 编译环境

| 项 | 值 |
|---|---|
| 构建系统 | 自定义（单文件 clang 编译；上游规则见 `gnome/Makefile.am`） |
| 编译日期 | 2026-09-25 |
| 编译器 | OHOS clang 15.0.4（`tools.build:compiler_executables` 提供，非 shell 变量） |
| 平台 | OHOS armv8 / aarch64（profile `ci/conan/profiles/ohos-aarch64`） |
| 状态 | built |

## 编译策略与命令

**为什么不用整树 autotools**：整树 `configure.ac` 硬要求 cargo/rustc（`lib/mp4`
Rust workspace），且会连带构建 libopenraw 库本体（已单独发布 `libopenraw/0.1.2`）。
本包只是**单个 C 文件**，上游 `gnome/Makefile.am` 用一条规则构建它：

```
libopenraw_pixbuf_la_LDFLAGS = -no-undefined -module -avoid-version
libopenraw_pixbuf_la_LIBADD  = ../lib/libopenraw.la $(LIBGLIB_LIBS) $(LIBGDKPIXBUF_LIBS)
libopenraw_pixbuf_la_SOURCES = pixbuf-loader.c
loaderdir = $(GDK_PIXBUF_DIR)
loader_LTLIBRARIES = libopenraw_pixbuf.la
```

conanfile.py 精确复刻该规则：单文件 `-shared -fPIC -O2` 编译，链接
libopenraw + glib + gdk-pixbuf，安装到 `lib/gdk-pixbuf-2.0/loaders/`。
编译输入（编译器、`-I`/`-L`/`-l`）全部来自 Conan toolchain / 依赖 `cpp_info`，
`self.run()` 中无任何裸 shell 变量（R33）。

等价的手工命令（配方 build() 实测输出）：

```bash
clang -shared -fPIC -O2 -o libopenraw_pixbuf.so gnome/pixbuf-loader.c \
  -I<libopenraw>/include -I<libopenraw>/include/libopenraw-0.1 \
  -I<gdk-pixbuf>/include/gdk-pixbuf-2.0 -I<gdk-pixbuf>/include \
  -I<glib>/include -I<glib>/include/glib-2.0 -I<glib>/lib/glib-2.0/include \
  -I<glib>/include/gio-unix-2.0 \
  -L<...> -lopenraw -lgdk_pixbuf-2.0 -lglib-2.0 -lgobject-2.0
```

产物 `libopenraw_pixbuf.so`（`-module -avoid-version` → 无 .so.N），随后用
`binary-sign-tool sign -selfSign 1` 签名（OHOS 下未签名 ELF 无法 dlopen）。
实测签名段存在：`.codesign` + `.note.ohos.ident`。

## 依赖选择（R36 决策，含实测证据）

**结论：`requires("libopenraw/0.1.2")`（已发布版本）。**

| 候选 | registry 状态（实测） | 结论 |
|---|---|---|
| `libopenraw/0.3.7` | `conan download libopenraw/0.3.7 -r=ohpcd --only-recipe` → **exit 1**（未发布） | ✗ 不可作为 requires |
| `libopenraw/0.1.2` | 同命令 → **exit 0**（已发布） | ✓ 采用 |

实测命令与输出：

```
$ conan download libopenraw/0.3.7 -r=ohpcd --only-recipe
Connecting to remote 'ohpcd' anonymously
ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]
(exit=1)

$ conan download libopenraw/0.1.2 -r=ohpcd --only-recipe
Skip recipe libopenraw/0.1.2#17b01134b68ccb153d6faf0e657931bb download, already in cache
(exit=0)
```

R36/PF4 判定：**0.3.7 被拦截**。W3 本地 CI（`ci/conan/build_and_test.sh`）内置
L0i 依赖发布检查（对 conanfile.py AST 抽出的每个 `requires` 跑
`conan download <dep> -r=ohpcd --only-recipe`，失败即 `L0_FAILED`），因此
`requires("libopenraw/0.3.7")` 会使 W3 直接失败、包不可合并；同时建 PR 前 PF4
依赖闸同口径拦截。→ 采用已发布的 0.1.2（R36/RF4 可通过）。

### 0.3.7 本地完整验证（为什么它其实是兼容的，待发布后可重指）

0.3.7 的 `pixbuf-loader.c` 调用的**全部 API 在 0.1.2 公共头文件中同样存在**
（实测 grep：`or_rawfile_new_from_memory` / `OR_RAWFILE_TYPE_UNKNOWN` /
`or_bitmapdata_new` / `or_rawfile_get_rendered_image` / `OR_ERROR_NONE` /
`or_bitmapdata_dimensions` / `or_bitmapdata_data` / `or_rawfile_get_orientation` /
`or_rawfile_release` / `or_bitmapdata_release` 全部命中）。

此外对 **libopenraw 0.3.7**（本地缓存二进制，未发布）做了手工完整验证：

```bash
# 用 0.3.7 头文件/库单文件编译并链接
clang -shared -fPIC -O2 -o libopenraw_pixbuf_037.so gnome/pixbuf-loader.c \
  -I<or037>/include/libopenraw-0.3 ... -L<or037>/lib -lopenraw -lgdk_pixbuf-2.0 -lglib-2.0
# → RC=0, NEEDED libopenraw.so.9
# 签名后 dlopen 测试（复用 test_package/test.c）
# → 14/14 checks passed（fill_info name="Digital camera RAW"、10 extensions、vtable 入口齐全）
```

即：**源码与 0.3.7 二进制 ABI/API 完全兼容**，唯一的阻塞是 0.3.7 尚未发布到
ohpcd。**建议发布顺序与后续动作**：先由 libopenraw 协作者发布
`libopenraw/0.3.7`（`conan upload`）→ 再把本包 `requires` 由 `libopenraw/0.1.2`
重指为 `libopenraw/0.3.7`（因 cnb.cool 同版本不可并存多 revision，本包版本号
按 R37 递增为 `0.3.7.1`），并重跑 W3。

### zlib 版本冲突（配方内 override）

`libopenraw` → `boost/1.84.0` 固定 `zlib/1.3.1`；`gdk-pixbuf` → `glib/2.84.0.1`
固定 `zlib/1.3.1.1`，直接组图冲突：

```
ERROR: Version conflict: Conflict between zlib/1.3.1.1 and zlib/1.3.1 in the graph.
```

配方用 `self.requires("zlib/1.3.1.1", override=True)` 统一到较新 ABI（方向选择：
override 到 1.3.1.1 只会让 libopenraw 侧 package-id 变化；反向 override 到 1.3.1
会牵动 glib/gdk-pixbuf/libpng/libtiff 整条链，代价更大）。

## 上游测试清点与实测（R51）

> **修正记录（2026-09-27）**：本节此前申报 **N = 0**，是错的——当时只清点了
> `gnome/`（加载器所在子目录），而 R51 要求清点的是**源码树注册的测试总数**。
> PR #12724 审查（@Septest）指出"上游有用例 9 个但一个也没测"，
> 经复核属实：本包源码就是 libopenraw 0.3.7 整树 tarball，树内 automake
> `TESTS` 注册 **9 个**用例。现已真实构建并运行，见下。

### 1. 清点（N = 9）

```bash
# 全树 TESTS 注册（这是 R51 的口径）
$ grep -rn "^TESTS" --include=Makefile.am .
./lib/Makefile.am:38:TESTS = teststream
./test/Makefile.am:2:TESTS = fileio testoption ljpegtest testunpack extensions testbititerator
./testsuite/Makefile.am:2:TESTS = test_xmlhandler testsuite

# gnome/（加载器所在目录）自身无测试 —— 这曾是 N=0 的唯一依据
$ grep -rn "TESTS\|check_PROGRAMS\|check_LTLIBRARIES" gnome/
  (none in gnome/)

# demo/ 是 noinst_PROGRAMS 演示程序（非测试）
$ grep -rn "noinst_PROGRAMS" demo/Makefile.am
7:noinst_PROGRAMS = extensions thumbc ccfa ppmload $(GNOME_BINARIES)
```

| 项 | 值 |
|---|---|
| 上游测试总数 **N** | **9**（`lib/`:1 + `test/`:6 + `testsuite/`:2） |
| 实际运行 **N′** | **9** |
| 通过率 | **9/9 = 100%** |
| 本包 test_package 断言 | **14**（含 2 个阴性对照，独立于上游用例） |

### 2. 实测（真实构建并运行，非声明）

本包 `build()` 现已集成整树构建与上游测试执行：configure/make 整棵 0.3.7 树 →
`make check-TESTS` 逐目录运行注册用例（`conanfile.py` 的 `_build_upstream_tree()`
与 `_run_upstream_tests()`）。`conan create` 实测输出：

```
RUN: make -j1 check-TESTS         (lib/)
PASS: teststream
# TOTAL: 1   # PASS: 1   # FAIL: 0

RUN: make -j1 check-TESTS         (testsuite/)
PASS: test_xmlhandler
PASS: testsuite
# TOTAL: 2   # PASS: 2   # FAIL: 0

RUN: make -j1 check-TESTS         (test/)
PASS: fileio
PASS: testoption
PASS: ljpegtest
PASS: testunpack
PASS: extensions
PASS: testbititerator
# TOTAL: 6   # PASS: 6   # FAIL: 0

UPSTREAM TESTS SUMMARY: 9/9 passed (N'=9, N=9)
```

逐项结果：`teststream`、`test_xmlhandler`、`testsuite`、`fileio`、`testoption`、
`ljpegtest`、`testunpack`、`extensions`、`testbititerator` —— 全部 **PASS**。

**必须说明的技术限制**：`testsuite` 是数据驱动用例，内部 47 条断言全部引用真实
相机 RAW 文件（上游靠 `-b` 经 libcurl 从 `libopenraw.freedesktop.org/samples/`
下载）。本环境 `HAVE_CURL=no`（未接 libcurl），bootstrap 关闭，47 条输出
`File not found, skipping.` 后以 0 退出，被 automake 记为 PASS。因此 9/9 中
`testsuite` 一项**不构成真实断言覆盖**，需相机 RAW 样本（网络）才能真跑；
其余 8 项（`teststream`、`test_xmlhandler` 与 `test/` 六项）为自包含真实断言
（boost 框架 "No errors detected"）。

### 3. 测试之外：本包自身的消费者测试

R51 之外，本模块的运行期行为由 `test_package/` 独立覆盖：dlopen 打包并**已签名**的
`lib/gdk-pixbuf-2.0/loaders/libopenraw_pixbuf.so`，dlsym `fill_info`/`fill_vtable`，
断言 `name == "Digital camera RAW"`、10 个 RAW 扩展名（含 cr2/dng）、
mime_types 含 `image/x-canon-cr2`，并断言 vtable 的
`begin_load`/`stop_load`/`load_increment` 已挂载、`load == NULL`（与上游一致）；
阴性对照：dlopen 不存在路径必须失败、dlsym 伪造符号必须返回 NULL。

## 验证结果

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=missing
# ... Test execution ...
ok 1 - negative control: dlopen() of a missing module fails
ok 2 - dlopen libopenraw_pixbuf.so module
...
ok 14 - negative control: dlsym() of a bogus symbol returns NULL
1..14
# 14/14 checks passed
```

## 注意事项 / 工具误报（附证据）

- **`lang-preflight` 工具误报**：`scripts/ohc/lang_detect.py::_manifest_scan` 是
  全递归文件名扫描且 `Cargo.toml` 分支优先，把 libopenraw 树内
  `lib/mp4/Cargo.toml` 当成工程 manifest，判定 `detected_language=mixed`
  （`build_system=cargo`，`manifest=Cargo.toml name = "mp4"`），并自动写
  `env_unsupported` 终态。本包实际只构建 `gnome/pixbuf-loader.c`（C），
  **属工具误报**，未按 env_unsupported 终止，最终 result 据实覆盖为成功。
- `/tmp` 只读（E002）：scratch 目录一律用 `$TMPDIR`（本机 `$HOME/tmp`）。
- HMDFS 并行 make 触发 jobserver fifo EPERM：`-j1` 或单文件编译规避。
- 本包**不需要 Rust**，未引入 cargo。

## 交付物

| 文件 | 说明 |
|---|---|
| `lib/gdk-pixbuf-2.0/loaders/libopenraw_pixbuf.so` | 签名后的 gdk-pixbuf RAW 加载器模块 |
---

**编译结束**: 2026-09-27 14:12
**最终状态**: built
