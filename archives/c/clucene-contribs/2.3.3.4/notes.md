# clucene-contribs 2.3.3.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-09
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
  -DBUILD_CONTRIBS_LIB=ON \
  -DBUILD_STATIC_LIBRARIES=<按 shared 选项> \
  -DCMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG="-Wl,-soname," \
  -DZLIB_ROOT=<conan zlib 包目录>
cmake --build . --target clucene-shared clucene-core clucene-contribs-lib cl_test
# 上游测试等价直跑（ctest 对 out-of-source 布局的相对路径解析是上游缺陷）
cd build/src/test && TEMP=test-tmp TMP=test-tmp \
  srcdir=<src>/src/test LD_LIBRARY_PATH=<build>/bin ../../bin/cl_test
cmake --install .
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.1 configure 失败 "Compatibility with CMake < 3.5 removed" | 上游 CMAKE_MINIMUM_REQUIRED(VERSION 2.4.0) | 传 -DCMAKE_POLICY_VERSION_MINIMUM=3.5（同 clucene-core 配方） |
| 2 | contribs-lib 编译/链接 | 无——整树构建一次通过（core 5 补丁重放后） | 无需 contribs 专属编译补丁 |
| 3 | 包布局运行断链（NEEDED 记 ../../bin 相对路径） | 同 clucene-core：CMake 对未知系统名 HarmonyOS 不提供 SONAME 规则 | 注入 CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG="-Wl,-soname," |
| 4 | cl_test 编译失败 'CLucene/analysis/de/GermanStemmer.h' file not found | 上游顺序缺陷：src/test 先于 src/contribs-lib ADD_SUBDIRECTORY，clucene-contribs-lib_SOURCE_DIR 未定义，contribs 测试 include 为空 | 补丁 0006：INCLUDE_DIRECTORIES 改用顶层 clucene_SOURCE_DIR 显式路径（单行） |
| 5 | make install 不装 contribs-lib 产物与公共头 | 上游 contribs-lib 无 install 规则且 EXCLUDE_FROM_ALL | 补丁 0006：按 core 同款 FOREACH 头安装 + install(TARGETS)，并去 EXCLUDE_FROM_ALL |
| 6 | RAMDirectory/GermanAnalyzer 套件间歇失败（"MockRAMDirectory: a random IOException"、GermanAnalyzer 构造随机 SIGSEGV） | 两个独立上游缺陷：① MockRAMDirectory::randomIOExceptionRate 未初始化（UB 垃圾值>0 启用故障注入）；② GERMAN_STOP_WORDS 数组无 NULL 哨兵而 fillStopTable 按 NULL 结尾遍历（越界读堆，GermanAnalyzer 构造为生产路径，任何真实用户随机崩） | 补丁 0005（构造补零）+ 0007（数组尾部哨兵）；修复后单套件 15/15、全套多轮 160/160 |
| 7 | 测试硬编码 /tmp 但设备 /tmp 只读 | 上游测试选目录只查存在性 | 运行时用上游支持的 TEMP/TMP 环境变量指向可写目录（配方内相对路径 test-tmp） |
| 8 | 测试运行报 "must be run from a subdirectory..." | cl_test 相对路径找数据与依赖库 | 在 build/src/test 目录下运行（上游预期 CWD），srcdir/LD_LIBRARY_PATH 注入 |
| 9 | PR 首次 CI 失败：worker 源码下载超时（elapsedTime 360s），改用 sourceforge CDN 节点列表后仍失败（master.dl 超时 371s） | ① CI worker 对 SourceForge 域整体不可达；② CI 的 mirror-fallback 对 sourceforge 无可用镜像映射（build_and_test.sh L1118-1122 仅回填原 URL）；③ clucene-core PR !8895 同 URL 通过是命中 worker 下载缓存（假阴性）；④ 多 URL 列表形态还会关闭 mirror-fallback 正则（知识条目 E549 红线：sources.url 一律单值字符串） | conandata sources.url 改**单值**权威发行版镜像 `https://cdn.netbsd.org/pub/pkgsrc/distfiles/clucene-core-2.3.3.4.tar.gz`（NetBSD pkgsrc distfiles CDN：与官方 tarball 字节级一致，cmp 通过、sha256 不变；仓库先例 aamath/0.3.1、libquantum/1.0.0 同域且 CI 通过）；全文件仅保留该一处裸 URL |

## 源码修改

| 补丁 | 内容 |
|------|------|
| patches/0001-fix-cxx11-narrowing.patch | 同 clucene-core 包（整树构建需要，core 部分） |
| patches/0002-fix-single-thread-mode-macros.patch | 同 clucene-core 包（单线程模式宏修复，shared 部分） |
| patches/0003-test-usleep-explicit-unistd.patch | 同 clucene-core 包（上游测试修改） |
| patches/0004-test-sort-data-rename-std17.patch | 同 clucene-core 包（上游测试修改） |
| patches/0005-test-mock-ramdir-init-rate.patch | 同 clucene-core 包（上游测试修改） |
| patches/0006-contribs-install-and-test-include.patch | contribs 专属：CMakeLists 顶层去 EXCLUDE_FROM_ALL；contribs-lib 补头/库 install 规则；test/CMakeLists include 路径变量修复（上游测试修改） |
| patches/0007-german-stopwords-sentinel.patch | GermanAnalyzer.cpp GERMAN_STOP_WORDS 数组尾部补 NULL 哨兵（contribs 主代码生产缺陷修复，PR 中申报） |

## 依赖版本

- clucene-core/2.3.3.4（本仓配套包；contribs-lib .so 运行期 NEEDED 其 core/shared .so，requires 恒定 shared=True 变体）
- zlib/1.3.1.1（构建树 zlib 探测 + contribs gzip 流）
- boost：不依赖（contribs-lib 与 core 源码均零 boost include；"boost factor" 系 Lucene 评分概念非 Boost 库）

## 验证结果

```bash
# 上游测试（DISABLE_MULTITHREADING=ON，BUILD_CONTRIBS_LIB=ON）
# bin/cl_test 输出末行（多轮一致，含 GermanAnalyzer contribs 套件）：
160 tests run:  160 passed,  0 failed,  0 not implemented.
# 与 clucene-core 包的 159 差 1：BUILD_CONTRIBS_LIB=ON 使 cl_test 编入
# contribs GermanAnalyzer 套件（1 case）

# 交付产物
lib/libclucene-contribs-lib.so{,.1,.2.3.3.4}  (575936B 实体)
include/CLucene/analysis/de|highlighter|snowball/...  (contribs 公共头)
```

## 注意事项

- **交付面**：本包只装 contribs 产物与全部公共头（core/shared 库产物由 clucene-core 包交付）；构建树内的 core/shared 目标仅作构建依赖。
- **依赖形态**：requires clucene-core/2.3.3.4 恒定 shared=True（contribs-lib .so 运行期 NEEDED core .so；core 默认 static 变体无 .so 会断链）。
- GermanAnalyzer 生产缺陷修复（0007）影响所有真实使用者，PR 中按主代码修复申报。
