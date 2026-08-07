# libsignon-glib 2.1 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-07
- 编译器: clang/clang++
- 状态: built

## 问题与解决方案

### 1. D-Bus XML 文件路径错误
- 问题: meson.build 中 D-Bus 接口 XML 路径为 `interfaces/` 子目录，但文件实际在 `libsignon-glib/` 目录
- 解决: 修改路径移除 `interfaces/` 前缀

### 2. gtkdoc 依赖
- 问题: docs/reference/meson.build 无条件调用 gnome.gtkdoc()，需要 gtkdoc-scan
- 解决: 使用 documentation 选项保护 docs subdir

### 3. Conan glib pkg-config 变量缺失
- 问题: Conan 生成的 gio-2.0.pc 和 glib-2.0.pc 缺少 gdbus_codegen、glib_mkenums、glib_genmarshal 变量
- 解决: 在 generate() 方法中补丁 .pc 文件添加这些变量

### 4. 共享库运行时签名
- 问题: HarmonyOS 要求 ELF 签名才能加载共享库，本地构建的 .so 未签名
- 解决: 默认构建静态库 (shared=False)，CI 发布时由 sign.sh 签名

## 验证命令
- conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable
- conan-verify: G1 PASS, G2 PASS, G3 PASS, G4 PASS

---
**编译结束**: 2026-08-07
**最终状态**: built
