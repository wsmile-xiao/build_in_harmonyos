# libyang 5.8.6 — HarmonyOS PC (aarch64) 适配笔记

- 上游：libyang（CESNET）—— YANG 数据建模库（schema 编译、实例数据解析、校验）
- 仓库：https://github.com/CESNET/libyang
- 版本：**5.8.6**（最新稳定 release，2026-06-22；tag `v5.8.6`）
- 许可证：BSD-3-Clause
- 构建系统：CMake（≥3.22）
- 依赖：**pcre2/10.47**（上游 `find_package(PCRE2 10.21 REQUIRED)`）；
  cmocka/2.0.2 仅用于构建上游测试（`build_requirements` 里 test_requires）；
  xxhash 可选，未启用
- 包形态：库 `libyang.so`/`libyang.a` + 头文件 + YANG 模块目录，
  另含 **yanglint / yangre** 两个工具（ENABLE_TOOLS 默认 ON）→ 需要 commands.json（R38）
- 状态：**READY_FOR_HARMONY** —— 本地（直接构建上游）已验证，conan 侧待真机

## 1. 上游测试清点（R51 三步法第 1 步）

| 项 | 值 | 依据 |
|---|---|---|
| `upstream_test_targets` | **57** | `tests/CMakeLists.txt:10-38` 的 `ly_add_utest()` 对每个用例 `add_test` |
| `upstream_test_files`   | **57** | `tests/utests/CMakeLists.txt` 里 57 次 `ly_add_utest(NAME ...)` |
| `upstream_case_total`   | **57** | 同上（逐条可数，可靠枚举） |

该构建下 `ctest -N` 共 61 项 = 57 utests + `headers`（风格检查）+ 3 个 `regress_fuzz_*`。
本配方只跑 `ctest -R "^utest_"`，其余三项不声明为通过（见 MANIFEST 的逐条说明）。

## 2. ⚠️ 上游对静态构建关闭全部测试（决定了 default shared=True）

```cmake
if(NOT BUILD_SHARED_LIBS)
    message(STATUS "Disabling tests for static build")
    set(ENABLE_TESTS OFF)
    set(ENABLE_VALGRIND_TESTS OFF)
endif()
```

静态构建下 **57 个测试目标根本不会生成**（我第一次本地配置就踩到：`ls tests/utest_*` = 0）。
所以 `default_options` 里 **shared 默认为 True**。libyang 不是系统同名库，
R26 的静态要求不适用，shared 由 Conan 管理依赖链。

## 3. ⚠️ 运行时必须能找到内置 YANG 模块（打包关键点）

`ly_ctx_new(NULL, 0, &ctx)` 会失败：

```
libyang[0]: Loading "ietf-inet-types@2025-12-22" module failed, not found.
ly_ctx_new(dir=(NULL)) -> err=5 ctx=(nil)
```

必须把含内置 `.yang` 的目录传进去（实测）：

```
ly_ctx_new(dir=/…/modules) -> err=0 ctx=0x…
```

上游把 `modules/` 安装到 `${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_DATADIR}/yang/modules/libyang`
（`CMakeLists.txt:259, 452`），Conan 包内即：

```
<package_folder>/share/yang/modules/libyang
```

test_package 通过 CMake 变量把该绝对路径编进消费者程序（`LIBYANG_MODULES_DIR` 宏）。
**使用本包的其它项目也需要同样处理**，这一点在 README 里写明了。

## 4. `lyd_validate_all` 的语义陷阱

直接 `lyd_validate_all(&tree, ctx, 0, NULL)` 会连同上下文里**所有**模块一起校验，
内置的 `ietf-yang-library` 有强制节点，于是报：

```
libyang[0]: Mandatory node "content-id" instance does not exist. (data path: /ietf-yang-library:yang-library)
```

只想校验自己那份数据时应传 `LYD_VALIDATE_PRESENT`（上游注释：*Validate only modules
whose data actually exist*）。修正后 9/9 全过。

## 5. 本地排雷受限，改用「直接构建上游」

libyang 的依赖 pcre2 在制品仓里是 **OHOS 适配版配方**（构建脚本硬编码
`/data/service/hnp/bin/bash`），在 WSL 上 `conan create` 必然失败：

```
zlib/1.3.2: RUN: CONFIG_SHELL=/data/service/hnp/bin/bash CC="/usr/bin/clang" …
zlib/1.3.2: ERROR:
```

因此本项目本地验证改为**直接构建上游**（自建 pcre2 10.47 + cmocka 1.1.7，
再 configure/build/ctest），真机再验证 conan 侧。记录于此以免后人重复踩。

## 6. 本地实测结果（直接构建上游）

```
$ cmake -S libyang-5.8.6 -B lys -DENABLE_TESTS=ON -DENABLE_VALGRIND_TESTS=OFF \
        -DENABLE_FUZZ_TARGETS=OFF -DENABLE_YANGLINT_INTERACTIVE=OFF -DBUILD_SHARED_LIBS=ON
$ make -j4            # 库 + yanglint + yangre + 57 个 utest 二进制
$ ctest -R "^utest_"  # 57/57 Test … Passed
100% tests passed, 0 tests failed out of 57      (6.11 sec)
$ ./test_libyang      # 消费者 9/9（含 3 项负向断言）
all libyang consumer checks passed
```

## 7. 待真机验证内容（READY_FOR_HARMONY 清单）

1. `conan create`（clang 15 / aarch64-ohos）：pcre2/10.47 与 cmocka/2.0.2 用制品仓
   预编译二进制；shared 构建在 OHOS 上正常
2. 真机 ctest 57/57（重点看依赖 pcre2 正则、XML/JSON 解析、schema 编译的用例）
3. test_package 9 项断言，特别是**模块目录路径**（`<package_folder>/share/yang/modules/libyang`）
   在安装后是否存在、`ly_ctx_new` 能否加载内置模块
4. yanglint / yangre 两个工具是否正常链接与执行（commands.json 已声明）
