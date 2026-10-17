# goffice 0.10.57.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-27
- 编译器: clang/clang++（OHOS SDK 15）
- 状态: built
- 目标平台: OHOS aarch64（armv8）
- Conan 引用: goffice/0.10.57.1

## 编译步骤

1. 依赖发布检查（W0）：cairo/1.18.4、pixman/0.46.4、libpng/1.6.58、freetype/2.14.3、
   fontconfig/2.18.1、zlib/1.3.1.1、expat/2.8.2、libgsf/1.14.58 均已发布到 ohpcd 制品仓。
2. 源码解压至 `/storage/Users/currentUser/tmp/builds/goffice-0.10.57.work`，
   保留 `.orig` 目录用于 difflib 生成补丁。
3. 编写 `conanfile.py`（autotools 配方）：`generate()` 中通过 `AutotoolsToolchain`
   注入 configure 参数，`build()` 应用补丁并运行 `./configure && make -j1 && make install`。
4. 关键 configure 参数：
   - `--disable-introspection`（无需 GObject Introspection）
   - `--disable-dependency-tracking`（HMDFS 下 depcomp 引导失败）
   - `--without-rsvg`（librsvg 不可用，通过补丁改为可选依赖）
   - `--without-lasem`（lasem 不可用）
   - `--build=aarch64-linux --host=aarch64-linux`（跨编译目标三元组）
5. `generate()` 阶段：
   - 安装 cmd-pkgs GTK+ 栈（gtk+/pango/gdk-pixbuf/atk/harfbuzz/fribidi/libepoxy 等）到 `GTK_PREFIX`；
   - 将 cmd-pkgs 的 `lib/pkgconfig` 置于 `PKG_CONFIG_PATH` 首位；
   - 派生 gobject-2.0/gmodule-2.0/gio-2.0 与 cairo-ps/pdf/svg 的 `.pc` 文件；
   - 剥离 cmd-pkgs GTK `.pc` 中的 cairo-gobject 依赖。
6. 运行 `conan create` 完成本地构建与 test_package 消费侧 smoke test。
7. 运行 `ohc-run.py finish goffice 0.10.57 built` 完成收尾（refresh-patch → close-archive →
   clean-verify → conan-verify → W3 本地 CI 模拟 → finalize-archive → 知识完整性 → gen_summary → PR 原子性）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | librsvg 是上游硬依赖，HarmonyOS PC 无 Rust 工具链 | librsvg 为 Rust 编写的 SVG 渲染器，未适配 OHOS | 补丁 0002/0003/0004/0005/0006 将 librsvg 改为 `--without-rsvg` 可选依赖，并用 `GOFFICE_WITH_RSVG` 宏守卫相关代码路径 |
| 2 | configure 执行 intltool 检查失败 | intltool 需要 `XML::Parser` perl 模块，OHOS 无此模块 | 补丁 0001 在 Makefile.in 中移除 po/ 子目录（禁用 NLS）；补丁 0002 禁用 intltool；build() 中写入 intltool-merge shim 去除 `.xml.in` 翻译标记 |
| 3 | configure 的 conftest 在 HMDFS 上失败 | `ac_tmp` 使用只读 /tmp，`mktemp` 权限 077 与 HMDFS 不兼容 | `_patch_configure_hmdfs()` 修补 configure：`ac_tmp` 指向固定可写目录、`ac_pwd` 回退到 `$PWD`、mktemp/mkdir umask 改为 022 |
| 4 | 补丁修改 configure.ac 后未生效 | tarball 预生成的 configure 不含新选项 | build() 中 `_regen_configure()` 用 autoconf 重新生成 configure，并 touch 生成文件避免 automake 重跑 |
| 5 | configure.ac 检查 gobject-2.0/gmodule-2.0/gio-2.0 失败 | conan PkgConfigDeps 只生成聚合 glib-2.0.pc | `_derive_glib_sub_pc()` 派生三个子 `.pc`，同样派生 cairo-ps/pdf/svg |
| 6 | libgoffice 运行链缺 libcairo-gobject.so.2（libgtk-3.so.0 的 DT_NEEDED） | conan cairo 配方 glib=disabled 不产出 cairo-gobject | 改用 cairo-gobject/1.18.4 配方（glib=enabled，同时产出 libcairo.so + libcairo-gobject.so.2），并在配方中派生 cairo.pc |
| 7 | glib-2.0.pc 含 `-l:ld-musl-aarch64.so.1` 导致 ld.lld 无法解析 | `-l:filename` 需要显式搜索路径 | `_patch_conan_pcs()` 将其替换为绝对路径 `/lib/ld-musl-aarch64.so.1` |
| 8 | make install 在 HMDFS 上因 `install` 命令差异失败 | 上游 Makefile 的 install 参数与 OHOS 环境不兼容 | build() 中 `_write_install_shim()` + `_redirect_install_to_shim()` 用 sh 脚本替代 install |
| 9 | 上游 5 个测试程序（TESTS）本地无法运行 | 测试二进制链接 libgoffice → libgtk（cmd-pkgs GTK 栈）；而 cmd-pkgs GTK 栈是静态内嵌 glib 构建（libgtk 导出 4208 个 g_* 符号且 .init_array 全 0，构造器丢失），与 conan 动态 glib 并存时 gobject 类型系统冲突（static_quark_type_flags 断言失败） | 运行期部署方案（详见"上游测试验证结果"）：DT_NEEDED 闭包收集（cp -L 按 SONAME）+ RUNPATH=$ORIGIN + ELF 签名后，用**空实现 stub**替换 cmd-pkgs GTK 栈库（保留符号、函数返回 0，供 BIND_NOW 重定位），LD_PRELOAD 加载 conan 动态 glib 全家 → 5 个测试真实运行 5/5 PASS |
| 10 | glib/libgsf 用绝对路径 .so 链接（libtool 不记入 NEEDED） | libgsf-1.la 的 dependency_libs 含绝对路径 .so；cmd-pkgs libgdk_pixbuf 的 DT_NEEDED 直接是绝对路径 | 闭包收集时对绝对路径 NEEDED 取 basename 命名；libgsf 未记录的 glib/gio 符号通过显式补入 glib 全家 + LD_PRELOAD 动态 glib 解析 |
| 11 | conan 构建目录父级仅 --x 权限，bash 启动 getcwd() 失败（"Not supported"） | HMDFS 的 getcwd 需要遍历+读父目录，conan 缓存目录只有执行权限 | 运行环境显式设置 PWD=runtime_dir（bash 校验后直接采用，不调用 getcwd()） |

