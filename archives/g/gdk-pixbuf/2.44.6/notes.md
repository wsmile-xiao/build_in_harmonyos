# gdk-pixbuf 2.44.6 适配笔记

## 适配目标

- 将旧式编译记录迁移为可复现的 Conan 2.x 配方。
- 使用已发布的 `glib/2.84.0.1` 生成 marshal/enums，不提交预生成源码。
- 显式启用 PNG、JPEG、TIFF、GIF，并将全部可构建加载器内置到主库。
- 编译并执行上游 `tests/meson.build` 登记的 23 个测试程序。

## 依赖

- `glib/2.84.0.1`
- `libpng/1.6.58`
- `libjpeg-turbo/3.2.0`
- `libtiff/4.7.2`
- `zlib/1.3.1.1`

上述依赖已在全新 Conan home 中通过 `conan download --only-recipe` 验证可用。

取源仍以 `conandata.yml` 中的 GNOME 官方地址为准。真机网络不稳定时，可把同一官方 tarball 暂存为 `~/Download/gdk-pixbuf-2.44.6.tar.xz`；配方会先校验相同 SHA256，再解压该文件。

## 构建策略

配方通过 `PkgConfigDeps` 和 `MesonToolchain` 提供依赖与 OHOS 工具链。`gio_sniffing`、GObject Introspection、文档、man page 和 thumbnailer 不属于核心库能力，分别因缺少 shared-mime-info、g-ir-scanner、gi-docgen/rst2man 而关闭。

上游 Meson 请求 `gmodule-no-export-2.0`，而 GLib 的 Conan 组件只生成可重定位的 `gmodule-2.0.pc`。配方由后者生成 `gmodule-no-export-2.0.pc` 别名，保留 Conan package 路径、依赖声明和上游读取的 `gmodule_supported=true` 变量，禁止回退下载 GLib 子项目。

GLib 的 Conan 组件不会把原始 `glib-2.0.pc` 中的生成器变量和 `-lintl` 复制到新生成的 pkg-config 文件。配方把 `glib-genmarshal`、`glib-mkenums`、`gobject-query` 指向构建目录中的可执行副本，并恢复来自同一 GLib 包的 `libintl` 链接；`glib-compile-resources` 复制到最终构建路径后重签名，避免使用系统旧版工具。

加载器使用 `builtin_loaders=all` 内置。这样既保留 PNG/JPEG/TIFF/GIF 功能，也不需要安装后生成包含 Conan cache 绝对路径的 `loaders.cache`，并避免独立加载器模块在安装后逐个重签名。

HarmonyOS PC 的 `/tmp` 对普通用户只读。配方将 `TMPDIR`、`TMP`、`TEMP` 统一设置为 Conan build 目录下的可写临时目录，避免 Clang sanity check 因无法创建临时文件而失败。

上游测试资源在主构建尚未结束时运行刚生成的 `gdk-pixbuf-pixdata`。构建环境显式加入构建树主库目录，保证该工具只加载本轮刚链接的 `libgdk_pixbuf-2.0.so.0`，而不是系统或旧安装副本。

Meson 在 OHOS 平台不会自动生成版本化共享库的 SONAME 软链接。配方先单独构建主库，再复制生成 `.so.0` 和 `.so` 别名后继续资源与测试目标；安装目录执行相同处理，保证构建期工具和下游消费者都能解析 SONAME。

## 测试策略

- 非交叉构建：`build()` 运行完整 `meson test -v`。
- 交叉构建：只编译目标产物；全部上游测试和新增消费测试在 HarmonyOS PC 原生执行。
- `test_package/test.c` 提供 15 项真实 API 检查，覆盖像素缓冲区创建、像素访问、四种格式注册、PNG 内存编解码和缩放。

## 当前状态

配方已在两台独立 HarmonyOS PC 上使用不同的全新 Conan home 完成验证。两台设备均从源码完成 `conan create`，上游 Meson 测试 23/23、消费测试 15/15，且自然退出 0。两次构建的 RREV 均为 `dd84a01ac263b78875a2b828a950ac1a`，Package ID 均为 `b0af90e1159efd308fd932b896270a6e02817540`。

软件包包含 129 个普通文件，三个命令行程序及主库均为 AArch64 ELF。主库的普通文件别名 `.so`、`.so.0`、`.so.0.4400.6` 均存在，动态依赖包含 GLib、libintl、PNG、JPEG 和 TIFF，安装产物带 `.codesign` 节。完整设备、日志哈希和配方输入哈希见 `reports/device-test-20260731.md`。

当前状态为 `built`，表示配方和目标端测试已通过但尚未由合并后的发布流水线上传；在制品上传成功前不得标记为 `published`。
