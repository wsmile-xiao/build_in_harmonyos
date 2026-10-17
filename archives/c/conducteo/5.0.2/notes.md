# conducteo 5.0.2 适配笔记

## 编译环境
- 构建系统: cmake（Qt6 Widgets GUI 应用，EN 10211 热桥计算）
- 编译日期: 2026-09-09
- 编译器: clang/clang++ 15.0.4（OHOS SDK）
- 状态: built（conan-verify 8 道门禁全部 PASS）

## 编译步骤

1. 源码：SourceForge 官方源 `conducteo_5.0.2.orig.tar.gz`（sha256
   7a336d78eeeb4813af0e5b4c5447163f3fda0b529ce4cb2044fd353147a7f466；
   SKILL search-url 缓存的 Savannah 死链已核实废弃，官方托管方经 Debian
   sources 元数据确认为 SourceForge）
2. 依赖发布检查（W0）：qtbase/6.11.1.1.1、eigen/3.4.1、tinyxml/2.6.2、
   dxflib/3.26.4、libzip/1.11.4、zlib/1.3.1.1、nlohmann_json/3.12.0、
   uuid/2.40.1 —— 8 项全部已在 ohpcd 制品仓发布
3. 构建：`cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake`
   → `make -j2` → `make install DESTDIR=...`（100% 编译成功）
4. 验证：`conan-verify conducteo 5.0.2` 全 PASS；W3 本地 CI（build_and_test.sh）通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `EIGEN_ROOT_DIRECTORY is not set` | OHOS 下 CMAKE_SYSTEM_NAME=HarmonyOS，CMake 不定义 UNIX 变量，`if (UNIX AND NOT APPLE)` 全部失效走 else 手动路径 | CMakeLists.txt 新增 `IS_LINUX_LIKE`（HarmonyOS→TRUE），5 处平台分支改为 `IS_LINUX_LIKE AND NOT APPLE`（补丁 0001） |
| 2 | `Qt6PrintSupport` 组件缺失 | 制品仓 qtbase 的 FEATURE_printsupport=OFF 且无 QtPrintSupport 头文件 | 源码中 QPrinter 仅 include 零实例化、PDF 导出走 QPdfWriter（QtGui 模块）→ 移除 PrintSupport 组件/链接/冗余 include，功能零损失（补丁 0001+0003） |
| 3 | `tinyxml.h/uuid.h/dl_creationadapter.h not found` | 裸库名 uuid/zip/tinyxml 与 find_path 不匹配 conan 目标 | 改为 find_package(tinyxml/libzip/uuid/dxflib) + conan 目标 uuid::uuid/libzip::libzip/tinyxml::tinyxml/dxflib::dxflib，dxflib include 补 `/dxflib` 子目录（补丁 0001） |
| 4 | conan create `BadZipFile` | SourceForge URL 以 /download 结尾，conan get() 无法推断压缩格式 | conandata.yml 显式声明 `filename: conducteo-5.0.2.tar.gz` |
| 5 | conan create `Eigen3Config not found` | 配方 generate() 缺 CMakeDeps；手写 conan_cmakedeps_paths.cmake 覆盖同名文件 | generate() 调 CMakeDeps + paths 文件保留 `${CMAKE_CURRENT_LIST_DIR}`（依赖 Config 所在目录） |
| 6 | 构建期 moc `Error relocating ... symbol not found` | libQt6Core.so 依赖 libc++_shared.so，位于 SDK `llvm/lib/aarch64-linux-ohos/`，profile LD_LIBRARY_PATH 未含 | conanfile build() 注入 qtbase lib + SDK libc++ 目录到 LD_LIBRARY_PATH |
| 7 | test_package 运行 `libc++_shared.so not found` | conanrun 环境 LD_LIBRARY_PATH 缺 SDK libc++ 目录 | test.sh 开头注入 SDK libc++ 路径 |
| 8 | install 失败 `debian/conducteo.desktop not found` | 上游 Debian 打包文件不随源码 tarball 发布 | DebianInstaller.cmake 对 desktop/png/xml 加 `EXISTS` 保护（补丁 0002） |

## 源码修改

- patches/0001-CMakeLists.txt.patch — OHOS 平台判断归一化（IS_LINUX_LIKE）+ PrintSupport 裁剪 + 依赖目标化（uuid::uuid/libzip::libzip/tinyxml::tinyxml/dxflib::dxflib）
- patches/0002-DebianInstaller.cmake.patch — debian/ 打包文件缺失的 install EXISTS 保护
- patches/0003-src-reports-ReportContent.cpp.patch — 移除冗余 QtPrintSupport/QPrinter include

## 依赖版本

- qtbase/6.11.1.1.1（Qt6 Widgets/Core/Gui）
- eigen/3.4.1
- tinyxml/2.6.2
- dxflib/3.26.4
- libzip/1.11.4
- zlib/1.3.1.1（libzip 依赖版本，override 对齐）
- nlohmann_json/3.12.0
- uuid/2.40.1

## 验证结果

- 编译：make 100% 成功，产物 conducteo（arm64 ELF，约 4.2MB）
- 上游测试（R51，test_driver 无头执行 Tests::exec()）：18/18 全部 PASSED
  （含 EN 10211/EN 10077 标准验证有限元求解）
- conan-verify：G0-G4 + L2/L4/L5 全 PASS
- W3 本地 CI（build_and_test.sh）：通过
- test_package：binary present + GUI event loop alive 冒烟测试通过

## 结束标记

本次适配完成：conan-verify 8 道门禁全 PASS、W3 本地 CI 通过、W4 审计零问题，达到提交标准。
