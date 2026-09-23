# kfilemetadata 6.28.0 适配笔记

## 编译环境
- 构建系统: cmake（3.29+ 最低要求，本机 cmake 4.1.2 满足）
- 编译日期: 2026-09-07
- 编译器: clang/clang++ 15 (aarch64-linux-ohos)
- 状态: built

## 版本背景（6.14.0 → 6.28.0 跟进）

上游 6.14→6.28 跨 14 个 minor 版本，关键变化：
- `find_package(ECM 6.28.0)`：需要 extra-cmake-modules 6.28.0（制品仓在仓 ✅，
  注意包名是 `extra-cmake-modules` 而非旧别名 `ecm`）。
- `set(KF_DEP_VERSION "6.28.0")`：上游对 KF6 依赖版本要求 6.28，但制品仓 KF6
  各框架最高在仓版本参差（karchive 6.19.0 / kcodecs 6.18.0 是短板）。
  **处理（主任务拍板）**：patch 降级 `KF_DEP_VERSION` 到 6.18.0——KF6 框架
  同 major（6.x）API/ABI 兼容，6.19/6.26 在仓版本满足 ConfigVersion 兼容规则。
- 新增 `check-struct-has-member`、`CheckStructHasMember` 无平台影响。
- `cmake_minimum_required(VERSION 3.29)`：本机/CI cmake 4.x 满足。

## 编译步骤

conan 配方驱动（conan create，干净构建）：

