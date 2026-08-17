# desktop-file-utils 0.28 编译笔记（HarmonyOS PC · 标准 Conan meson）

## 定位
- .desktop 文件工具集：desktop-file-validate / desktop-file-install / update-desktop-database。
- 纯 CLI 工具（package_type: application），无 GUI 依赖。

## 关键适配
- **meson 构建**：meson.build 声明 `dependency('glib-2.0', >=2.26)` 与 `dependency('gio-2.0', >=2.26)`，
  均由 conan glib/2.84.0 配方的 PkgConfigDeps 提供。
- **ar/ranlib 注入**（`_inject_meson_archiver`）：OHOS 的 clang 工具链在 /data/service/hnp/bin，
  默认 PATH 无 llvm-ar → meson configure 报 "Unknown linker(s)"；把 ar/ranlib 全路径写入
  conan_meson_native.ini 的 [binaries] 段（pango/cairo 同款方案）。
- **wrap_mode=nodownload**：禁止 meson 偷偷下载 wrap 子项目，依赖一律走 conan。
- **代码签名**（`_sign_binaries`）：鸿蒙 PC XPM 要求被 exec 的可执行文件代码签名，
  binary-sign-tool 自签 bin/ 下 ELF。

## 上游测试
- 上游无标准测试套件（纯 CLI 工具），test_package 冒烟验证 `desktop-file-validate --version`。

## 依赖版本
- glib-2.0/gio-2.0: 2.84.0（conan glib/2.84.0 配方）

## 状态
built（CI conan create + test 通过）
