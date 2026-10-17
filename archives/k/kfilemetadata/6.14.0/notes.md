# kfilemetadata 6.14.0 适配笔记

## 编译环境
- 构建系统: cmake（init-build 误标 autotools，以源码 CMakeLists.txt 为准）
- 编译日期: 2026-08-28
- 编译器: clang/clang++ 15 (aarch64-linux-ohos)
- 状态: built

## 编译步骤

conan 配方驱动（conan create，等同干净构建）：

```bash
cd archives/k/kfilemetadata/6.14.0
conan create . \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

configure 关键变量（conanfile.py generate()）：
- `KF_IGNORE_PLATFORM_CHECK=TRUE`：OHOS 不在 KDE 平台白名单，绕过。
- `BUILD_SHARED_LIBS=ON`、`BUILD_TESTING=ON`（上游 autotests 编译并在 build() 阶段
  经 ctest 实跑，纯 API 子集 12/21 通过，见「验证结果」）。
- `CMAKE_DISABLE_FIND_PACKAGE_{Poppler,Taglib,LibExiv2,FFmpeg,EPub,CatDoc,QMobipocket6,libappimage}=ON`：
  显式关闭可选媒体后端，保持最小依赖（core 提取器不受影响）。
- `ECM_MODULE_PATH` 手工设置为 ecm 包的 modules/find-modules/kde-modules
  （CMakeDeps 生成的 ECMConfig.cmake 不传播该变量，否则 FindKF6 等找不到）。
- `conan_cmakedeps_paths.cmake` 手工生成：qtbase 用 cmake_find_mode=none，
  CMakeDeps 不把其 lib/cmake 加进 CMAKE_PREFIX_PATH；把每个依赖的
  lib/cmake、lib、include 前置进去，find_package(Qt6 Xml/Gui) 与
  find_package(KF6 COMPONENTS ...)（经 FindKF6 → find_package(KF6Xxx CONFIG)）才能解析。
- `CMAKE_CXX_STANDARD=20` + `CMAKE_CXX_FLAGS=-std=c++20`：CMakeDeps 工具链默认 C++17，
  kcoreaddons 6.26.0 教训，统一用编译标志强制 C++20。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 Qt6LinguistTools 缺失 | `ki18n_install(po)` 内部 `ecm_install_po_files_as_qm` → `find_package(Qt6 LinguistTools REQUIRED)`，qtbase 未发布 LinguistTools 组件 | 补丁 `patches/0001-CMakeLists.txt.patch` 注释掉 `ki18n_install(po)`（与 kconfig/karchive 6.14.0 同法） |
| 2 | ECM_MODULE_PATH 为空 | CMakeDeps 生成的 ECMConfig.cmake 不设置该变量 | conanfile.py 中从 ecm.package_folder/share/ECM 手工设置 |
| 3 | find_package(Qt6 Xml) 找不到 | qtbase cmake_find_mode=none，CMakeDeps 不生成其路径 | 手工写 conan_cmakedeps_paths.cmake 前置 qtbase lib/cmake |
| 4 | .build-context 误标 autotools | init-build 按默认启发式判断 | 手工核对 CMakeLists.txt，manifest build_system 改为 cmake |
| 5 | 媒体后端意外启用风险 | 宿主机/CI 环境可能自带系统 poppler/taglib 等 | CMAKE_DISABLE_FIND_PACKAGE_* 显式关闭全部可选后端 |

## 源码修改

- `patches/0001-CMakeLists.txt.patch`：注释 `ki18n_install(po)`（禁用 .qm 翻译安装，
  qtbase 无 Qt6LinguistTools）。

## 依赖版本

- qtbase/6.11.1（Qt6Core/Gui/Test/Xml）
- karchive/6.14.0、kconfig/6.14.0、kcoreaddons/6.14.0、ki18n/6.14.0、kcodecs/6.14.0
- ecm/6.20.0（build tool_requires）

## 验证结果

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 构建通过（BUILD_TESTING=ON，build() 阶段实跑上游 autotests）
# ctest: 57% tests passed, 9 tests failed out of 21
# 通过的 12 项：propertyinfotest_en/localized、typeinfotest_en/localized、
#   externalextractortest、xmlextractortest、pngextractortest、externalwritertest、
#   dump_fail、dump_meta、dump_fulltext、dump_meta_svg
# 失败的 9 项均为 OHOS 环境差异（mimetype 数据库缺失条目/xattr 权限语义/字符集探测），
#   逐条说明见 reports/test-report.md §3.2
# 未注册 9 项：媒体后端测试（Poppler/Taglib/LibExiv2/FFmpeg/EPub/Mobipocket/AppImage），
#   因 CMAKE_DISABLE_FIND_PACKAGE_* 关闭，见 reports/test-report.md §3.3
# test_package 冒烟测试:
# PASS: KFileMetaData SimpleExtractionResult + PropertyInfo OK
# ctest: 1/1 Test #1: test_kfilemetadata Passed
```

产物：`lib/libKF6FileMetaData.so` + 10 个核心提取器插件
（plaintext/po/xml/postscriptdsc/odf/office2007/office/png/fb2/krita）
+ `bin/kfilemetadata_dump6` + CMake 配置 + 公共头文件。

## 注意事项

- 可选媒体后端（Poppler/Taglib/LibExiv2/FFmpeg）默认关闭，本任务保持最小依赖；
  后续如需启用，在 conanfile.py 增加对应 requires 并去掉对应
  CMAKE_DISABLE_FIND_PACKAGE_* 即可，插件会由 CMake 自动纳入。
- 上游 autotests 已开启（BUILD_TESTING=ON）并在 build() 阶段实跑：21 个可注册
  测试中 12 个通过（57%）；9 个失败为 OHOS 环境差异（mimetype 库缺失条目、
  xattr 权限语义、字符集探测），9 个媒体后端测试因后端关闭未注册——均逐条说明，
  详见 reports/test-report.md。

## ⚠️ R40 需人工确认（依赖链 SONAME 限制）

- **现象**：W3 L5b 门禁失败——libKF6FileMetaData.so 的 DT_NEEDED
  含机器特定绝对路径（指向 conan 缓存中 ki18n/kcoreaddons 的 .so）。
- **根因**：制品仓 ki18n/6.14.0、kcoreaddons/6.14.0 老包自身无
  DT_SONAME（readelf 已证实），链接器只能记录绝对路径。
- **非本配方缺陷**：本包自身 DT_SONAME 已通过（L5a，产物含
  .so.6.14.0/.so.3/.so 版本化软链链），conanfile.py 已注入
  CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG=-Wl,-soname,。
- **发布风险**：打包的 libKF6FileMetaData.so 脱离 conan 缓存环境
  部署/加载可能失败；修复需重发 ki18n/kcoreaddons 依赖包（补
  SONAME）并重链本包。
- **结论**：依赖链既有限制，需人工确认适配完整性后再发布。
---

**编译结束**: 2026-08-28 21:39
**最终状态**: built
