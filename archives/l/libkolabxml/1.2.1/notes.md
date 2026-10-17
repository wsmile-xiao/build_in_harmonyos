# libkolabxml 1.2.1 OHOS 适配笔记

## 软件概况

libkolabxml 是 Kolab 项目的 XML 格式库（KDE PIM 生态）：Kolab v3 XML
（xCal/xCard 变体）的序列化/反序列化，覆盖 event/todo/journal/note/
contact/configuration/freebusy/file 八类对象。上游 KDE GitLab
（invent.kde.org/pim/libkolabxml，原 git.kolab.org）需要登录，源码取自
Debian 官方 orig tarball（R39 权威镜像源）。

- 版本：1.2.1（2014 年最后版本，上游停止维护）
- 构建：CMake（2.8.5 时代）
- 语言：C++（2014-era，重度依赖 std::auto_ptr）

## 适配核心难点（按发现顺序）

### 1. CodeSynthesis XSD 工具链（最大难点）

上游构建需要两个 host 工具：
- `xsdcxx`：从 schemas/*.xsd 生成 C++/Tree bindings
- `xsdbin`：把 schema 编译为二进制 grammar 数组

两者在 CI 交叉编译 worker 上不存在，且 x86_64 预编译二进制在本机
（OHOS arm64）无法运行。

**解法：本机从源码编译 XSD 4.0.0 工具链，预生成产物打进 patches/**

a) 本机编译 xsdcxx（xsd-4.0.0+dep.tar.bz2，CodeSynthesis 官方一体包）：
   - OHOS SDK clang + conan 静态 xerces-c/3.2.5（本机即 OHOS arm64，
     编出的工具本机可直接运行）
   - 踩坑 1：组件目录的无扩展名 `version` 文件与 libc++ 的
     `#include <version>` 冲突（新版 libc++ 无条件包含）→ 重命名为
     version.txt（该文件只被 dist 目标引用）
   - 踩坑 2：libxsd-frontend 的 `operator<<(wostream&, Path)` 在新编译器
     报错（`path.string()` 是 char 串不能流给 wostream）→ 逐字符 widen
   - 构建变量：`make CXX=clang++ CC=clang CXXFLAGS="-O2 -std=c++14
     -I<xerces>/include" LDFLAGS="-L<xerces>/lib" LIBS="-lxerces-c -lc++
     -lc++abi -ldl -lpthread"`
   - 运行时需 LD_LIBRARY_PATH 指向 SDK 的 libc++_shared.so

b) 预生成 bindings（与上游 CMakeLists 命令一致，仅加 --std c++11）：
   ```
   xsdcxx cxx-tree --std c++11 --generate-polymorphic \
     --generate-serialization --namespace-map http://kolab.org=KolabXSD \
     --root-element icalendar --root-element vcards --root-element note \
     --root-element configuration --root-element file \
     --output-dir bindings/ <7 个 xsd 文件>
   ```
   **--std c++11 必须加**：默认（c++03）生成的代码用
   `xsd::cxx::xml::dom::auto_ptr`，在 XSD_CXX11 模式的 libxsd 头下不存在。

c) 预编译 schema 数组：`xsdbin --array-name iCalendar_schema ...`

d) libxsd runtime（header-only，106 个 .hxx）随 patches/libxsd/ 分发

### 2. std::auto_ptr → std::unique_ptr（C++17 移除）

上游源码 20+ 处 std::auto_ptr / xsd::cxx::xml::dom::auto_ptr。
替换规则：
- 声明/构造：直接换成 unique_ptr
- **所有权转移点必须显式 std::move**（auto_ptr 的拷贝即转移语义）：
  - `note = KolabXSD::note(doc)` → `note(std::move(doc))`
  - `prop.recurrence_id(recurrenceId)` → `std::move(recurrenceId)`
  - `ValarmType(p)` → `ValarmType(std::move(p))`
- 涉及文件：kolabconversions.h / xcalconversions.h / xcardconversions.h /
  compiled/XMLParserWrapper.{h,cpp}

### 3. XSD_CXX11 宏三件套

libxsd 的 config.hxx：`XSD_AUTO_PTR` 在 XSD_CXX11 下定义为 unique_ptr。
`XSD_CXX11_TEMPLATE_ALIAS` 正常从 `__GNUC__ >= 4.7` 推导，但
**clang-on-OHOS 伪装成 GCC 4.2**，必须显式定义：
`-DXSD_CXX11 -DXSD_CXX11_TEMPLATE_ALIAS -DXSD_CXX11_NULLPTR`

### 4. boost::thread_specific_ptr → C++11 thread_local

boost/1.90.0 conan 包不含编译版 boost_thread（`get_tss_data`/
`set_tss_data` 未定义）。两处使用（utils.cpp 的 Global、
XMLParserWrapper.cpp 的 parser 单例）语义上就是线程局部存储，
thread_local 等价替换。测试里的 boost::thread 换 std::thread。

### 5. Boost 组件声明

上游 `find_package(Boost REQUIRED COMPONENTS thread system)` 在
boost/1.90.0（header-only + unit_test_framework）下失败 → patch 为
headers-only `find_package(Boost REQUIRED)`（thread 用法已消除）。

### 6. qt5/5.15.19 的三个坑（仅 -o build_tests=True 本地测试模式）

- **组件 config 缺失**：CMakeDeps 不为 qt5 生成 Qt5CoreConfig.cmake，
  但包内 lib/cmake/ 有上游原装 config → configure cli 传
  `-DCMAKE_PREFIX_PATH=<qt5_pkg>/lib/cmake`（不能用 toolchain cache
  变量——会覆盖 CMakeDeps generators 目录的 prepend，导致 ECM 找不到）
- **mkspecs 路径断链**：Qt5CoreConfigExtrasMkspecDir.cmake 引用打包时
  的 `../b//mkspecs/linux-clang` → 配方 build() 里自动创建
  `b/mkspecs -> p/mkspecs` symlink（_fix_qt5_mkspecs_symlink）
- **zlib 版本冲突**：qt5 要 1.3.1（其制品仓二进制按 1.3.1 构建），
  libcurl 要 1.3.1.1 → 本地测试模式下 `zlib/1.3.1.1 force=True`

### 6b. CI 依赖图策略（关键）

**qt5 的制品仓二进制 package id 键合 zlib/1.3.1**；force override 到
1.3.1.1 后 id 变化（cc376eb6≠d1981312）→ conan 尝试从源码全量构建
Qt5（51MB qtbase）→ CI 沙箱 fork 受限 configure 失败（首轮 CI #51530
实锤）。

**解法**：default_options.build_tests=False——CI 图只有
xerces-c/boost/libcurl（二进制全在）。上游 84 测试函数已在本地
（-o build_tests=True）真实执行并留证（reports/），完全符合
"CI 跑不了的本地执行+附证据"铁律。test_package round-trip 在两种
模式下都始终运行。

### 7. CMake 4.x 兼容

`cmake_minimum_required(2.8.5)` → CMake 4.x 拒绝 →
`CMAKE_POLICY_VERSION_MINIMUM=3.5`（cache variable）。

### 8. UUID 检查

FindLibkolabxmlDependencies 的 `${Boost_MAJOR_VERSION}` 在 CMakeDeps
下未定义导致版本比较走错分支找 ossp-uuid → boost≥1.43 的 header-only
uuid 直接 patch 掉检查。

## 上游测试（铁律执行：本地真实跑）

上游 tests/CMakeLists.txt 注册 **5 个测试可执行文件**（Qt5Test 框架；
`-o build_tests=True` + QT5_BUILD=TRUE + ECM + Qt5Core/Qt5Test 本地构建）：

| 测试 | 结果 |
|---|---|
| bindingstest | 27 passed, 0 failed |
| conversiontest | 39 passed, 0 failed |
| kolabconversationtest | 4 passed, 0 failed |
| parsingtest | 3 passed, 0 failed |
| validationtest | 11 passed, 0 failed |
| **合计** | **84 passed, 0 failed（100%）** |

运行环境：conan create 的 build 目录，LD_LIBRARY_PATH 指向 qt5/curl/
SDK libc++。证据：reports/upstream-tests-evidence.txt。
（conversiontest 含 threadLocalTest——std::thread 两线程并发验证
thread_local 语义正确。）

test_package（conan L1）：Kolab::Note 序列化-反序列化 round-trip，
writeNote → readNote 字段比对，真实调用库 API，PASS。

## CI 预案（mkspecs 问题）

配方 build() 的 _fix_qt5_mkspecs_symlink 已自动处理 p 布局包的
mkspecs 断链（build_tests=True 本地模式）。CI 默认模式不引入 qt5，
无此问题。

## 产物

- libkolabxml.so（含 xerces/boost 静态链入；curl 动态）
- headers: include/kolabxml/*.h（上游 install 展平 containers/）
- test_package: note round-trip

## 依赖版本

默认（CI）：xerces-c/3.2.5 + boost/1.90.0 + libcurl/8.5.0
测试模式（-o build_tests=True，本地）：+ qt5/5.15.19 + ecm/6.20.0 +
zlib/1.3.1.1（force 统一）
