# libnma-gtk4 1.10.6 适配笔记

## 定位

libnma 的 GTK4 变体拆分包（libportal-gtk3/gtk4 同款拆分模式）。姊妹件
libnma 1.10.6 本体（gtk3 主库）在途 #8298（2301_77929998），本件只交付
libnma-gtk4.so + libnma-gtk4.pc + include/libnma 公共头。

上游 meson 无条件构建 gtk3 主库与 gtk4 变体两个目标；本件补丁新增
libnma_gtk3 选项，false 时跳过 gtk+-3.0 探测与主库构建，共享源码
（utils-libnm 静态库/gir_sources/tests）改用 gtk4 头编译——源码本身
gtk3/gtk4 双兼容（utils.c 等带 GTK_CHECK_VERSION(4,0,0) 分支）。

## 源码选择

GNOME 官方 release tarball（download.gnome.org），非 GitHub tag archive：
- dist tarball 自带 src/libnma-gtk4/ 17 个预转换 Gtk4 .ui 文件
  （Makefile.am EXTRA_DIST 清单），meson 走"dist 已含 gtk4 数据"分支
- GitHub tag archive 缺该目录 → meson 走 generator 用 gtk4-builder-tool
  simplify --3to4 在线转换 → 需构建机 PATH 上有可执行的
  gtk4-builder-tool（OHOS ELF 需签名，本机实测未签名工具 Operation
  not permitted，签名+正确 LD_LIBRARY_PATH 后可用）——官方 dist 从根上
  绕开此依赖
- GNOME 镜像同步滞后：USTC/TUNA/BFSU/SJTU 均无 1.10.6（404），NJU 已同步

## 依赖图（W0 判定）

- libnm/1.58.0：上游 meson.build:178 无条件 dependency('libnm', '>= 1.7')
  ——gtk4 变体也链接。制品仓已有（PR #11275，2501_91367425，9-21 合入）
  ——本件非"变体先出禁依赖"场景，直接 requires
- gtk4/4.22.4（broadway 后端）：变体构建核心依赖
- glib 统一 2.84.0.1.1（gtk4 recipe 同款 override；libnm 链 glib/2.84.0.1
  被 override 统一，同 2.84 ABI soname 不变）
- gcr=false：ohpcd 未发布 gcr-4/gck-2（gcr-base/3.41.2 只有 gcr-base-3/
  gck-1 pc 名，且 pkcs11 源码在 enable_gcr=false 时不参与编译，
  nma-cert-chooser.c 的 #ifdef GCK stub 分支天然兼容）
- iso_codes=false / mobile_broadband_provider_info=false：仅影响 config.h
  数据目录宏，不影响编译产物
- gettext/0.22.5.1 tool_requires：subdir po → i18n.gettext 需要
  msgfmt/msgmerge（系统只有 msgfmt/xgettext）

## 关键踩坑（顺序即出现顺序）

1. **gmodule-export-2.0 pc 缺失**：glib recipe 未声明该组件，
   PkgConfigDeps 不产出——从 glib 包内真实 pc 复制改 prefix + 把依赖包
   pkgconfig 目录追加进 native file 的 pkg_config_path（libnm 1.58.0
   模式）
2. **gtk+-3.0 硬探测**：无选项可关——补丁 0001 新增 libnma_gtk3 选项；
   初版尝试 gtk/3.24.43 进图但 pango 双版本冲突（gtk3 binary 绑定
   pango/1.50 系，gtk4 绑定 1.56 系，conan 图同名包不允许双版本），
   统一到任一侧都会使另一侧 binary 失配触发源码重编——gtk3 全链出图
   才是解
3. **glib_compile_resources 变量缺失**：gnome.compile_resources 经
   gio-2.0.pc 的 glib_compile_resources 变量定位工具（meson 1.12 实测）
4. **glib-compile-resources 运行时找不到 libgio**：glib 包 bin/ 的 ELF
   工具无 RPATH，ninja custom command 环境 LD_LIBRARY_PATH 不含 glib
   lib——工具变量一律指向 shell wrapper（wrapper 内 export
   LD_LIBRARY_PATH）而非裸路径
5. **meson test 的 gettext libintl 遮蔽**：conanbuildenv 把 gettext 工具包
   lib 目录排 LD_LIBRARY_PATH 前部，其 libintl.so.8（libintl_* 无前缀
   符号）遮蔽 glib vendor libintl（g_libintl_* 符号）→ libgtk-4 一整链
   Error relocating——subprocess 直跑 meson test --no-rebuild +
   os.environ 精拼路径（runtime-lib 物化目录最前，物化 glib vendor
   libintl 全家）
6. **cpp_info.requires 组件校验**：override 的依赖（glib）不能进组件表
   （check_component_requires 排除 r.override）——不声明 requires，pc 链
   传递（libportal-gtk4 同款）
7. **CMakeDeps 静态 glib2 双实例**：test_package 用 CMake 拼法时，
   graphene→glib2/2.88.0 静态库与 glib/2.84.0.1.1 动态库同时排进链接行
   → GType 双状态 abort——test_package 改 pkg-config/meson 拼法
   （gtk4 test_package 同款）

## 上游测试（R51）

- meson 注册 test() 1 例：src/utils 的 test-utils（utils.c 纯函数单测，
  35 项 TAP 断言）——实跑全 ok
- src/tests 8 个示例 executable()（+gtk4 启用后 8 个 -gtk4 示例）不注册
  test()——构建级验证（138 编译目标全绿）
- test_package 消费者测试：nma_bar_code_new/get_size（QR 编码管线，
  无显示依赖）6 断言实跑通过

## 头文件布局

include/libnma/nma-*.h（gtk3/gtk4 变体同名同路径）；includedirs 声明
["include"]，消费者 #include <libnma/nma-bar-code.h>（带前缀拼法，与
本体包形成显式二选一）。
