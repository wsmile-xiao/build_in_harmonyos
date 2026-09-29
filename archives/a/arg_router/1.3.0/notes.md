# arg_router 1.3.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt 3.18+；manifest `build.system: cmake`）
- 编译日期: 2026-09-28
- 编译器: clang/clang++ 15.0.4（`aarch64-unknown-linux-ohos`，HNP 工具链），libc++；
  Conan profile `ci/conan/profiles/ohos-aarch64`（os=OHOS/6.0、arch=armv8、
  compiler.version=15、compiler.libcxx=libc++、compiler.cppstd=17、build_type=Release）
- 编译标准: 主测试树与 death 目标 **C++20**（上游默认形态，见「问题 4」）、
  `examples/c++17/*` = C++17、`examples/c++20/*` = C++20（各自 `target_compile_features`）
- 并行度: `tools.build:jobs=4`（配方 generate() 内 define；cpu_count=20 / affinity=8，
  不钉会 2.5× 超订）
- 状态: built（O5：合并并确认 release upload 之前一律 built）

## 编译步骤

1. 源码三路取证（W0-1）：`git ls-remote --tags https://github.com/cmannett85/arg_router`
   → 9 个 tag 全量命中，`v1.3.0` = `ea82e8c94c84b8df80b38a37b65162c70d10b276`（轻量 tag）；
   官方 tag 归档实测 sha256 = `4ef2ec923046c26d65b19f06630b3180a81189362d8920a68113c7d921ca968b`
   （299 585 B，解包 3.6 M）== 任务卡 CCI 记录值。
2. Conan 配方构建（CI 同路径）：
   ```bash
   conan create archives/a/arg_router/1.3.0 \
     -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
   ```
   配方内部：`generate()` 落盘 `arg_router_adapt_hook.cmake` 并经 `CMAKE_PROJECT_INCLUDE`
   注入（`unset(CMAKE_CXX_STANDARD)` + 补 `Boost::boost` 目标）→ `cmake.configure()`
   （cache 变量 `DISABLE_VCPKG=ON`、`BUILD_UNIT_TESTS_AND_EXAMPLES=ON`、
   `BUILD_CPP20_EXAMPLES=ON`、`ENABLE_CLANG_FORMAT_CHECKS=OFF`）→ `cmake.build()` →
   层 1 上游测试 `ctest --test-dir <build> --output-on-failure -V`（沙箱 HOME =
   `<build>/test-home`）→ `package()` 拷贝 79 个 `.hpp` + LICENSE + README 并做安装树清点。
3. 消费者层：`test_package/` 经 CMakeDeps 的 `arg_router::arg_router` 链接打包头文件，
   以**声明的最低标准 C++17**（+ span-lite）编译并运行 6 条断言。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 任务卡写「0 依赖」，实际构建要 Boost | 上游 CMakeLists `find_package(Boost 1.74 REQUIRED)`、`unit_test.cmake` 再取 `COMPONENTS filesystem`；源码 include `<boost/mp11/*.hpp>`、`<boost/lexical_cast.hpp>`、`<boost/process/{io,search_path,system,child}.hpp>`；上游自带 conanfile.py 也写 `boost/[>=1.74.0]` | W0-2 实查 `conan list -r=ohpcd "boost/*"` 15 个版本、`conan install --build=never` rc=0 命中远端 binary ⇒ 依赖可得不构成止损，按实有依赖登记 `boost/1.85.0` + `span-lite/0.11.0` |
