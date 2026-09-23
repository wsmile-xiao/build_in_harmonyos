# chaiscript 6.1.0 适配笔记

## 基本信息

- 上游：https://github.com/ChaiScript/ChaiScript （tag v6.1.0，2017 末版）
- 许可：BSD-2-Clause
- 语言/标准：C++14
- 依赖：无（header-only，stdlib 编译进消费者 TU）
- 交付形态：header-library，仅打包 `include/chaiscript/`（47 个 .hpp）+ LICENSE

## 上游测试清点（R51）

| 项目 | 数量 | 驱动方式 |
|------|------|----------|
| unittests/*.chai 脚本测试 | 234 | `chai unit_test.inc <test>`（ctest 注册，exit(-1)=失败） |
| unittests/3.x/*.chai（3.x 兼容） | 140 | 同上 |
| compiled_tests.cpp Catch 用例 | 48 | 捆绑的 unittests/catch.hpp（Catch v1，随源码分发，无网络下载） |
| 独立 C++ 测试程序 | 7 | static_chaiscript / boxed_cast / type_info / c_linkage / integer_literal / multithreaded / multifile |
| REPL 交互测试 | 3 | version_check / version_check_2 / help（依赖 chai REPL 二进制） |
| **合计（ctest 口径）** | **432** | |

不采用上游 CMake 构建的原因（非测试裁剪）：

1. 上游 CMakeLists 对 clang 硬编码 `-stdlib=libc++`（USE_LIBCXX 默认 TRUE），
   且其构建目标（chai REPL 依赖 readline、可 dlopen 的 stl module、预编译
   静态库）均不属于 header-library 交付物。
2. 上游测试改为**等价 harness 在真机全量执行**（见下节），非裁剪：
   - `.chai` 套件：自写 `chai_shim`（复刻 src/main.cpp 的
     exit/quit/throws_exception/get_eval_error/now 注册与
     CHAI_USE_PATH/CHAI_MODULE_PATH 语义），按上游 ctest 同款
     `chai_shim unit_test.inc <test>.chai` 每测试独立进程驱动；
   - C++ 套件：直接编译上游 10 个测试 .cpp（捆绑 catch.hpp）+
     static_libs 两 TU + test_module/stl_extra 模块。
3. 配方 test_package 另含 8 项消费者断言（见 test_package/MANIFEST.yml）。

## 真机上游套件执行结果（2026-09-08，OHOS 6.0 / clang-15 / armv8 / libc++）

| 套件 | 总数 | 通过 | 失败 |
|------|------|------|------|
| `.chai` 脚本测试（unittests/ + 3.x/） | 374 | 363 | 11 |
| Catch 用例（compiled_tests，175 断言） | 48 | 48 | 0 |
| 独立测试程序 | 7 | 6 | 1（multithreaded_test） |
| **合计（REPL 3 个未执行）** | **429** | **417（97.2%）** | **12** |

12 个失败（11 个 `.chai` + multithreaded_test）**单一根因**：全部调用
`load_module()` 或模块加载型构造（dlopen 跨 DSO）：

- **OHOS 跨 dlopen 边界 `std::type_info::operator==` 不成立**。最小探针
  （exe + dlopen .so，双方各实例化同一模板类型）实测：类型名完全相同
  （如 `NSt4__n14listIiNS_9allocatorIiEEEE`）时 `operator==` 仍返回
  false（exe 与模块各持一份 type_info，指针不同；OHOS libc++abi 无
  glibc/libstdc++ 侧的名字比较回退）。chaiscript 的类型分派依赖
  `type_info` 同一性（type_info.hpp `operator==` 仅回退到
  `std::type_info::operator==`），故模块注册的函数无法与主程序的
  字面量/对象分派匹配（典型报错：`to_string(const int)`、
  `push_back_ref(List).(int)`、`==(const string, std::__n1::basic_string)`）。
- 上游 CI（glibc，弱符号合并 + 名字回退）不受影响；此为 OHOS 平台
  C++ 动态插件生态的通用限制，非 chaiscript 配方缺陷。
- **推荐用法不受影响**：伞形头编译内置 stdlib（单 TU，无 dlopen），
  本配方交付即此形态——363 个非模块 `.chai`、48 Catch、6 独立程序、
  test_package 8 断言全部通过。
- multithreaded_test 已补建上游 `chaiscript_stdlib-6.1.0` 模块复测：
  dlopen 与注册成功，仍因跨 DSO 类型分派失败（同根因）。

REPL 交互测试 3 个（version_check×2/help）未执行：被测对象为 chai REPL
可执行文件，不在 header-library 交付物内；version()/eval_file 能力已由
harness 与 test_package 覆盖。

## 平台适配要点

- `chaiscript_threading.hpp`：std::thread/thread_local，无平台分支，无 patch。
- 构造函数在 `_POSIX_VERSION` 下调用 `dladdr()` 探测模块搜索路径；OHOS musl
  libc 提供 dladdr，消费者链接 `CMAKE_DL_LIBS`。
- `ChaiScript()`（伞形头）默认构造编译内置 `Std_Lib::library()`，启动零 dlopen；
  只有单参 `ChaiScript_Basic(parser, ...)` 构造才运行时加载
  `chaiscript_stdlib-<ver>` 模块（使用该构造需自备模块，PR 说明中注明）。
- `CHAISCRIPT_NO_THREADS` / `CHAISCRIPT_NO_DYNLOAD` 宏由消费者按需定义，
  配方不做默认定义。

## 版本与验证

- 首次适配，版本号取上游 `6.1.0`（R37）。
- sha256（GitHub 官方 tag tarball）：
  `3ca9ba6434b4f0123b5ab56433e3383b01244d9666c85c06cc116d7c41e8f92a`
- 本机验证：`conan create` RC=0（MSVC 194 / cppstd14），test_package 8/8 PASS。
- 真机验证：`conan create` 通过（revision 与本机一致 8ece1c3c…），
  test_chaiscript 设备运行 8/8 PASS；jobs=1 全程内存平稳
  （MemAvailable ~13GB，与 botan3 -j1 任务并发）。

## 下一步

- 补建 issue 后提 PR：`【知识库扩展】feat(chaiscript): 6.1.0 编译完成`。
