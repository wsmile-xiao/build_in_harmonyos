# libodsstream 0.9.18 — 适配笔记

> 档案创建时间: 2026-09-22
> 最后更新: 2026-09-22
> 状态: built（本机 conan create 全绿：上游 5/5 TEST_CASE + test_package 11/11 断言）

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libodsstream |
| 版本 | 0.9.18（forgemia 项目 1471 最新 upstream tag） |
| 构建系统 | CMake (C++20) |
| 源码 | https://forgemia.inra.fr/pappso/libodsstream/-/archive/upstream/0.9.18/libodsstream-upstream-0.9.18.tar.gz |
| sha256 | a0df7c7b55aaf199824dc7d4064a4b8c7bd0549fc6252b51875718da73a4ca60 |
| 任务背景 | libpappsomspp 0.11.26 前置链第 2 件 |

## 二、W0 依赖核验（全绿才动工）
- qtbase/6.11.1 ✅（制品仓）
- qt5compat/6.11.1 ✅（Core5Compat 头 + 库）
- zlib/1.3.1 ✅（注意：非 PIC 静态库）
- catch2/3.16.0 ✅（上游测试框架）
- QuaZip：⚠️ 制品仓只有 Qt5 线 quazip/1.4、1.4.1——**与 Qt6 ABI 断裂**（见三.1），改 vendor

## 三、关键适配点（六大坑全记录）

### 3.1 Qt5 线 QuaZip 与 Qt6 代码的 C++ ABI 断裂（本件最大坑）
- 制品仓 quazip/1.4.1 是 Qt5 线（quazip1-qt5，链 Qt5Core）
- libodsstream 是 Qt6 代码。Qt6 把 `QIODevice::OpenModeFlag` 移入 `QIODeviceBase`，
  mangled 名从 `_ZN9QIODevice12OpenModeFlagE` 变为 `_ZN13QIODeviceBase12OpenModeFlagE`
- 实锤：链接期 `undefined symbol: QuaZipFile::open(QFlags<QIODeviceBase::OpenModeFlag>, ...)`
  而 quazip1-qt5.a 只导出 `QuaZipFile::open(QFlags<QIODevice::OpenModeFlag>, ...)`
- **修法**：vendor QuaZip 1.4 源码（vendor-quazip/，与 quazip/1.4.1 同源同 sha256 的
  v1.4 tag tarball），构建期以 Qt6（qtbase 6.11.1 + qt5compat 6.11.1）编静态
  libquazip1-qt6.a，写 QuaZip-Qt6Config shim 供上游 find_package(QuaZip-Qt6) 解析；
  package 阶段把 vendored .a + 头 + config 装进包（消费者可完整解析 QuaZip::QuaZip target）
- fceux 2.6.6 vendored-minizip 先例

### 3.2 CMAKE_SYSTEM_NAME=HarmonyOS 平台分支跳过
- 上游主 CMakeLists 平台链 `elseif(UNIX AND NOT APPLE)`——OHOS conan toolchain 映射
  CMAKE_SYSTEM_NAME=HarmonyOS，CMake 4.1 无 Platform/HarmonyOS.cmake → UNIX 变量未定义
  → unix-toolchain.cmake（ZLIB/Catch2/QuaZip find_package 所在地）整段不执行
- patch 0003：平台条件补 `OR SYSTEM_UNAME_S MATCHES "HarmonyOS"`

### 3.3 zlib 非 PIC + 共享库
- 制品仓 zlib/1.3.1 静态库非 PIC：链入 libodsstream.so 报
  `R_AARCH64_ADD_ABS_LO12_NC cannot be used against 'z_errmsg'`
- override 到 zlib/1.3.1.1（PIC 版）会连锁触发 qtbase 6.11.1 全量源码重建（package_id 失配，900s+ 未完成）
- **修法**：patch 0004 让上游 `add_library(Core SHARED)` 跟随 BUILD_SHARED_LIBS，
  配方默认 shared=False 静态交付（upstream 本就同时装 odsstream-static）