```bash
cd archives/k/kfilemetadata/6.28.0
conan create . \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 依赖版本（全部制品仓在仓实测，W0 conan download/install 核验）

| 依赖 | 版本 | 说明 |
|---|---|---|
| qtbase | 6.11.1 | Qt6Core/Gui/Test/Xml |
| extra-cmake-modules | 6.28.0 | 满足上游 ECM 6.28 版本墙（tool_requires） |
| karchive | 6.19.0 | 在仓最高版（6.26 不在仓）；binary 为 static |
| kconfig | 6.26.0 | |
| kcoreaddons | 6.26.0 | |
| ki18n | 6.26.0 | |
| kcodecs | 6.18.0 | 在仓最高版（6.26 不在仓） |
| taglib | 2.3 | **新增**：taglibextractor + taglibwriter 插件 |
| exiv2 | 0.28.7 | **新增**：exiv2extractor 插件 |
| openssl | 3.5.6 | 解锁 karchive 6.19 binary 的 KF6ArchiveConfig 链 |
| zlib | 1.3.1.1 | force=True：taglib 要 1.3.1 / exiv2 要 1.3.1.1，图内归一 |
| shared-mime-info | 2.4 | tool_requires：上游测试的 freedesktop mime 数据库（XDG_DATA_DIRS 注入，测试期数据不进消费者图） |

媒体后端仍禁用：Poppler/FFmpeg/EPub/CatDoc/QMobipocket6/libappimage
（`CMAKE_DISABLE_FIND_PACKAGE_*`，不在 OHOS 基线）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 Qt6LinguistTools 缺失 | `ki18n_install(po)` → `ecm_install_po_files_as_qm` → `find_package(Qt6 LinguistTools REQUIRED)`，qtbase 未发布该组件 | 补丁注释 `ki18n_install(po)`（6.14 同法） |
| 2 | configure 报 ECM 6.28.0 版本不满足 | 上游 `find_package(ECM 6.28.0)`，制品仓 ecm 别名包最高 6.26 | tool_requires 改用 `extra-cmake-modules/6.28.0`（制品仓在仓，同名包） |
| 3 | find_package(KF6 6.28) 找不到 Archive/Codecs | KF_DEP_VERSION=6.28 但 karchive 6.19/kcodecs 6.18 在仓 | 补丁降级 `KF_DEP_VERSION` 到 "6.18.0"（KF6 同 major 兼容，主任务拍板） |
| 4 | zlib 双版本冲突 | taglib→zlib/1.3.1，exiv2→zlib/1.3.1.1 | `configure()` 里 `self.requires("zlib/1.3.1.1", force=True)` 归一 |
| 5 | Taglib::Taglib target 未定义 | conan taglib/exiv2 是静态包，包自带 config 定义 `TagLib::tag`/`Exiv2::exiv2lib`（大小写不同）；ECM FindTaglib module 又不携带静态闭包（inflate* 链接错） | generate() 写 wrapper FindTaglib/FindLibExiv2 到 generators 目录：find_package(taglib/exiv2 CONFIG) 加载包自带 config（含 zlib/expat INTERFACE 闭包）+ alias 成 Taglib::Taglib/LibExiv2::LibExiv2 + 预定义 ZLIB::ZLIB/EXPAT::EXPAT |
| 6 | wrapper 不被调用（ECM FindTaglib 抢先） | CMakeLists L10 `set(CMAKE_MODULE_PATH ... ${ECM_MODULE_PATH})` 整体覆盖；ECMConfig.cmake 自己 set(ECM_MODULE_PATH) 普通变量覆盖 toolchain CACHE 值 | 补丁改 L10 为 `set(CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake" ${CONAN_GENERATORS_DIR} ${ECM_MODULE_PATH})`，conanfile 设 `tc.variables["CONAN_GENERATORS_DIR"]=generators`（普通变量不被 ECMConfig 覆盖） |
| 7 | CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON 绕过 wrapper | PREFER_CONFIG 使 find_package(Taglib) 直接命中包自带 taglib-config.cmake（定义 TagLib::tag，非 Taglib::Taglib） | 移除 PREFER_CONFIG（KF6/Qt6 的 find 链显式 CONFIG 不受影响） |
| 8 | KF6Archive target 报 PkgConfig::LibZstd / OpenSSL::Crypto 缺失 | karchive 6.19 binary 以 WITH_OPENSSL=ON 构建，其 KF6ArchiveTargets.cmake 引用 PkgConfig::LibZstd/OpenSSL::Crypto 接口 target | conan_cmakedeps_paths.cmake 里预定义这三个 target 为 UNKNOWN IMPORTED（指向 conan zstd/openssl 包产物）+ requires 加 openssl/3.5.6 |
| 9 | exiv2extractor.cpp clang 15 编译错 | 上游 6.28 用 C++20 结构化绑定捕获进嵌套 lambda（`reference to local binding ... declared in enclosing function`），clang 15 支持不完整 | 补丁把 `offsetTime` 复制为具名局部 `offsetTime_` 后再捕获 |
| 10 | qtpaths 运行失败（ECMQueryQt） | 沙箱 LD_LIBRARY_PATH 含不兼容 libc++_shared.so | build()/测试 env 前置 /system/lib64（kconfig 6.26/bluez-qt 6.28 先例） |
| 11 | 上游测试 mimetype 匹配大面积失败（kra→application/zip、ape/flac/ogg 不识别，10 项测试失败） | OHOS 无 /usr/share/mime，QMimeDatabase 仅剩 Qt 内置 mime 子集，MimeUtils::strictMimeType 识别退化导致提取器插件匹配不上 | `tool_requires("shared-mime-info/2.4")`（制品仓在仓，测试期数据不进消费者图）+ `_run_upstream_tests()` 把包内 `data/freedesktop.org.xml.in` 暂存到 `<build>/share/mime/packages/` + `XDG_DATA_DIRS` 前置该 share 根（kcalendarcore 6.26.0 注入 tzdata 同法）——26 测试 15 过→23 过 |
| 12 | conan.tools.files.copy() 单文件改名复制静默无操作 | copy(pattern, src, dst) 的 pattern 按文件名在 src **目录**里匹配，src 传具体文件路径时目录枚举不到该条目，既不报错也不产出目标文件（整轮 conan create 后 staged XML 缺失，XDG_DATA_DIRS 指向空目录） | 换 `shutil.copy(smi_xml, staged)` 标准库语义（单文件直拷）；conan copy 只适合"目录内 pattern 批量复制"场景 |

## 源码修改（patches/0001-CMakeLists.txt.patch，双文件三处）

1. `CMakeLists.txt`：`KF_DEP_VERSION` 6.28.0 → 6.18.0（在仓依赖天花板）。
2. `CMakeLists.txt`：`CMAKE_MODULE_PATH` 注入 `${CONAN_GENERATORS_DIR}`。
3. `CMakeLists.txt`：注释 `ki18n_install(po)`。
4. `src/extractors/exiv2extractor.cpp`：clang 15 结构化绑定兼容修复。

## 验证结果（2026-09-07 实测）

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 构建通过（BUILD_TESTING=ON，build() 阶段实跑上游 autotests）
# ctest（构建树，mime DB 注入后）：26 个测试注册，23 通过 3 失败（88%）
# 通过 23（mime DB 注入后 88%）：
#   datetimetest、propertyinfotest_en/localized、typeinfotest_en/localized、
#   externalextractortest、writercollectiontest、xmlextractortest、pngextractortest、
#   taglibwritertest（taglib 提取器真实写入验证）、externalwritertest、
#   dump_fail、dump_meta、dump_fulltext、dump_meta_svg、
#   extractorcoveragetest、odfextractortest（含 flat-xml）、officeextractortest
#   （含 3mf）、fb2extractortest（含压缩）、taglibextractortest（ape/flac/
#   ogg/opus/wavpack 全恢复）、extractorcollectiontest、
#   postscriptdscextractortest、kritaextractortest（test.kra 正确识别）
# 失败 3（逐项定性，非 mimetype 类）：
#   indexextractortest：4/17 子测试（win1251/GB18030/EucJp/win1251-html）——
#     qtbase QT_FEATURE_icu=OFF，QStringDecoder 不支持传统编码（探针实测：
#     prober confidence 0.98/0.99/1.0 但 decoder invalid）
#   exiv2extractortest：2/10 子测试（jxl/heif）——制品仓 exiv2/0.28.7 未启用
#     EXV_ENABLE_BMFF（exv_conf.h 实测 undef），jxl/heif 不在提取器 mime 表
#   usermetadatawritertest：2/9 子测试（MissingPermission/MetadataSize）——
#     OHOS 用户态 setxattr 权限语义差异
# 对照 6.14.0：当时 21 注册 12 通过 57%——6.28.0 现达 88%（23/26）
# test_package 冒烟测试:
# PASS: KFileMetaData SimpleExtractionResult + PropertyInfo + TypeInfo OK
# ctest: 1/1 test_kfilemetadata Passed
```

产物：`lib/libKF6FileMetaData.so`（含 DT_SONAME 注入）+ 12 个提取器插件
（plaintext/po/xml/postscriptdsc/odf/office2007/office/png/fb2/krita/
**taglib/exiv2**）+ taglibwriter 写入插件 + `bin/kfilemetadata_dump6`
+ CMake 配置 + 公共头文件。

## 与 6.14.0 相比的能力增强

- **taglib 提取器/写入器启用**（音乐元数据：mp3/ogg/flac/opus/m4a/wma...）
- **exiv2 提取器启用**（图片元数据：jpeg/webp/heif EXIF/IPTC/XMP）
- 提取器插件从 10 个增加到 12 个，写入器从 0 到 1（taglibwriter）。

## 注意事项 / 已知限制

- 可选媒体后端 Poppler/FFmpeg/EPub/Mobipocket/AppImage 仍禁用（不在 OHOS 基线）。
- KF_DEP_VERSION 降级到 6.18：制品仓 KF6 6.28/6.26 全系发布后可移除该补丁行。
- 上游测试 mimetype 类失败已通过 `tool_requires("shared-mime-info/2.4")` +
  XDG_DATA_DIRS 注入修复（58% → 88%）；剩余 3 项失败为依赖配置差异
  （qtbase 无 ICU / exiv2 无 BMFF）与 OHOS xattr 权限语义，修复在依赖包/系统层
  （qtbase 重编启用 ICU、exiv2 重编启用 BMFF），非本包缺陷。

## ⚠️ R40 依赖链 SONAME 限制（沿袭 6.14 结论）

- 制品仓 kconfig/kcoreaddons/ki18n/karchive/kcodecs 包自身无 DT_SONAME
  （readelf 证实，kconfig 6.26.0 制品同样如此），链接器对部分 NEEDED 记录
  绝对路径。本包自身 DT_SONAME 已注入（`CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG`），
  产物含 `.so.6.28.0/.so.3/.so` 版本化软链链。依赖链修复需上游 KF6 包
  重发（补 SONAME），非本配方缺陷——与 6.14.0 相同结论，制品仓 KF6 链现状。
---

**编译结束**: 2026-09-07 01:09
**最终状态**: built
