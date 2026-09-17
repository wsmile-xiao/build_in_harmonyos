# 【依赖项】feat(libkdcraw): 26.04.0 适配 HarmonyOS PC

## PR 信息
- **三方库名称**：libkdcraw（不含版本号！rule1+软件名校验）
- **上游版本**：26.04.0
- **上游仓库地址**：https://invent.kde.org/graphics/libkdcraw
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无（复用仓内 KF6/Qt6 26.04 系既有打法：libkdegames/26.04.0 配方骨架 + ECM 接线 + cmake_find_mode=none + CMAKE_PREFIX_PATH 喂包路径模式）

> 源码包 URL（conandata.yml）: https://invent.kde.org/graphics/libkdcraw/-/archive/v26.04.0/libkdcraw-v26.04.0.tar.gz （SHA-256 见 conandata.yml）

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游 26.04.0 无 ctest 注册（tests/CMakeLists.txt 仅 add_executable，无 add_test；实测 grep + 构建后 CTestTestfile 无测试） |
| 集成测试 | 2 | tests/ 两个手动命令行工具（BUILD_TESTING=ON 编译）：raw2png（RAW→PNG 转换器）、libinfo（库能力信息打印）——上游未注册 add_test，按手动工具计，不计入 ctest |
| 其他测试 | 0 | 上游无 |
| **合计** | **2** | 上游手动工具口径（ctest 注册数 0：add_test 全树为 0） |

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 同上游：无 ctest 注册 |
| 集成测试 | 2 | 不变 | 上游 raw2png/libinfo 全部编译并在 conan create 内 smoke 实跑（见验证结果段实测记录） |
| **鸿蒙特有测试** | 1 | 新增 | test_package 消费者测试：KDcraw 真实 API 调用（version/librawVersion/rawFilesList/supportedCamera/RawDecodingSettings/DcrawInfoContainer + 解码路径拒绝断言 + __OHOS__ 宏验证，offscreen 平台运行） |
| **合计** | **3** | +1 | 上游 2 + 鸿蒙消费者测试 1 |

## 上游测试用例减少原因
无减少。上游 2 项手动工具（raw2png、libinfo）全部编译并实跑通过；ctest 注册数上游即为 0（add_test 全树 0），适配后同为 0，口径一致。

## 上游测试用例修改说明
- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在修改（逐条：文件路径+修改原因+修改内容）

## 补全测试用例说明
- [ ] **否**，上游已有测试覆盖
- [x] **是**，上游无消费者级测试，适配后补全（补全范围+原因+新增文件清单）
  - 补全范围：test_package/ 消费者冒烟——链接 KDcrawQt6 库并真实调用 KDcraw::version()（5.0.0 断言非空）、KDcraw::librawVersion()（0.22.1≥0.22 版本断言）、KDcraw::rawFilesList()（45 扩展，含 dng/cr2/nef）、KDcraw::rawFilesVersion()（=5，正数断言）、KDcraw::supportedCamera()（1258 相机，非空断言）、KDcraw::rawFiles()（C 串非空）、RawDecodingSettings 字段回写+拷贝比较、DcrawInfoContainer 默认值、四条解码路径（rawFileIdentify/loadRawPreview/loadEmbeddedPreview/loadHalfPreview）对不存在文件的拒绝断言（LibRaw 真实走查）；__OHOS__ 宏分支验证（鸿蒙特有）。
  - 原因：上游 test_package 无消费者级集成验证（上游仅两个手动工具，无自动化测试）。
  - 新增文件清单：archives/l/libkdcraw/26.04.0/test_package/ 下 conanfile.py、CMakeLists.txt、test.cpp、run_test.sh、MANIFEST.yml

## 验证结果
- 编译状态：通过（conan create 全绿）
- 上游测试用例通过率：2/2（100%）（raw2png usage/拒绝路径 + libinfo 能力打印，conan create 内 smoke 实跑）
- 新增测试用例通过率：1/1（100%）

