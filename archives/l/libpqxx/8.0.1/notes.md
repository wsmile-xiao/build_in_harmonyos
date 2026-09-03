# libpqxx 8.0.1 适配笔记

## 基本信息

- 上游：https://github.com/jtv/libpqxx
- 版本：8.0.1（tag 8.0.1，tarball SHA-256 `24f878a1b4249035e4b6c07d49351506bf99f88df584d36bf198d58ebf293823`）
- 类型：C++20 库（编译 `src/*.cxx` 24 个源文件成 libpqxx-N.M.a/.so + 大量 header-only 模板）
- 构建系统：CMake（上游另有 autotools，本适配走 CMake——与 CCI 官方配方一致）
- 最终状态：`built`（conan create + test_package 本地全量通过；未上传制品仓）
- PostgreSQL 官方推荐的 C++ 客户端库

## 依赖

- `libpq/18.1`（ohpcd 制品仓预编译包，W0 实测：`conan download libpq/18.1 -r=ohpcd --only-recipe`
  → revision `6f9e9c128f7c346abe8bbf26fa729453`；唯一二进制包 `01d92cf3...` 为
  `shared=True, OHOS/armv8/clang15/libc++/cppstd17/Release`）
- **注意**：libpq/18.1 的包内 `libpq.a` 引用 `libpgport`/`libpgcommon` 符号但包不带这两个
  伴生库（其 .pc 的 `Libs.private: -lpgcommon -lpgport` 可证），静态链接会报
  `undefined symbol: pg_snprintf` 等；消费者一律链接 `libpq.so`（配方 `requires` 指向
  libpq/18.1，CMakeDeps target `libpq::libpq`）。

## OHOS 工具链三大缺口与对策（本适配核心）

上游 requirements.json 要求 `c++ >= 20, clang >= 16`；本设备为 OHOS clang 15.0.4 +
libc++ 15（15004）。三个 C++20 缺口全部以 portability patch 解决，不改功能逻辑：

| # | 问题 | 根因 | 解决方案 | patch |
|---|------|------|----------|-------|
| 1 | `fatal error: 'source_location' file not found` | libc++ 15 无 `<source_location>`（16 才有） | `include/pqxx/internal/source_location_shim.hxx` 提供 `std::source_location` 最小回退（current/file_name/function_name/line/column 均为占位值），`__cpp_lib_source_location` 存在时自动用真头 | 0005+0006 |
| 2 | `error: call to consteval function 'std::basic_format_string' is not a constant expression`（note: non-constexpr function '__throw_format_error'） | libc++ 15 incomplete `<format>` 的 `__parse_fill_align` 把 `<`/`>` 识别为 fill/align 候选字符走非 constexpr 抛错路径；格式串中 `<` 紧邻 `{}`（模式 `<{`）必触发；最小复现：`std::format("x <{}> y", sv)` 失败、`"x {} < y"` 通过 | 全库仅 4 处字面量命中（array.hxx 1 + test_util.cxx 3），措辞加空格 `< {} >` 规避（纯诊断文本，无测试断言依赖该文本） | 0004+0007 |
| 3 | `undefined symbol: typeinfo for std::__n1::format_error`（链接期） | OHOS 共享 libc++.so 按 `_LIBCPP_HAS_NO_INCOMPLETE_FORMAT` 裁掉了 incomplete format 的运行时符号；符号在 `libc++experimental.a` | CMake（HarmonyOS/OHOS 分支）`add_compile_definitions(_LIBCPP_ENABLE_EXPERIMENTAL)` + `add_link_options(-lc++experimental)`；配方 `package_info` 再向消费者传播 `defines=['_LIBCPP_ENABLE_EXPERIMENTAL']` + `system_libs=['c++experimental']`（ladybug 0.18.2 先例） | 0001 + 配方 package_info |

## 其他关键适配点

- **CMake 依赖接线**：上游 `find_package(PostgreSQL)` 找的是 CMake 内置 FindPostgreSQL
  的 `PostgreSQL::PostgreSQL`；本仓库 libpq/18.1 的 CMakeDeps 命名是 `libpq-config.cmake`
  / `libpq::libpq`。patch 0001/0002/0003 让 `cmake/config.cmake`、`src/CMakeLists.txt`、
  `test/CMakeLists.txt` 优先 `find_package(libpq CONFIG QUIET)`，拿不到再回退
  FindPostgreSQL（非 conan 环境仍可用）。
- **cppstd 覆盖**：ohos-aarch64 profile 钉死 `compiler.cppstd=17`，conan 的 cppstd block
  会在每个编译命令注入 `-std=c++17`，`CMAKE_CXX_STANDARD=20` cache 变量会被压制。
  正确做法：`toolchain.blocks["cppstd"].values["cppstd"] = "20"`（generate() 内）。
  validate() 相应放宽：profile=17/20/23 都接受（工具链实测能编 C++20 源码）。
- **运行时加载**：test_package 二进制动态链接 `/system/lib64/libc++_shared.so`；设备
  shell 的 LD_LIBRARY_PATH 有分隔符后空格的坑（`...chipset-pub-sdk: /system/lib64`），
  `test()` 内用 `Environment().define("LD_LIBRARY_PATH", "/system/lib64")` 显式钉住
  （date 3.0.5 先例）。
