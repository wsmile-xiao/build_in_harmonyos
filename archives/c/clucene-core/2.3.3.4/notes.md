# clucene-core 2.3.3.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-07
- 编译器: clang/clang++ (clang 15.0.4, OHOS aarch64 原生)
- 状态: built

## 编译步骤

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

配方内等价于：

```bash
cmake <src> \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DDISABLE_MULTITHREADING=ON \
  -DBUILD_STATIC_LIBRARIES=ON \
  -DZLIB_ROOT=<conan zlib 包目录>
cmake --build . --target clucene-shared clucene-core cl_test
# 上游测试等价直跑（ctest 对 out-of-source 布局的相对路径解析是上游缺陷，
# 见下文问题 9）：159/159 通过
cd build/src/test && TEMP=test-tmp TMP=test-tmp \
  srcdir=<src>/src/test LD_LIBRARY_PATH=<build>/bin ../../bin/cl_test
cmake --install .
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.1 configure 直接失败 "Compatibility with CMake < 3.5 removed" | 上游 CMAKE_MINIMUM_REQUIRED(VERSION 2.4.0) | 传 -DCMAKE_POLICY_VERSION_MINIMUM=3.5（CMake 官方政策参数，不改上游文件） |
| 2 | generate 阶段 ZLIB_INCLUDE_DIR-NOTFOUND | 上游 src/shared/CMakeLists.txt:45 用 ELSEIF(ZLIB_FOUND)（永假笔误），系统无 zlib 头时捆绑回退死代码 | -DZLIB_ROOT 指向 Conan zlib/1.3.1.1 包目录（W0 实证 binary 可用） |
| 3 | QueryParser.cpp 窄化错误：0x80000000 不能窄化为 int32_t | C++11 禁止列表初始化窄化；JavaCC 生成位表以 int32_t 存 31 位标志 | 补丁 0001：显式 static_cast（与 chimera narrowing 补丁同源同位） |
| 4 | QueryParserTokenManager 窄化错误：0xffffffffffffffff 不能窄化为 int64_t | 同上；位掩码表存全 1 掩码 | 补丁 0001：表类型改 uint64_t（声明+定义同步改） |
| 5 | DISABLE_MULTITHREADING=ON 编译失败：_LUCENE_ATOMIC_INT_SET/GET 未定义 | 上游单线程模式宏自 2.3.3.4 位腐烂（缺 SET/GET 与 mutex_thread 空实现） | 补丁 0002：按 Adelie/chimera musl 适配补丁补齐宏与空 mutex_thread |
| 6 | 测试 cl_test 编译失败：usleep 未声明 | musl <unistd.h> 不被传递包含（glibc 依赖传递链） | 补丁 0003：测试文件显式 #include <unistd.h> |
| 7 | MT 开启时 Atomic Updates (TestThreading) 必现 SIGSEGV，Debug/-O0 同崩；reuters-21578-index 测试数据整包校验通过 | 上游多线程写入/读打开竞争缺陷（FSDirectory FSIndexInput::close 的 dounlock 分支 bug 等已知 UB），非平台问题 | 用上游官方便携模式 DISABLE_MULTITHREADING=ON 跑测试；musl 生态 chimera/Adelie 打包同口径（"tests fail with mt enabled"） |
| 8 | 测试硬编码 /tmp 但设备 /tmp 只读 | 上游测试选择逻辑 Misc::dir_Exists("/tmp") 只查存在性 | 运行时用上游支持的 TEMP/TMP 环境变量指向可写目录（不改源码） |
| 9 | cl_test 直接运行报 "must be run from a subdirectory..." 或动态库打不开 | 上游按相对路径找测试数据与依赖库（NEEDED 记 ../../bin/*.so 相对链接时目录） | 在 build/src/test 目录下运行（上游预期 CWD）；find_package(ZLIB) 修复后链接走 libz.a 正常 |
| 10 | C++17 下 TestSort.cpp 编译失败 "reference to 'data' is ambiguous" | 全局变量 data 与 C++17 std::data（libc++ \<iterator\>）二义；探索构建用默认 gnu++14 未暴露，CI profile cppstd=17 必现 | 补丁 0004：测试数据表改名 datap（chimera test-data 同款，上游测试修改） |
| 11 | 包布局运行断链：libclucene-core.so 的 NEEDED 记 ../../bin/libclucene-shared.so 相对路径 | CMake 对未知系统名 HarmonyOS 不提供 SONAME 规则；上游未设 SONAME 的目标被链接器按路径记录 | generate() 注入 CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG="-Wl,-soname,"，恢复上游 VERSION/SOVERSION 属性语义（产物 .so/.so.1/.so.2.3.3.4 三件套） |
| 12 | make install 不装 src/shared/CLucene 的 config/debug/util 头 | 上游 install 规则只覆盖 core 头（公共头链必需 shared 头，Debian headers.patch 同问题） | package() 从源目录补齐 shared 头（仅 .h，剔除混入的实现 .cpp），并删除内嵌 ext/boost 捆绑头 |
| 13 | conan-verify G2 干净轮 RAMDirectory 套件间歇失败（"MockRAMDirectory: a random IOException"，单套件复现 25/30） | 上游测试 MockRAMDirectory::randomIOExceptionRate 成员未初始化（UB），垃圾值 >0 时启用故障注入随机抛 IO 异常；无任何调用方启用注入 | 补丁 0005：构造函数补零初始化；修复后单套件 15/15、全套多轮 159/159 |

## 源码修改

| 补丁 | 内容 |
|------|------|
| patches/0001-fix-cxx11-narrowing.patch | QueryParser.cpp jj_la1_0 两处 0x80000000 显式转换；QueryParserTokenManager .h/.cpp jjbitVec0/2 类型 int64_t→uint64_t；legacy/Lexer.cpp TCHAR 初值显式转换 |
| patches/0002-fix-single-thread-mode-macros.patch | LuceneThreads.h 单线程分支补 _LUCENE_ATOMIC_INT_SET/GET 与空 mutex_thread/DEFINE_MUTEX；Misc.cpp/.h 的线程 id toString 加 MT 条件编译 |
| patches/0003-test-usleep-explicit-unistd.patch | src/test/search/TestIndexSearcher.cpp 显式包含 unistd.h（上游测试修改，PR 中申报） |
| patches/0004-test-sort-data-rename-std17.patch | src/test/search/TestSort.cpp 测试数据表 data 改名 datap，消除 C++17 下与 std::data 的二义（上游测试修改，PR 中申报） |
| patches/0005-test-mock-ramdir-init-rate.patch | src/test/store/MockRAMDirectory.cpp 三个构造函数补 randomIOExceptionRate 零初始化（上游未初始化成员 UB：垃圾值 >0 时故障注入随机 IOException，testRAMDirectorySize 间歇失败实测 25/30；无调用方启用注入。上游测试修改，PR 中申报） |

## 依赖版本

- zlib/1.3.1.1（ohpcd 远端 binary 实证可安装；静态 PIC libz.a，可被共享库吸收）
- boost：不依赖。2.3.3.4 源码零 boost include，CMake 探测为残余逻辑（找不到时回退 src/ext 捆绑头）

## 验证结果

```bash
# 上游测试（DISABLE_MULTITHREADING=ON，TEMP 指向可写目录）
# bin/cl_test 输出末行（3 轮一致）：
159 tests run:  159 passed, 0 failed, 0 not implemented.
# Tests run in ~60727ms

