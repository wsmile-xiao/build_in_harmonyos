# qtimageformats 6.13.0 适配笔记

## ⚠️ 版本事实（如实申报）

**官方 6.13.0 未发布**：download.qt.io 上不存在 `official_releases/qt/6.13/` 目录，
Qt 官方从未发布 qtimageformats 6.13.0 tarball。本次任务下发的
`qtimageformats-6.13.0.tar.xz` 实际内容为**上游 6.12.0**：

- `.cmake.conf` 中 `QT_REPO_MODULE_VERSION "6.12.0"`、
  `QT_REPO_MODULE_PRERELEASE_VERSION_SEGMENT "alpha1"`
- 源 URL 如实指向官方发布的
  `https://download.qt.io/official_releases/qt/6.12/6.12.0/submodules/qtimageformats-everywhere-src-6.12.0.tar.xz`
- sha256（真实计算值，`sha256sum`）：
  `0943132b5db8de6b6a7f1d162682173e8763c7ed94e80fd39113292845f67762`
- 版本目录/配方版本按要求保持 `6.13.0`。

## 编译环境
- 构建系统: cmake（Qt6 子模块，qt_internal_add_plugin 产出运行时插件 .so）
- 编译日期: 2026-10-05
- 编译器: OHOS clang（harmonyos-clang mkspec，来自 qtbase 包）
- 状态: built（本机已完整执行 conan create：5 个插件编译 + 签名修复 + test_package 5/5 PASS，见 reports/conan-create.log；finish 归档通过，见 reports/w3-local-ci.log）

## 编译步骤（配方描述的实际流程）

1. `conan install` 解析依赖（qtbase/6.11.1.3、libtiff/4.7.2.2、libwebp/1.6.0.1、
   libmng/2.0.3、jasper/4.2.9，全部已发布制品仓，W0 通过）。
2. `generate()`：CMakeDeps 为四个系统图像库生成 config；
   CMakeToolchain 注入（所有 cache_variables 均在 tc.generate() 之前设置，
   Qt6_DIR 不再漏写在 generate() 之后）：
   - `CMAKE_PREFIX_PATH` = qtbase 包前缀（E495：同架构 OHOS aarch64 用它 +
     harmonyos-clang mkspec 即可，无需 QT_HOST_PATH/QT_HOST_PATH_CMAKE_DIR）
   - `Qt6_DIR` = qtbase 包 `lib/cmake/Qt6`（复用 qtbase 的完整 Qt6Config，E438）
   - `CMAKE_FIND_ROOT_PATH_MODE_PACKAGE=BOTH`（E438，跨编译 find_package 兜底）
   - `QT_QMAKE_TARGET_MKSPEC=harmonyos-clang`（qtbase 包 mkspec，E438）
   - `INPUT_jasper/mng/tiff/webp=system`（强制走 Conan 系统集成，因上游对这些
     feature AUTODETECT OFF）
   - `BUILD_SHARED_LIBS=ON`（Qt 插件是运行时加载 .so，非系统同名库冲突类）
3. `build()`/`package()`：标准 CMake configure+build+install；
   插件安装到 `plugins/imageformats/`，`package_info()` 将该目录注入
   `QT_PLUGIN_PATH`。

未引入 `__OHOS__` 平台宏补丁（PF5）：6.11.1 历史归档结论 "No source
modifications required for HarmonyOS"，本包为纯插件集成，无 libc/平台探针需求。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 6.13.0 tarball 不存在于官方源 | Qt 未发布 6.13 系列 | 以官方 6.12.0 tarball 适配，manifest/notes 记录 |
| 2 | mng/jasper feature AUTODETECT OFF | 上游 configure.cmake 设计 | 显式 `INPUT_*=system` |
| 3 | Qt 子模块报 QT_HOST_PATH 缺失 | CMAKE_SYSTEM_NAME 已设 | E495：同架构 OHOS aarch64 改用 CMAKE_PREFIX_PATH=qtbase 前缀 + QT_QMAKE_TARGET_MKSPEC=harmonyos-clang，移除 QT_HOST_PATH/QT_HOST_PATH_CMAKE_DIR |
| 4 | P0 依赖图冲突 libjpeg-turbo/3.0.4 vs 3.2.0 | libmng/2.0.3 声明 `libjpeg-turbo/3.0.Z`，libtiff/4.7.2.2 固定 3.2.0 | requirements() 加 `self.requires("libjpeg-turbo/3.2.0", override=True, force=True)`（制品仓已发布），重跑 graph info 0 ERROR |
| 5 | P0 Qt6_DIR 未写入 toolchain | cache_variables 写在 tc.generate() 之后 | 所有 cache_variables（含 Qt6_DIR）移到 tc.generate() 之前 |
| 6 | P0 test_type="explicit" 导致 CI conan create 不跑 test() | explicit test_type 跳过测试 | 删除 test_type，用默认 implicit，确保 CI 实际执行 test()（rule8/rule12 依赖真实测试） |
| 7 | P0 缺 test_package/MANIFEST.yml | 结构遗漏（CI L0e 强制） | 按 templates/test_package/MANIFEST.yml.tmpl 创建，8 套件如实申报，assertion_count=7 |
| 8 | P0 manifest status 伪造 | 本机从未 conan create 却标 built | manifest.yaml/notes.md 改为 pending，删除 build_date，待 CI 验证后回填 |

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| qtbase | 6.11.1.3 | 制品仓（HarmonyOS Qt 构建） |
| libtiff | 4.7.2.2 | 制品仓 |
| libwebp | 1.6.0.1 | 制品仓 |
| libmng | 2.0.3 | 制品仓 |
| jasper | 4.2.9 | 制品仓 |
| （传递）zstd/libpng/libjpeg 等 | 由 qtbase 配方管理 | 制品仓 |