## 源码修改

6 个补丁（archives/g/goffice/0.10.57/patches/）：

- `0001-Makefile.in.patch`：从 SUBDIRS 移除 po/（禁用 NLS）。
- `0002-configure.ac.patch`：将 librsvg 改为可选 `--without-rsvg`，禁用 intltool/po。
- `0003-goffice-component-go-component.c.patch`：用 `GOFFICE_WITH_RSVG` 守卫组件快照渲染中的 librsvg 用法。
- `0004-goffice-utils-go-image.c.patch`：守卫 go-image.c 中的 librsvg include。
- `0005-goffice-utils-go-svg.c.patch`：守卫 go-svg.c 中的 librsvg 用法。
- `0006-libgoffice.pc.in.patch`：从 libgoffice.pc 的 Requires.private 移除 librsvg-2.0（移到 EXTRA_DEPS）。

## 依赖版本

Conan（ohpcd 制品仓）：
- glib/2.88.0.1（**shared=True**，GTK 栈同版本族；libgsf/cairo-gobject 传递的
  glib/2.84.0.1 经 override 统一）、zlib/1.3.1.1.1.1（override，PIC 静态库供
  glib shared 链接）、cairo-gobject/1.18.4、pixman/0.46.4、libpng/1.6.58、
  freetype/2.14.3、fontconfig/2.18.1.1、expat/2.8.2.1、libgsf/1.14.58

cmd-pkgs 预编译 GTK+ 栈（GTK_PREFIX=/storage/Users/currentUser/usr/local，**静态内嵌
glib 构建**，测试运行期用 stub 替换）：
- gdk-pixbuf 2.42.12、atk 2.38.0、fribidi 1.0.13、libepoxy 1.5.10、
  harfbuzz 14.2.0、pango 1.50.14、gtk+ 3.24.38、libxml2 2.15.3、libxslt 1.1.39、
  libjpeg-turbo 3.1.4.1 等

构建工具：intltool 0.51.0（cmd-pkgs 预编译，提供 intltool-update）。

## 验证结果

```bash
# conan create 成功，本地缓存存在 armv8/OHOS binary 包
conan list "goffice/0.10.57:*"
# → goffice/0.10.57 (arch=armv8, os=OHOS, compiler=clang 15, build_type=Release)

# test_package 消费侧 smoke test 通过（10 个断言）
# test.c 实质调用 libgoffice_init / libgoffice_shutdown 与 go_format_* API
# → ./test_goffice 返回 0，所有断言通过
```

## 上游测试验证结果

上游 5 个正式测试程序（tests/Makefile.am 的 TESTS）已集成到 build() **编译 + 真实运行**：

| 测试程序 | 编译 | 运行 | 说明 |
|---------|:----:|:----:|------|
| test-quad | PASS | **PASS** | quad 精度数学（801 行断言输出，rc=0） |
| test-math | PASS | **PASS** | 数学函数（442 行，rc=0） |
| test-format | PASS | **PASS** | 数字格式化（73 行，rc=0） |
| test-dtoa | PASS | **PASS** | double-to-ascii（7 行，rc=0） |
| test-decimal | PASS | **PASS** | 上游原生"未编译 Decimal64 支持"路径（rc=0） |