- **构建依赖 Python3**：上游 cmake/config.cmake 的 filter_config.py 需要 Python 解释器，
  设备 `/data/app/bin/python3.12` 满足，CI 侧也有（无额外 tool_requires 必要）。

## 验证结果

### conan create（W3）

命令（worktree 根目录，OHC_PROJECT_DIR 指向 worktree）：

```text
python3 -c "from conans.conan import run; import sys; \
sys.argv=['conan','create','archives/l/libpqxx/8.0.1','--name=libpqxx','--version=8.0.1',\
'-pr:h=ci/conan/profiles/ohos-aarch64','-pr:b=ci/conan/profiles/ohos-aarch64','--build=missing']; run()"
```

结果：主包构建 + 安装 + test_package 构建运行全绿，test_package 输出
`libpqxx test_package OK (8.0.1)`。日志：`$HOME/tmp/libpqxx-conan-create8.log`。

### test_package（R34：真实 API 调用）

`test_package/test_package.cpp` 调用：
1. 版本宏 `PQXX_VERSION/PQXX_VERSION_MAJOR/MINOR`（`<pqxx/version>`）
2. `pqxx::to_string(42)/to_string(3.25)`、`pqxx::from_string("1234", i)`、
   `from_string("true", b)`（`<pqxx/strconv>`，纯客户端转换）
3. `pqxx::separated_list(", ", begin, end)`（`<pqxx/separated_list>` 模板工具）
4. `pqxx::connection` 错误路径：连接 `127.0.0.1:1`（必然拒绝）必须抛
   `pqxx::broken_connection` 且 `what()` 非空（`<pqxx/connection>`+`<pqxx/except>`，
   驱动 libpq 真实连接尝试，无需 PG 服务端）

### 上游测试（test/ 目录，80 个 .cxx、298 个注册测试）

构建方式：源码工作目录 CMake `BUILD_TEST=ON`（同 patch 后源码，EXE_LINKER_FLAGS 补
`-lc++experimental`），产出 `test/runner`（runner 支持 `-j N` 并行与按名运行单测）。
执行：`LD_LIBRARY_PATH=<libpq包lib>:<toolchain libc++ dir>:/system/lib64 ./runner -j 2`。

结果：**298 个注册测试，89 通过 / 209 失败**，失败分类（100% 归因清晰）：

| 失败类别 | 数量 | 原因说明 |
|---|---|---|
| `pqxx::broken_connection`：`local user with ID 20020182 does not exist` | 208 | 需要活的 PostgreSQL 服务端。runner 的测试通过 `pqxx::connection` 连本地 PG（默认按 OS 用户名连 unix socket），设备无 postgres 服务端（`which postgres psql pg_ctl initdb` 全空，cmd-pkgs 亦无），libpq 报 local user 不存在。**环境限制，非代码缺陷** |
| `test_source_loc_renders_real_source_location` | 1 | 该测试断言 `pqxx::sl::current()` 渲染出真实文件名/行号；shim（0005/0006）返回 `(unknown)` 占位值，断言按设计失败。**shim 已知限制，如实记录不掩盖** |

89 个通过者均为纯客户端测试（strconv/separated_list/zview/composite 解析/array 解析/
binary_cast/type_name/connection_string 解析等）。日志：`$HOME/tmp/libpqxx-upstream-run.log`。

## 设备日志索引

- conan create 全量：`$HOME/tmp/libpqxx-conan-create8.log`
- 上游测试构建：`$HOME/tmp/libpqxx-upstream-build2.log`（编译期）+ 链接修复说明（`-lc++experimental`）
- 上游测试运行：`$HOME/tmp/libpqxx-upstream-run.log`（298 tests, 209 failed, 89 passed）
- std::format 探针：`$HOME/tmp/libpqxx-smoke/`（format-repro2/3 + 边界实验 fmt-v.cpp）
- W0 依赖实测：本笔记"依赖"小节（revision 6f9e9c128f7c346abe8bbf26fa729453）

## 源码修改

7 个补丁见 `patches/`（refresh-patch --auto 生成的 per-file diff），全部为 OHOS 平台
适配（portability），不改变上游功能逻辑：
- `0001-cmake-config.cmake.patch`：CMake 优先 conan libpq target + OHOS format 开关
- `0002-src-CMakeLists.txt.patch`：src 库目标链接接线（conan 优先，PostgreSQL 回退）
- `0003-test-CMakeLists.txt.patch`：test runner 依赖接线
- `0004-include-pqxx-array.hxx.patch`：array.hxx 格式串字面量 `<{}` 规避
- `0005-include-pqxx-types.hxx.patch`：types.hxx include shim 头
- `0006-include-pqxx-internal-source_location_shim.hxx.patch`：新增 source_location shim
- `0007-test-test_util.cxx.patch`：test_util.cxx 3 处格式串字面量规避
---

**编译结束**: 2026-09-03 02:09
**最终状态**: built
