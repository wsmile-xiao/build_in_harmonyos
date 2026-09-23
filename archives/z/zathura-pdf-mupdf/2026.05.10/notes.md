# zathura-pdf-mupdf 2026.05.10 适配笔记

## 编译信息
- **编译日期**: 2026-09-17
- **构建系统**: meson + ninja
- **平台**: HarmonyOS (OpenHarmony) aarch64
- **许可证**: MIT（vendoring 的 zathura 头文件为 Zlib 许可，SPDX 头保留）

## 软件简介
zathura-pdf-mupdf 是 zathura 文档查看器的 PDF 插件，使用 MuPDF 渲染引擎。

## Conan 适配（v3，接续修复 PR #4853）
插件为运行时 dlopen 对象：静态内嵌 MuPDF，经 DT_NEEDED 引用 girara/cairo，
zathura_*/girara 符号由宿主进程解析——构建无需 libzathura。

### Conan 依赖（全部已在制品仓发布）
| Dependency | Conan Version | 说明 |
|-----------|---------------|------|
| girara | 2026.07.07 | UI 库（其 .so 已静态内嵌 glib，导出 4096+ g_ 符号） |
| glib | 2.84.0 | GLib（与 girara/gtk 依赖链对齐，注意 gtk/3.24.x 锁 glib/2.84.0.1 会冲突） |
| cairo | 1.18.4 | 2D 图形 |
| mupdf-tools | 1.27.2 | 提供 libmupdf.a + libmupdf-third.a（PIC）与全部 mupdf/ 头文件 |

### pkg-config 依赖
| Dependency | 状态 | 说明 |
|-----------|------|------|
| zathura | 未发布（PR #8136 open） | 公共插件 API 头从 zathura 2026.05.20 vendoring（补丁），无链接期依赖 |
| mupdf | 由 mupdf-tools 提供 | generate() 手写 mupdf.pc（Libs: -lmupdf -lmupdf-third -lm，同 Debian libmupdf-dev） |

### 配方关键点
- MesonToolchain: c_std=c2x（clang 15 不支持 C23）、tests=disabled、pdf=enabled、
  plugindir=lib/zathura（zathura 自身 meson 的默认 plugindir，同时免去 pkg-config 变量查询）、
  wrap_mode=nodownload
- 生成 mupdf.pc 指向 mupdf-tools 包根，满足 `dependency('mupdf', version: '>=1.26')`
- llvm-ar/llvm-ranlib 全路径注入 conan_meson_native.ini [binaries]（沿 girara 模式）
- OHOS 共享库签名：llvm-objcopy 剥旧 .codesign + binary-sign-tool -selfSign 1 重签
- 链接保险：CI worker 的 OHOS SDK lld 依赖 libxml2.so.16（SDK 自身 llvm/lib 内，
  不在默认 loader 路径），build() 将该目录前置到 LD_LIBRARY_PATH（无 libxml2 则 no-op）
- test_package 用 -rdynamic 提供 zathura_* 宿主 API 桩（17 个符号），dlopen 验证
  导出符号 zathura_plugin_6_7、插件名、版本与 mimetype 表（含 application/pdf）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CI failed（08-26/27，6 次） | test_package 用 CMake，TryCompile 链接时 OHOS SDK lld 无法加载 libxml2.so.16 | 重写为直接 cc 编译（无 CMake）；主配方 build() 前置 SDK lib 目录到 LD_LIBRARY_PATH |
| 2 | CI failed（09-04） | main 分支误入 test_push.txt 触发 G0e 白名单 | main 已清理（36cf4efc34），本分支无需处理 |
| 3 | meson 找不到 zathura | zathura 无 conan 包（PR #8136 未合入） | vendoring zathura 2026.05.20 公共插件 API 头（Zlib 许可），declare_dependency 替代 pkg-config 查询 |
| 4 | meson 找不到 mupdf | mupdf 库包未发布；mupdf-tools 已发布且含完整库+头 | requires mupdf-tools/1.27.2 + generate() 手写 mupdf.pc |
| 5 | glib 版本冲突 | gtk/3.24.x 锁 glib/2.84.0.1，girara 锁 glib/2.84.0 | 放弃 gtk 依赖：links.h 的 GdkAtom 为不透明指针，前向声明即可（插件源码零 GTK 调用） |
| 6 | document.c 编译失败 | 上游 `#include <glib-2.0/glib.h>` 依赖系统默认 include 根 | 补丁改为标准 `<glib.h>` |
| 7 | dlopen 失败 symbol not found | musl dlopen 严格重定位，插件对宿主 zathura_* 符号无提供者 | test.c 以 -rdynamic 提供 17 个 zathura_* 桩（模拟宿主角色，函数体不执行） |
| 8 | meson tests 选项报错 | tests 为 feature 型选项 | "disabled" 而非 "false" |

## 上游测试用例清点（R51）
上游 tarball 无测试目录（仅 AUTHORS/LICENSE/README/data/meson.build/
meson_options.txt/zathura-pdf-mupdf 源码），meson_options 的 tests 选项
仅控制 zathura 上游的 plugin 注册测试（依赖 zathura 本体），故 tests=disabled。
适配后 test_package 提供 4 项断言（dlopen/符号/名称版本/mimetype）。

## 验证结果（本地 conan create，ohos-aarch64-local profile）
```
zathura-pdf-mupdf: dlopen libpdf-mupdf.so ok (host API relocations bound)
zathura-pdf-mupdf: plugin pdf-mupdf, plugin version 2026.5.10
zathura-pdf-mupdf: plugin ABI verified (12 mimetypes, application/pdf supported)
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（meson + 4 个已发布 conan 依赖） |
| conandata.yml | 源码与补丁声明 |
| patches/0001-meson-conan-build-zathura-headers.patch | vendoring zathura 头 + meson/document.c 移植 |
| test_package/test.c | dlopen + ABI 验证（含宿主 API 桩） |
| test_package/conanfile.py | 测试包配方（VirtualRunEnv + -rdynamic） |
| test_package/MANIFEST.yml | 测试清单 |

## 注意事项
- zathura conan 包（PR #8136）合入后，vendoring 头可替换为正式依赖
- 插件 .so 内嵌完整 mupdf（~42MB），符号可见性遵循上游设计
- 插件安装路径 <prefix>/lib/zathura/（与 zathura plugindir 约定一致）

---
**编译结束**: 2026-09-17
**最终状态**: built (conan create 全流程通过：build + package + test)