### 3.4 ctest ENVIRONMENT 整替 LD_LIBRARY_PATH
- 上游 test/CMakeLists `set_tests_properties(... ENVIRONMENT "LD_LIBRARY_PATH=...")`
  会整体替换，藏掉 conan 依赖库目录 → test 运行时 Qt 库加载失败
- patch 0005：改 `ENVIRONMENT_MODIFICATION "LD_LIBRARY_PATH=path_list_prepend:..."`（CMake≥3.22）

### 3.5 qt5-qtbase 官方 config 的 mkspecs 断链
- quazip 官方 QuaZip-Qt5Config 的 find_dependency(Qt5) 拖 qt5-qtbase 包内官方
  Qt5CoreConfigExtrasMkspecDir.cmake，其引用构建期路径 `<pkg>/../b//mkspecs/linux-clang`
  （包内不存在）→ 官方 config 不可用。全部依赖统一走 CMakeDeps 生成的 config
- conan OHOS toolchain 的 CMAKE_PREFIX_PATH 注入对 find_dependency 链不稳：
  conan_cmakedeps_paths.cmake 里手写 `list(PREPEND CMAKE_PREFIX_PATH <generators>)` 兜底

### 3.6 quazip_qt_compat.h 的 QtCore5Compat include
- vendored quazip 源码 quazip_qt_compat.h 在 QT_VERSION>=6 时 include
  `<QtCore5Compat/QTextCodec>`——qt5compat 包 include 注入为全局 `-isystem`（CXX flags）

## 四、上游测试口径（N=5，全过）
- test/ 三个测试程序（Catch2 3.16）：test_ods（2 TEST_CASE）+ test_tsv（2）+ test_zlib（1）= **N=5**
- 本机 conan create 实跑：`All tests passed`（2+2+1 全过）
- 消费者测试兜底：test_package/test_odsstream.cpp 11 断言（OdsDocWriter 写 → OdsDocReader 读回，
  sheet 名/数值/文本 cell 往返），全过

## 五、R 条款对照
- R26：非系统同名库，静态交付规避 RPATH
- R28/R34：test_package 调真实 API（OdsDocWriter/OdsDocReader 往返）
- R32：settings.os 判断 in ("Linux","OHOS")
- R33：编译器全走 CMakeToolchain
- R38：产物含 ods2tsv/tsv2ods CLI——软件级 commands.json 需声明
- R39：conandata URL 是官方 forgemia tag 归档

## 六、源码修改清单
| 文件 | 原因 | 方式 |
|------|------|------|
| test/test_ods.cpp | cwd 相对路径 → CMAKE_SOURCE_DIR | patch 0001 |
| CMakeStuff/toolchains/unix-toolchain.cmake | QuaZip config 名兼容+alias+ZLIB alias | patch 0002 |
| CMakeLists.txt | HarmonyOS 平台分支 | patch 0003 |
| src/CMakeLists.txt | Core SHARED 硬编码 → BUILD_SHARED_LIBS | patch 0004 |
| test/CMakeLists.txt | 静态库 fallback + ENVIRONMENT_MODIFICATION | patch 0005 |

## 七、本机验证
```bash
cd ~/huawei/worktrees/j669539/libodsstream-0.9.18
conan create archives/l/libodsstream/0.9.18 -pr:h=~/.conan2/profiles/ohos-aarch64 \
  -pr:b=~/.conan2/profiles/ohos-aarch64 --build=missing -c tools.build:jobs=2
# → 上游 5/5 TEST_CASE 全过；test_package 11/11 断言全过
```

## 八、对话记录
### 对话 #1 — 2026-09-22
**操作**: 全链适配（vendored Qt6 QuaZip + 5 补丁 + test_package）
**结果**: conan create 全绿
**当前状态**: 待归档收尾 → push → PR → CI → 提审
