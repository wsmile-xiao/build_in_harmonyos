# DRAFT-libkolabxml-xsd-legacy-cpp-migration — 老 C++ XML 绑定库的 OHOS 迁移知识链

> 实证来源：libkolabxml 1.2.1（PR #11169）适配全记录，archives/l/libkolabxml/1.2.1/notes.md 八坑全记录。
> 定位：**组合型知识链**——五环环环相扣，缺一环则全链不通。配套单点草稿：DRAFT-E-xsd-toolchain-pregen（环1-3 工具链）、DRAFT-E-autoptr-unique-ptr（环4 auto_ptr 迁移）。

## 适用场景（价值判断）

- **"双亡老库"**：业务库停止维护（libkolabxml 1.2.1 = 2014 末版）**且**其依赖的代码生成器生态同样停更（CodeSynthesis XSD 4.0.0 = 2014 末版）
- 构建期依赖 host 端代码生成工具（.xsd → C++ bindings），交叉编译 CI 无法提供
- 源码是 C++03/11 时代风格：`std::auto_ptr`、`boost::thread_specific_ptr`、CMake 2.8 minimum
- 典型候选：一切基于 CodeSynthesis XSD / gsoap /类似 2014 前代码生成器的 C++ 库

## 错误特征（进入知识链的信号）

```
Could NOT find XSDCXX (missing: XSDCXX XSDCXX_INCLUDE_DIRS)
xsdcxx: command not found
error: no template named 'auto_ptr' in namespace 'std'
xsd::cxx::xml::dom::auto_ptr ... not declared   # XSD_CXX11 模式下不存在
undefined reference to get_tss_data/set_tss_data  # boost_thread 未编译
cmake_minimum_required(2.8.5) → CMake 4.x 拒绝
```

**关键认知**：这些错误**不会同时出现**——修完工具链才轮到宏错误，修完宏才轮到 auto_ptr，修完 auto_ptr 才轮到 boost/thread。单点修完一头，下一头立刻冒头。知识链价值 = 预见完整路径，避免每一环都当"新问题"重新踩坑。

## 五环解法（libkolabxml 全链实证）

### 环1：host 工具链自举（OHOS 本机从源码编 xsdcxx/xsdbin）

CI 交叉 worker 无 XSD 工具且官方预编译二进制仅 x86_64。解法：**在 OHOS arm64 本机**从 `xsd-4.0.0+dep.tar.bz2`（官方一体包）源码编译：

```bash
make CXX=clang++ CC=clang CXXFLAGS="-O2 -std=c++14 -I<xerces>/include" \
     LDFLAGS="-L<xerces>/lib" LIBS="-lxerces-c -lc++ -lc++abi -ldl -lpthread"
```

（OHOS SDK clang + conan 静态 xerces-c/3.2.5；本机即 arm64，编出的工具可直接运行；运行时 LD_LIBRARY_PATH 指向 SDK libc++_shared.so）

**坑 a**：组件目录的无扩展名 `version` 文件与 libc++ 的 `#include <version>` 冲突（新版 libc++ 无条件包含）→ 重命名 `version.txt`（该文件仅被 dist 目标引用）。
**坑 b**：libxsd-frontend 的 `operator<<(wostream&, Path)` 在新编译器报错（`path.string()` 是 char 串不能流给 wostream）→ 逐字符 widen 成 wstring。

### 环2：预生成（生成器 flag 与宏体系必须配套）

```bash
xsdcxx cxx-tree --std c++11 --generate-polymorphic --generate-serialization \
  --namespace-map http://kolab.org=KolabXSD --root-element icalendar ... <7 个 xsd>
xsdbin --array-name iCalendar_schema --output-dir . <xsd>
```

**`--std c++11` 必须加**：默认（c++03）生成的代码用 `xsd::cxx::xml::dom::auto_ptr`，在 XSD_CXX11 模式的 libxsd 头下**不存在**——生成器 flag 决定生成代码的智能指针形态，与环4 的宏体系强耦合。

### 环3：预生成产物进 patches/，CI 零工具依赖

- 产物：`patches/bindings/`（14 文件）+ `patches/kolabformat-xcal-schema.cxx/.hxx`（grammar 数组）+ `patches/libxsd/`（header-only runtime，106 头）
- conanfile.py `build()` copy 进源码树；patch 上游 CMakeLists：`XSDCXX` 不可用时 `copy` 预生成文件（**保留原 xsdcxx 命令路径作为 fallback**——上游有工具的环境仍走原生路径）
- 效果：CI 干净环境完全不需要 XSD 工具链

### 环4：C++17 语义迁移（两处）

**auto_ptr → unique_ptr**（20+ 处，kolabconversions.h / xcalconversions.h / xcardconversions.h / compiled/XMLParserWrapper.{h,cpp}）：
```cpp
// 声明点直换
std::auto_ptr<KolabXSD::Note> note;    →  std::unique_ptr<KolabXSD::Note> note;
xsd::cxx::xml::dom::auto_ptr<T>        →  xsd::cxx::xml::dom::unique_ptr<T>  // libxsd C++11 别名
// 所有权转移点必须显式 std::move（auto_ptr 拷贝即转移，unique_ptr 拷贝被 delete）
note = KolabXSD::note(std::move(doc));
prop.recurrence_id(std::move(recurrenceId));
```