# 库构建产物
bin/libclucene-core.so    (2.4MB)
bin/libclucene-shared.so  (0.2MB)
# + BUILD_STATIC_LIBRARIES=ON 的 clucene-core-static / clucene-shared-static
```

## 注意事项

- **单线程模式是上游官方 OPTION**（CMakeLists OPTION(DISABLE_MULTITHREADING ...)），非删功能：pthread 分支整体不编入，库 API 语义不变；MT 需求的下游需等上游修复竞争缺陷。
- zlib 依赖为实质依赖（FieldsReader 压缩字段 uncompress、Misc deflate/gzip 工具）；boost 探测为残余死逻辑，勿误加 boost 依赖。
- recipe 的 ZLIB_ROOT 用 self.dependencies["zlib"].package_folder（依赖包目录根），保证 find_package(ZLIB) 命中 Conan 包而非系统；另配 CMakeDeps（generators 目录前置进 CMAKE_PREFIX_PATH），防 PREFER_CONFIG 命中开发环境 host 端 ZLIB 配置包（$HOME/.harmonybrew）。
- 上游 ELSEIF(ZLIB_FOUND) 笔误使捆绑 zlib 回退死代码，但 ZLIB_FOUND 路径正常；本适配走 ZLIB_ROOT 注入，不改上游 CMakeLists。