| 2 | boost 15 个版本选哪个（踩了三个坑） | ①`boost/1.90.0` 是裁剪版：只导出 headers + `libboost_unit_test_framework.a`，无 `Boost::filesystem`；②`boost/1.90.0.3/.4.1` 走 `BOOST_INCLUDE_LIBRARIES` 选择性安装且不含 `process`；③**Boost ≥1.88 把 Boost.Process v1 挪进 `boost/process/v1/`**，实测 1.90.0.4 包内 `boost/process/{io,search_path,system,child}.hpp` 四个头全缺（上游 `test/test_helpers.cpp` 正好 include 这四个） | 逐版本实查后锁定 **`boost/1.85.0`**：整棵 `boost/*` 头文件 + `libboost_filesystem.a` + 远端已有本 profile binary `32b74e3e…`，还自带 OHOS musl 的 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE` 传播 |
| 3 | 上游 `library.cmake` 链 `Boost::boost`，configure 报 target not found | ohpcd `boost/1.85.0` 导出的是 `Boost::headers`/`Boost::filesystem`/… 与**小写**根目标 `boost::boost`（CMake 目标名大小写敏感） | 配方 `generate()` 落盘 CMake 钩子、经 `CMAKE_PROJECT_INCLUDE` 在 `project()` 末尾补一个 `Boost::boost` INTERFACE 转发目标到 `Boost::headers`；**不改上游任何源文件** |
| 4 | **4 个 death 用例假失败**：`root_wrapper_suite/death_test`、`compile_time_string_suite/death_test` 期望的 static_assert 文本没出现，报 `use of undeclared identifier 'multi_lang'` / `unknown type name 'S_'` | 标准错位：conan toolchain 无条件 `set(CMAKE_CXX_STANDARD 17)`（命令行/-D 全被盖掉，实测 `-DCMAKE_CXX_STANDARD=20` 无效）⇒ `unit_test.cmake` 见其已定义就不再给主测试树加 `cxx_std_20`（主树 17，于是那些「只在 C++17 存在」的用例被编进来），而 `death_test.cmake` 是**无条件** `target_compile_features(cxx_std_20)`（death 目标 20，`AR_ENABLE_CPP20_STRINGS` 定义 ⇒ `multi_lang`/`S_` 都不存在）⇒ 片段编译出的错误里没有期望文本 | 钩子里 `unset(CMAKE_CXX_STANDARD)`，回到**上游默认**：主测试树 `cxx_std_20`，与 death 目标同为 20，上游自己用条件编译把那 10 个用例排除（`pr_checker.yml` 默认 job 就是这个形态）。实测 unset 前 4 失败 / unset 后全绿 |
| 5 | 上游 `external/vcpkg` 是空目录 | tag 归档不含子模块内容，`path_prefixer(CMAKE_TOOLCHAIN_FILE …)` 会把不存在的路径交给 CMake | `-DDISABLE_VCPKG=ON`（上游自带开关） |
| 6 | 死亡测试（`death_test_compile`）依赖运行期 `cmake --build .. --target arg_router_death_test_N` | 上游把 8 个 stub 目标设为 `EXCLUDE_FROM_ALL`，靠测试程序在运行期改写 `test/death_test/main_<i>.cpp` 再重编译、断言**编译失败**并匹配诊断文本 | 保持上游形态不动；测试执行的 cwd 必须与 CTest 注册目录一致（配方 `build()` 直接以 `<build>/test` 为 cwd 调 ctest），`cmake` 由 `conanbuild` env 提供 |
| 7 | `--list_content` 数不出用例（`Case:` 恒 0） | Boost 1.85 的 `--list_content` 是 HRF 树：`<indent><name>*`（`*` = `RS_ENABLED`），master suite 不打印，**没有 `Case:` 前缀** | 改按「总行数 − 名字以 `_suite` 结尾的套件行」计数，并与逐行守卫脚本独立复算的 354 互证 |

## 源码修改

**无。** `conandata.yml` 的 `patches: {}`，零补丁 —— W0-3 三组 grep（ISA 专属头、
glibc printf 钩子族、`#error Unknown CPU|other architectures are not supported|
allowed_architectures`）在 `include/ test/ examples/` 下全零命中，所有适配都在配方侧完成。

## 依赖版本

- `boost/1.85.0`（headers 全量 + `libboost_filesystem.a`，远端 binary `32b74e3e…`）
- `span-lite/0.11.0`（header-only，C++17 面的 `<nonstd/span.hpp>` 提供方，远端 binary `6b129b06…`）
- 传递：`zlib/1.3.Z`（boost iostreams 组件的可选链，不进本包 link 面）
- 工具链：clang 15.0.4 / cmake 4.1.2 / conan 2.29.1（均来自 profile 与 HNP）

## 验证结果

（实跑读数以本轮采信轮证据为准：`reports/test-report.md`、`reports/conan-create.log`。）

```bash
# N（源码宏数，候选最大值）
grep -rnoE 'BOOST_(AUTO|FIXTURE|PARAMETER|TEMPLATE)_TEST_CASE' <src>/test/ | wc -l   # → 364
# N′（框架注册数 = 实跑）：配方 build() 内 `--list_content` 用例行硬断言 = 354
# 差额 NOT_RUN = 10，全部归因于 C++20 下上游条件编译排除「只在 C++17 存在」的用例
# （逐行预处理守卫跟踪脚本复算 364 → 354，见 test_package/MANIFEST.yml「N 的取数命令」）
```

| 口径 | 值 | 说明 |
|---|---|---|
| 源码宏数（N） | 364 | 360 BOOST_AUTO_TEST_CASE + 4 BOOST_FIXTURE_TEST_CASE |
| 框架注册数（N′ 实跑） | 354 | `--list_content` 用例行，build() 内硬断言 |
| CTest 注册数（程序口径，不作 N） | 1 | 1 个聚合可执行 `arg_router_test` |
| 断言宏数（源码静态 749；执行面） | 739 | 10 个未编译用例只贡献 10 条（全在 root_wrapper_test.cpp） |
| 消费者断言数（鸿蒙特有，不进上游分母） | 6 | `test_package/test_arg_router.cpp` 末行 `ARG-ROUTER-CONSUMER checks=6` |

## 注意事项

- **包目录是全新的**（`archives/a/arg_router` 不在 upstream/main）—— `task_init.sh` 以
  `--allow-unpublished` 放行；分支名门禁 `feat/arg_router-1.3.0` == `arg_router-1.3.0` ✓。
- 10 个 NOT_RUN 用例**既非 PASS 也非 SKIP**，按 §7.3 单列并给出 `config.hpp` 守卫原文；
  把全局标准钉成 C++17 不会让它们跑起来，反而制造「主树 17 / death 目标 20」的错位
  （实测 4 个 death 用例假失败），所以按上游默认走 C++20。
- 库本体声明的最低标准是 C++17（`check_min_cppstd(17)`）；C++17 消费面需要 span-lite，
  本配方已把 span-lite 作为传递依赖给出，消费者 `find_package(arg_router)` 即可直接编译
  （test_package 就是按 C++17 编的）。
- 零补丁 ⇒ 无 `patches/` 文件、无 `patch_*` 改写、无 H4/H3 注释类命中面。