### 编译验证
- 编译器: clang 15 (aarch64-unknown-linux-ohos)
- 编译状态: 成功
- 构建系统: CMake（ECM/KDE 标准工具链）
- 配置选项: BUILD_TESTING=ON、BUILD_SHARED_LIBS=ON、KF_IGNORE_PLATFORM_CHECK=TRUE、CMAKE_POLICY_VERSION_MINIMUM=3.5（命令行传）

### 产物验证
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | ✅ | libKDcrawQt6.so（SOVERSION 5）+ KDcrawQt6Config.cmake/ConfigVersion/Targets(-release) + include/KDcrawQt6/ 头文件（KDCRAW/ CamelCase 转发头 + kdcraw/ 实头 + libkdcraw_version.h）+ libkdcraw.categories |
| 产物存在性 | ✅ | conan create 验证（含安装产物完整性） |
| ELF 格式 | ✅ | aarch64-unknown-linux-ohos |
| 运行测试 | ✅ | 2/2 上游工具 smoke + 1/1 消费者测试 |

### 上游测试实测记录（本地 conan create 内实跑，clancyxie 口径）
- 实测命令：conan create（BUILD_TESTING=ON）→ build/Release/bin/{libinfo,raw2png} smoke 运行（cwd=build/Release/tests 使 build-tree 相对 NEEDED `../bin/libKDcrawQt6.so` 正确解析）
- 实测输出：
  - `libinfo`：`Libkdcraw version : "5.0.0"`、`Libraw version : "0.22.1"`、`Raw files version : 5`、`Supported camera : QList("Adobe Digital Negative (DNG)", ..., "Zenit M")` 共 1258 项（LibRaw cameraList 全量）
  - `raw2png`（无参）：`raw2png - RAW Camera Image to PNG Converter` / `Usage: <rawfile>`，exit -1（上游设计行为）；对不存在文件：`raw2png: Idendify RAW image failed. Aborted...`（LibRaw identify 路径干净拒绝）
- ctest 口径说明：上游 26.04.0 tests/CMakeLists.txt 仅 `add_executable(raw2png)/add_executable(libinfo)`，全树无 `add_test`，构建后 CTestTestfile.cmake 无注册项——上游 ctest 注册数为 0（与上游 .gitlab-ci.yml 不跑 ctest 一致）。
- test_package 消费者输出：`OHOS-specific check: compiled with __OHOS__ on HarmonyOS PC (aarch64)`、`KDcraw version 5.0.0, LibRaw 0.22.1, 45 RAW extensions, 1258 cameras`、`test_libkdcraw: ALL CHECKS PASSED`。

## 补丁说明
无补丁（选项配置适配）。

## 依赖
- qtbase/6.11.1（已发布）
- libraw/0.22.1（已发布）
- 构建依赖：ecm/6.26.0（已发布）

## 补充说明
- 版本号策略：26.04.0 为上游 KDE Gear 26.04 正式版本号
- 上游 26.04.0 依赖闭包极简：Qt6 Core+Gui + LibRaw≥0.18 + ECM（构建工具），无需任何 KF6 框架库（实测上游 CMakeLists.txt）
- 库名与包名：构建目标 KDcraw，OUTPUT_NAME/EXPORT_NAME/CMake 包名均为 KDcrawQt6（导入目标 KDcrawQt6，空命名空间，SOVERSION 5）——与上游 KF5 时代命名不同，消费者 find_package(KDcrawQt6) + target_link_libraries(KDcrawQt6)
- FindLibRaw 为上游自带 module 模式查找（cmake/modules/FindLibRaw.cmake），通过 CMAKE_PREFIX_PATH/CMAKE_LIBRARY_PATH/CMAKE_INCLUDE_PATH 喂 conan libraw/0.22.1 包路径解析（PkgConfig 前缀探测在 OHOS 上缺席，模块回退 plain find_path/find_library 正常工作）
- 已知限制：raw2png 完整 RAW→PNG 转换需真实 RAW 样本文件（上游仓库不随源码分发测试样本），本验证覆盖 usage 路径与错误拒绝路径；libinfo 覆盖全部 9 个能力查询 API
