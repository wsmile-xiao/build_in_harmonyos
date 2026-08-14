# girara 2026.07.07 编译笔记

## 编译信息
- **编译日期**: 2026-07-16
- **构建系统**: meson (>=1.5) + ninja
- **平台**: HarmonyOS (OpenHarmony) aarch64
- **许可证**: Zlib

## 软件简介
girara 是 zathura 文档查看器使用的用户界面库，提供数据结构（列表/树节点）、输入历史、模板、日志等通用工具。本版本（2026.07.07）只含 datastructures/utils/template/log 等核心模块，无 GTK 依赖。

## 依赖处理
glib-2.0 / gobject-2.0 / gio-2.0 由 Conan 依赖 `glib/2.84.0` 提供，并通过 PkgConfigDeps 暴露给 meson。根据 R36，必须先将 `glib/2.84.0` 发布到 Conan Registry，再构建 girara。

## 主要问题及解决方案

### 问题1: tests subdir 无条件构建
- **问题**: 上游 meson.build 末尾 `subdir('tests')` 无条件执行，会在包构建时编译测试可执行文件。交叉编译环境构建/签名测试可执行文件无意义且增加失败面。
- **解决**: 补丁 0001 新增 `tests` 布尔选项（默认 false），将 `subdir('tests')` 条件化。构建时传 `-Dtests=false` 跳过。

### 问题2: doxygen 文档
- **问题**: doc subdir 调用 doxygen 生成 API 文档。
- **解决**: 上游已有 `docs` feature 选项，传 `-Ddocs=disabled` 禁用。

### 问题3: meson wrap 下载
- **问题**: meson 可能尝试下载 wrap 子项目。
- **解决**: 传 `--wrap-mode=nodownload`，依赖全部由系统 pkg-config 提供。

### 问题4: 共享库签名
- **问题**: meson install 重写 rpath 会改动链接后的 .so，破坏链接器自签，OHOS dlopen 报 Permission denied。
- **解决**: package() 后用 llvm-objcopy 剥旧 .codesign 段，再 binary-sign-tool -selfSign 1 重签。

## 测试
test_package 用 dlopen 加载 libgirara.so，dlsym 解析 girara_list_new / girara_list_size / girara_list_free 三个真实导出 API 并调用：新建列表（传 NULL 释放回调，与上游 girara_list_new(girara_list_free_func_t) 真实签名一致）→ 校验 size==0 → 释放。使用与上游 types.h 一致的 struct girara_list_s 不透明类型声明，避开 glib.h 系统头依赖并保持函数指针签名一致。运行期 dlopen 验证仅在本机（非交叉编译）构建时执行；CI 交叉编译场景下 test() 因 cross_building 跳过运行期，仅验证编译+链接（见 test_package/MANIFEST.yml runtime: native-only）。

---
*编译者: OpenHarmony PC 暑假比赛参赛者*
*日期: 2026-07-16*
