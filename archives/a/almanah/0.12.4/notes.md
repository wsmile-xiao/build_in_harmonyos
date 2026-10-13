# almanah 0.12.4 适配笔记（OHOS PC aarch64）

## 上游形态
GNOME 加密日记应用（GPL-3.0+），meson 构建，C 主体（35 源文件 100% C）。
源：https://download.gnome.org/sources/almanah/0.12/almanah-0.12.4.tar.xz
sha256 0f2c16e8692885fd25ad7dccc3f51ac2b4b887624e68e7ea1f64ae9479319452

## 依赖（全部制品仓已发布）
gtk/3.24.43、gtksourceview4/4.8.4、libcryptui/3.12.2（cryptui-0.0.pc 别名）、
sqlite3/3.53.4、libsecret/0.21.7、gpgme/1.24.2、enchant/2.8.2
（+ 传递：glib/2.84.0.1、dbus-glib、libgpg-error、libassuan 等）

## 依赖图冲突与解法（gcr 互斥）
- gcr-base/3.41.2 钉死 glib/2.84.0，gtk/3.24.43 链是 glib/2.84.0.1（精确互斥）；
- gcr-base 无 2.84.0.1 二进制 → replace 重定向后从源码构建 → 链接缺 gobject 符号（配方侧死路）；
- 反向重定向（.1→2.84.0）又撞 dbus-glib 钉 pcre2/10.40 vs glib 钉 pcre2/10.45 二连冲突，replace 全栈无二进制；
- **最终解法**：gcr 只是 vfs.c 的安全内存增强（上游注释明示 malloc fallback 语义），打 portability
  补丁 0001-0004 把 gcr 可选化（HAVE_GCR 守卫 + gcr feature 选项），配方 -Dgcr=disabled，
  用 deps4 无 gcr 组合（全部二进制，零冲突）。 secure memory 回退普通分配 = 上游设计内行为。

## 交叉构建流程（conanfile build() 固化，探索期实测）
1. cross file（c/pkg-config/llvm-ar 路径，linux-aarch64）+ --wrap-mode=nodownload；
2. 特性裁剪：gcr/translations/evolution/spell_checking=disabled；
   - translations=disabled 顺带跳过 data/ 的 desktop/appstream i18n.merge_file
     （需 gettext ITS 规则，宿主工具链数据不全 → msgfmt "cannot locate ITS rules" 失败）；
3. 宿主工具垫片（ohc-tools，进 PATH）：
   - gtk-update-icon-cache / update-desktop-database stub（post-install 钩子，OHOS 无桌面集成）；
   - glib-compile-resources wrapper：hnp 版过旧不识 meson 1.11 的 --dependency-file
     （只影响增量依赖清单不影响产物），过滤后转发 + 补 libffi LD_LIBRARY_PATH；
   - glib-mkenums：hnp 工具链缺，从 tool_requires glib 包复制（python 脚本平台无关）；
4. c_link_args=-lintl：链接 g_libintl_gettext（glib 制品 libdir 自带 libintl.so.8）；
5. PKG_CONFIG_PATH 指 PkgConfigDeps 生成目录（含 cryptui-0.0.pc 等 52 个 .pc）。

## HMDFS exec 陷阱（E046 同源，本包实测最完整证据链）
- 包缓存二进制（meson install --destdir 版，RPATH 重写过）exec 报 EPERM；
- ld 直出版（build/src/almanah，带 RPATH）可执行；字节级复制两版到同一目录同 mode：
  构建版 OK、installed 版 126 —— 内容差异决定（4096 字节，install 改写）；
- test() 中 umask 000 副本无效（copyfile 666 无 x 位，chmod 被忽略）→ 改为 package()
  直接打包 ld 直出版 + test() 语义用该产物（同 oddjob 先例）；
- package() 顺序坑：destdir bin/* 先拷、ld 直出版**最后覆盖**（否则被 2452160 旧字节回写）。

## test_package 演进（消费者测试，R34/R51）
- 初版：链接 sqlite3/gpgme/glib 复刻 vfs 数据链路 —— 沙箱 include 目录发现逐包猜
  （gpgme.h→gio.h→sqlite3.h）不可收敛，弃；
- 终版：纯 libc —— ①包内产物 ELF64 LE aarch64 magic（真实读文件）；
  ②运行包内二进制 --help：加载器解析全部传递 .so 到达 gtk_init（headless 沙箱
  display-open 失败为预期环境限，Gtk 输出证明依赖链完整加载）；
  运行环境经 VirtualRunEnv（conanrun.sh，手工聚合 libdirs 漏库实证 exit 126）。

## 上游测试（R51 三步法，详见 reports/test-report.md）
- 清点：tests/vfs-test 3 用例（plain/data/encrypted）+ 桌面校验 2 项（不适用）；
- 实跑：plain、data 逐用例 ok（GSETTINGS_SCHEMA_DIR 编译到临时目录后），2/3 真实通过；
- encrypted：gpgme 初始化 0x07000056=GPG_ERR_INV_ENGINE——gpgme 制品缺 gpg 引擎
  （依赖侧缺口，非库缺陷，如实标注）。

## conan-verify
G1/G2/G3 + L2/L4/L5 全绿（reports/conan-verify-report.md）。
---

**编译结束**: 2026-10-12 12:44
**最终状态**: published