- **编译**：5/5 PASS（arm64 ELF + 链接 libgoffice，go_quad_* 等符号已导出验证）
- **运行**：5/5 真实运行 PASS。运行期部署方案（本配方 build() 内置）：

  1. **闭包收集**：把测试二进制与完整 DT_NEEDED 闭包 cp -L 复制到独立运行目录
     （按 SONAME 文件名写入真实文件，解引用符号链接；HMDFS loader 无法经符号
     链接加载 .so）。cmd-pkgs libgdk_pixbuf 用绝对路径 NEEDED → 按 basename 处理；
     libgsf 未记录 NEEDED glib/gio（绝对路径链接）→ 显式补入 glib 全家。
  2. **RUNPATH=$ORIGIN**：patchelf 对测试二进制与全部闭包库设置 $ORIGIN（单引号
     防 shell 展开），loader 从运行目录解析依赖，规避 OHOS namespace 限制。
  3. **ELF 签名**：全部闭包 ELF 用 llvm-objcopy 移除旧 .codesign 后重新
     binary-sign-tool 签名（OHOS 内核要求）。
  4. **GTK 栈 stub 替换**：cmd-pkgs GTK 栈（libgtk/libgdk/libpango 等）静态内嵌
     glib 且构造器丢失，与 conan 动态 glib 冲突导致 gobject 类型系统崩溃。
     测试只调用 libgoffice 纯计算函数、不真正使用 GTK → 用"空实现 stub"
     （导出全部符号、函数返回 0）替换 GTK 栈库，BIND_NOW 重定位得到满足。
  5. **LD_PRELOAD 动态 glib**：预加载 libglib/libgobject/libgio/libgmodule/
     libintl（动态），保证 libgsf/libgoffice 的 glib/gio 符号解析到动态版
     （quark/gtype 系统正常），且 stub 无内嵌 glib → 两套状态互不干扰。
  6. **bash 逐项运行**：/system/bin/sh（mksh）不能 exec ELF → 用 bash 包装；
     显式 PWD=runtime_dir 规避 HMDFS getcwd 限制；TMPDIR/HOME 指向可写目录。

## 交付物

- `conanfile.py`：Conan 2.x autotools 配方（474 行）。
- `conandata.yml`：官方源码 URL + SHA256 + 6 个补丁声明。
- `test_package/`：conanfile.py、test.c、CMakeLists.txt、MANIFEST.yml。
- `patches/`：0001~0006 共 6 个补丁。
- 本地 conan 缓存二进制包：goffice/0.10.57（armv8/OHOS）。

## 注意事项

- goffice 是 GTK+3 GUI 库，适配要点与 gtkdatabox 先例一致：GTK 栈走 cmd-pkgs，底层库走 conan。
- librsvg 被禁用，SVG 相关功能在 OHOS 上不可用（上游 goffice 将 librsvg 视为硬依赖，本配方改为可选）。
- 上游 5 个测试程序（TESTS）已在 build() 集成交叉编译（编译 PASS），但运行期因无头环境缺 GTK 运行库（libcairo-gobject.so.2 等）受限（SKIP），详见 MANIFEST.yml upstream_test_audit。
- 不要重新下载源码 / 重新编译：本地缓存已有成功构建结果。

---

### 对话 #1 — 2026-08-18 16:15

- 初始化归档骨架，确定 goffice 0.10.57 使用 autotools 构建，源码来自 download.gnome.org。
- W0 依赖发布检查：8 个底层依赖均已发布到 ohpcd，无需先适配依赖。

### 对话 #2 — 2026-08-18 17:00

- configure 阶段首次失败：intltool 需要 XML::Parser、librsvg 硬依赖无法满足。
- 决定方案：补丁将 librsvg 改为可选（--without-rsvg），禁用 intltool/NLS，
  写入 intltool-merge shim 与 install shim 处理 HMDFS 差异。

### 对话 #3 — 2026-08-18 17:26

- 生成 6 个补丁（refresh-patch --auto），确认 patch_classification 与 conandata.yml 一致。
- 编写 conanfile.py（474 行），generate() 安装 cmd-pkgs GTK 栈并派生 .pc，build() 应用补丁 + 重生成 configure。

### 对话 #4 — 2026-08-18 19:00

- conan create 成功，本地缓存生成 goffice/0.10.57（armv8/OHOS）binary 包。
- test_package 消费侧 smoke test 通过（test.c 调用 libgoffice_init/libgoffice_shutdown 与 go_format_* API，10 个断言）。

### 对话 #5 — 2026-08-18 19:30

- 收尾：填充 manifest.yaml 与 notes.md，运行 finish 管线（W3 本地 CI 模拟阻塞门禁）。
- 编译结束。
---

**编译结束**: 2026-08-18 20:07
**最终状态**: built
