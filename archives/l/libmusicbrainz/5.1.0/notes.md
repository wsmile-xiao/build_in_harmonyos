# libmusicbrainz 5.1.0 适配笔记

## 定位
- 上游 metabrainz/libmusicbrainz release-5.1.0，MusicBrainz 客户端库
- 构建系统: CMake（`ADD_LIBRARY(musicbrainz5 SHARED ...)`）
- 依赖: neon/0.34.0 + libxml2/2.15.3.1（registry 已发布）

## 编译环境
- 构建系统: CMake
- 编译器: clang/clang++（OHOS aarch64）
- 状态: built（conan create 全流程通过，消费者输出 `libpng runtime version` 类比 `test_musicbrainz: OK`）

## 构建要点
- 2 个补丁（构建/兼容修复）：
  - 0001 `xmlParser.cc`：兼容 libxml2 2.15.x（`xmlGetLastError()` 返回 `const xmlError*`，老代码用 `xmlErrorPtr` 编译失败）
  - 0002 `src/CMakeLists.txt`：移除 `DEPENDS ... *.inc` 字面通配符（make 不展开，报 `No rule to make target`）
- generate() 注入 libxml2/neon 的 `CMAKE_INCLUDE_PATH`/`CMAKE_LIBRARY_PATH`（上游 `FindLibXml2.cmake` 用 `FIND_LIBRARY` 只搜系统路径；libxml2 include 布局为 `include/libxml2/`）
- build() 注入 `LD_LIBRARY_PATH`（`make-c-interface` 构建期工具运行期需加载 libxml2.so）
- test_package 运行期同样注入 `LD_LIBRARY_PATH`（libmusicbrainz5/neon/libxml2 均 shared 包）

## 测试
- 上游无离线自动化测试套件（tests/ 仅需联网的手工程序）
- test_package 消费者 4 断言：`MusicBrainz5::CMetadata` 默认构造 + XMLNS/Generator/Created getter 空值断言 + 拷贝构造/Clone 生命周期

## 遇到的问题与解决方案
| # | 问题 | 解决方案 |
|---|------|----------|
| 1 | xmlGetLastError 返回类型与 libxml2 2.15 不兼容 | 0001 patch：改用 const xmlError* |
| 2 | *.inc 字面通配符 DEPENDS 报 No rule | 0002 patch：移除该依赖 |
| 3 | FindLibXml2.cmake 找不到 conan 依赖库 | generate() 注入 CMAKE_INCLUDE_PATH/LIBRARY_PATH |
| 4 | make-c-interface 运行期缺 libxml2.so | build() 注入 LD_LIBRARY_PATH |
| 5 | C API 无 new 构造（仅 clone/delete） | 消费者用例改用 C++ API（MusicBrainz5::CMetadata） |

## 验证
- 本地 `conan create . --profile=ohos-aarch64`：`test_musicbrainz: OK (C++ API construct/getter roundtrip)`