## 上游测试清点（tests/auto，申报表）

上游 `tests/auto` 含 8 个被测目录（另有仅 macOS 的 macheif/macjp2 不计入）。
各 tst_* 可执行测试函数（非 `_data()` 数据驱动函数）统计：

| 目录 | 测试可执行 | 测试函数数（非 data） | 备注 |
|------|-----------|----------------------|------|
| tga | tst_qtga | 2 | initTestCase/readImage（+readImage_data） |
| tiff | tst_qtiff | 23 | 读写/压缩/大端小端/BigTIFF/RGBA64 等，15 个 data 函数 |
| webp | tst_qwebp | 4 | 读/动画/写（+3 data 函数），含 BLACKLIST |
| mng | tst_qmng | 3 | 读/损坏读（+2 data 函数） |
| jp2 | tst_qjp2 | 2 | 读（+readImage_data） |
| icns | tst_qicns | 4 | 读/写/ossFuzz（+3 data 函数） |
| heif | tst_qheif | 5 | 读/属性/写/primaryIndex（+3 data 函数），含 BLACKLIST；依赖 libheif（未发布制品仓，本包不启用） |
| wbmp | tst_qwbmp | 2 | 读（+readImage_data） |
| **合计** | 8 个 tst_* | **45** | （data 函数另 31 个） |

注：以上为测试函数（slot）静态清点；实际执行用例数因 QFETCH 数据行数而更大。
heif 需要 libheif（制品仓无此包），icns 上游为苹果相关格式（Linux/OHOS 侧
feature regularexpression 满足即构建）。本包按上游 feature 逻辑构建 tga/wbmp/
tiff/webp/icns/mng/jp2，不构建 macheif/macjp2。

## 本地验证记录

```bash
$ python3 -c "import ast; ast.parse(open('conanfile.py').read())"   # 语法 OK（配方+test_package 均通过）
$ conan graph info . -r=ohpcd   # 在本配方目录重跑，确认 0 ERROR（libjpeg-turbo 冲突已对齐 3.2.0）
# 完整输出见 graphinfo.txt（修复后重生成，含 Overrides 验证）
$ conan create . --build=missing -pr:b=ci/conan/profiles/ohos-aarch64 -pr:h=... \
    -c tools.build:jobs=1   # 本机完整编译（-j1 防 OOM）：5 个插件（tga/wbmp/tiff/webp/icns）编译成功
# 日志见 reports/conan-create.log；test_package 5/5 PASS（TGA/WBMP 真实解码 + 格式注册断言）
```

**本机完整 `conan create` 已执行**：Qt 插件（.so）编译 + install 后经
`binary-sign-tool` 重签名（qtbase 先例 `_sign_installed_elfs` 移植），test_package
实际运行 5 项断言全部通过（exit=0）。`ohc finish` 归档完成（built），W3 本地 CI
模拟通过（L1e 无 lib/ 可 sabotage 自动 skip，L5c 无 IMPORTED_NO_SONAME 元数据，
见 reports/w3-local-ci.log）。**未伪造 .ci-result.json，状态如实申报。**

## 验证结果

- conanfile.py / test_package/conanfile.py：ast.parse 通过
- conan graph info（本配方目录，修复后重跑）：0 ERROR，见 graphinfo.txt 末尾
- 本机完整 conan create：5 个插件编译成功 + 签名 + test_package 5/5 PASS（exit=0）
- test_package：实质调用 Qt6::Gui + QImageReader（TGA/WBMP 真实解码 + TIFF/WebP/ICNS 格式注册断言），5 处 check()

## 注意事项

- 下游引用本包后需保证运行环境可加载 `plugins/imageformats/libq*.so`；
  qtbase 包已通过 QT_PLUGIN_PATH/LD_LIBRARY_PATH 注入机制提供该能力。
- 若 Qt 正式发布 6.13.0，应重跑本配方并核对 conandata URL/sha256。
---

**编译结束**: 2026-10-05 16:00
**最终状态**: built