**boost::thread_specific_ptr → thread_local**：boost/1.90.0 conan 包不含编译版 boost_thread（`get_tss_data`/`set_tss_data` 未定义）。两处使用（utils.cpp 的 Global、XMLParserWrapper.cpp 的 parser 单例）语义上就是线程局部存储，`thread_local` 等价替换；测试里 `boost::thread` → `std::thread`（conversiontest 的 threadLocalTest 两线程并发用例验证语义正确）。

### 环5：宏三件套 + CMake 4 + qt5 三坑

```bash
-DXSD_CXX11 -DXSD_CXX11_TEMPLATE_ALIAS -DXSD_CXX11_NULLPTR
```
libxsd 的 config.hxx 在 `XSD_CXX11` 下把 `XSD_AUTO_PTR` 定义为 unique_ptr；`XSD_CXX11_TEMPLATE_ALIAS` 正常从 `__GNUC__ >= 4.7` 推导，但 **clang-on-OHOS 伪装成 GCC 4.2**，必须显式定义。

- CMake 4.x：`CMAKE_POLICY_VERSION_MINIMUM=3.5`（cache variable，2.8.5 minimum 被拒）
- qt5/5.15.19 三坑：
  1. 组件 config 缺失 → configure cli 传 `-DCMAKE_PREFIX_PATH=<pkg>/lib/cmake`（**不能用 toolchain cache 变量**——会覆盖 CMakeDeps generators 目录的 prepend，导致 ECM 找不到）
  2. mkspecs 路径断链（Qt5CoreConfigExtrasMkspecDir 引用打包时 `../b//mkspecs/linux-clang`）→ 包缓存旁建 `b/mkspecs` symlink（配方 build() 自动创建）
  3. zlib 版本冲突（qt5 要 1.3.1、libcurl 要 1.3.1.1）→ `self.requires("zlib/1.3.1.1", force=True)`

## 红线（禁止的做法）

- ❌ `#ifdef __OHOS__` 平台分支包裹 auto_ptr/thread 逻辑——知识应基于**语言标准**（`__cplusplus`）而非平台名，否则不可跨库复用
- ❌ `-D_LIBCPP_ENABLE_CXX17_REMOVED_AUTO_PTR` 作为主方案——libc++ 私有逃生口，不可移植，仅过渡兜底
- ❌ 删掉上游原生成命令只留 copy——必须保留原路径 fallback（有工具环境仍走原生构建）
- ❌ 预生成时省略 `--std c++11`——生成的代码与 XSD_CXX11 宏体系不配套，必返工

## 降级路径（fallback）

| 断环 | 降级方案 |
|------|---------|
| 环1 无 OHOS 本机 | 任意 Linux x86_64 编 xsdcxx（xsd-4.0.0+dep make / build2），预生成产物是纯 C++ 源码与平台无关 |
| 环4 无法上 C++11 | `-std=c++03` 或 `-D_LIBCPP_ENABLE_CXX17_REMOVED_AUTO_PTR`（libc++ 逃生口，仅过渡） |
| 环3 无法 patch CMakeLists | `CMAKE_DISABLE_FIND_PACKAGE_XSDCXX` + 外层 add_custom_command 注入 |
| boost_thread 硬需求 | 源码内嵌 header-only 替代或换 std::thread（本例实测等价） |

## 验证

- 本地 conan create（OHOS arm64）PASS
- 上游 5 测试可执行文件 84/84 PASS：bindingstest 27、conversiontest 39（含 threadLocalTest 并发用例）、kolabconversationtest 4、parsingtest 3、validationtest 11
- test_package：Kolab::Note 序列化→反序列化 round-trip PASS
- 证据：archives/l/libkolabxml/1.2.1/reports/upstream-tests-evidence.txt

## 查重与增量（覆盖判断）

| 既有条目 | 主题 | 为何不覆盖 |
|---------|------|-----------|
| E026 | TLS glibc 扩展 vs musl | 讲的是**编译器 TLS 语法**支持差异；本链讲的是**boost_thread 库缺失**下 thread_specific_ptr 的依赖替代——错误签名（get_tss_data undefined）与修法（thread_local）都不同 |
| E507 | pthread 能力检测 | CheckCXXSymbolExists 检测策略，与代码生成/语义迁移无关 |
| E546-draft（gupnp-av） | XSD **运行时**寻址（DATADIR 宏） | 讲 schema 文件装载路径；本链讲**构建期** xsdcxx 代码生成工具链——同词不同题 |
| DRAFT-bulletml-auto_ptr（他人） | auto_ptr **shim**（库保持 C++98，消费者 C++17） | 修法是布局兼容兼容层；本链（环4）是**源码级迁移** unique_ptr+std::move，适用有源码控制权的场景——互补不撞题 |
| DRAFT-E-autoptr-unique-ptr / DRAFT-E-xsd-toolchain-pregen（本 PR 单点草稿） | 环4 / 环1-3 的单点展开 | 本条目是**五环组合链**：单点各自成立，但"工具链 flag ↔ 宏体系 ↔ 语义迁移"的配套关系（如 --std c++11 与 XSD_CXX11 的耦合）只在链级条目中完整呈现 |

## 推广价值

一切"业务库 + 代码生成器生态"同时停更的 C++ 老库（XSD/gsoap/类似 2014 前生成器系），迁移到 OHOS 交叉编译环境时的完整路径模板：**工具自举 → 预生成落盘 → CI 零工具依赖 → 语义迁移 → 宏/构建系统配套**。
