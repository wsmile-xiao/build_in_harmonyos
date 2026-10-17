# libsoci 4.0.3 适配记录

## 上游与交付

- **上游**：SOCI — Simple Open-source C++ database access library 4.0.3
  （`https://github.com/SOCI/soci`，tag `v4.0.3`，sha256 `4b1ff9c8…f934928`）。
  平台任务：`libsoci` / `4.0.3`（【依赖项】，`feat/libsoci-4.0.3`）。
- **交付**（安装布局与上游 CMake 一致）：
  - `lib/libsoci_core.so`、`lib/libsoci_sqlite3.so`、`lib/libsoci_empty.so`
    （OHOS 上是**无版本号**实体文件 + ELF `DT_SONAME` 同名的形态，见 OHOS 适配要点 6；
    不做 `.so.4.0.3`/`.so.4.0` 软链；静态构建时是对应的 `.a`）
  - `include/soci/*.h`（含生成的 `soci-config.h`）、`include/soci/sqlite3/soci-sqlite3.h`、
    `include/soci/empty/soci-empty.h`
  - `lib/cmake/SOCI/SOCIConfig.cmake`（上游自带，目标 `SOCI::soci_core` 等）
  - `licenses/LICENSE_1_0.txt`（BSL-1.0）
- **后端范围**：只适配 **SQLite3**（`requires("sqlite3/3.49.1")`）与零依赖的 **empty**
  骨架后端；MySQL/PostgreSQL/ODBC/Firebird/DB2/Oracle 在 OHOS 上没有客户端库，
  显式关闭（SOCI 对缺失依赖本来也只告警不报错，但显式关闭可避免探测到宿主机库造成
  构建结果不确定）。

## OHOS 适配要点

1. **CMake 最低版本**：上游 `cmake_minimum_required(VERSION 2.8)` 在 CMake ≥ 3.31/4.x
   直接报错 → 传 `CMAKE_POLICY_VERSION_MINIMUM=3.5`。
2. **SQLite3 依赖接线**：SOCI 自带 `cmake/modules/FindSQLite3.cmake`（老式
   `find_path`/`find_library`，还会去看 `ProgramFiles`），交叉构建下搜索不可靠 →
   直接预设缓存变量 `SQLITE3_INCLUDE_DIR` / `SQLITE3_LIBRARY` 指向 conan 的
   `sqlite3/3.49.1`（该包是 `-fPIC` 静态 `libsqlite3.a` + `sqlite3.h`，可链进 .so）。
3. **C++11 开关**：必须 `SOCI_CXX11=ON`，否则生成的 `soci-config.h` 会让 C++11 及以上的
   消费者编译报 `SOCI must be configured with C++11 support when using C++11`。
4. **shared/static 只出一份**（R26）：`SOCI_SHARED`/`SOCI_STATIC` 跟随 `shared` 选项，
   避免同时装出 `.so` 与 `.a`。
5. **头文件闭包**：`soci/sqlite3/soci-sqlite3.h` 里 `#include <sqlite3.h>`（在
   `namespace sqlite_api` 内），因此 sqlite3 必须以
   `transitive_headers=True, transitive_libs=True` 传递。
6. **⚠️ 共享库必须自带 SONAME，否则运行期按字面量找不到库**（CI #65351 根因）：
   CI 的 `CMAKE_SYSTEM_NAME` 是 `HarmonyOS`，而 CMake 没有 `Platform/HarmonyOS.cmake`
   （会打印 `System is unknown to cmake`），于是平台变量
   `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` 为空 —— 链接时**完全不发 `-soname`**。
   后果有两个，都实测复现（`cmake -DCMAKE_SYSTEM_NAME=HarmonyOS` 原生构建 + `readelf -d`）：
   * `VERSION`/`SOVERSION` 被忽略 → 产物是 `libsoci_core.so`（无版本号）；
   * 因为库里没有 SONAME，ld/lld 把链接命令行上的**路径**原样写进 `DT_NEEDED`，
     而 CMake 给的是**相对路径**：
     ```
     libsoci_empty.so: NEEDED ../../../lib/libsoci_core.so
     soci_empty_test:  NEEDED ../../lib/libsoci_empty.so
     ```
     带斜杠的 `DT_NEEDED` 不走任何搜索路径（`LD_LIBRARY_PATH` 也无效），OHOS 加载器
     只能按字面量找 ⇒ `ctest` 两个用例全挂：
     ```
     Error loading shared library ../../../lib/libsoci_core.so
       (needed by ../../lib/libsoci_empty.so)
     ```
   修法（同仓库 `yajl/2.1.0`、`expat/2.8.4`、`yaml-cpp/0.9.0` 先例）：在 `generate()`
   里按 `self.settings.os == "OHOS"` 补
   `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG="-Wl,-soname,"`，并加
   `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON`。后者保证仍是**无版本号实体文件**
   （SONAME 就等于文件名 `libsoci_core.so`），既让 `DT_NEEDED` 变成可搜索的裸名字，
   又**不建符号链接** —— HMDFS 上 `cmake_symlink_library` 会 `Permission denied`
   （`expat/2.8.2.1.1` 曾因此返工）。
7. **`ctest` 必须显式给 `LD_LIBRARY_PATH`**：同一平台缺失
   `CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG` ⇒ 可执行文件**没有 RPATH**
   （`readelf -d` 无 `RPATH/RUNPATH`）。`conanrun` 只带依赖包（sqlite3）的 `lib`，
   不带本项目构建树的 `build/Release/lib` ⇒ 即使补了 SONAME 仍会
   `Error loading shared library libsoci_core.so`。因此 `build()` 里跑：
   `LD_LIBRARY_PATH="<build_folder>/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ctest --output-on-failure`。
8. **⚠️ `SOCI_VISIBILITY` 必须关掉，否则动态行读取抛 `std::bad_cast`**（CI #65391 根因，
   9 个上游用例 / 23 条断言失败）：
   * `SOCI_VISIBILITY=ON`（上游默认）→ 上游 CMakeLists 设
     `CMAKE_CXX_VISIBILITY_PRESET=hidden` → 模板类
     `soci::details::holder<T>` / `type_holder<T>` 的 **typeinfo 变成各 DSO 私有**，
     不进 `.dynsym`。
   * OHOS libc++ 的 `std::type_info::operator==` **没有"类型名相同就相等"的字符串
     回退**（只看指针）；musl 只在 weak typeinfo **被导出**时才跨模块把它插桩统一
     （仓库先例：`knowledge/drafts/DRAFT-ohos-musl-cross-module-rtti-typeinfo-unify`，
     bali-phy 4.1 patch 0003 真机探针 `explicit_inst_cross_dynamic_cast=OK`）。
   * 于是 `row` 在 `libsoci_sqlite3.so` 内装填、测试程序 `r.get<int>(0)` 在头文件里
     实例化 `holder<int>` → `include/soci/type-holder.h:35` 的
     `dynamic_cast<type_holder<T>*>(this)` 返回 null → 抛 `std::bad_cast`。
     典型报错（`ctest --output-on-failure`）：
     ```
     tests/common-tests.h:2363: FAILED: {Unknown expression after the reported line}
     due to unexpected exception with message: std::bad_cast
     test cases: 65 | 56 passed | 9 failed     assertions: 1642 | 1619 passed | 23 failed
     ```
     失败全部集中在走**动态行绑定**（`soci::row` + `row::get<T>`）的用例。
   * 修法：`SOCI_VISIBILITY=OFF`（上游自带开关）→ `SOCI_HAVE_VISIBILITY_SUPPORT off`
     → typeinfo 走默认可见性进 `.dynsym` → musl 统一后 `dynamic_cast` 正常。
     不改上游任何源码。注意本机原生（glibc/libstdc++）复现不出该问题：
     libstdc++ 的 `type_info::operator==` 有名字回退，hidden 也判等 —— 所以这是
     OHOS 专属差异，必须在真机/CI 上验证。

## 测试证据

| 层级 | 内容 | 结果 |
|------|------|------|
| 上游官方测试 | `SOCI_TESTS=ON` → catch + CTest：`soci_sqlite3_test`（65 个 catch 用例 / 1715 条断言）+ `soci_empty_test` | ctest 2/2 通过（**本地原生 gcc 实测**）；CI 在 `build()` 里原生跑 ctest（OHOS 侧的 `DT_NEEDED`/RPATH 坑见 OHOS 适配要点 6、7） |
| 完整消费者用例（rule12） | `test_package/test_libsoci.cpp`：SQLite3 后端 + 内存库 → 预编译 `use` 绑定写 1000 行 → 聚合 count/sum/avg（1000 / 250250.0 / 250.25）→ `rowset<soci::row>` 迭代与列元数据（列名 `id`）→ NULL 指示器（`i_null`）→ 事务回滚（行数不变）/提交（+1）→ 参数化查询（id=500 → 250.0）→ 非法 SQL 抛 `soci_error`（带 `no such table` 消息）→ `sqlite_api::sqlite3_libversion()` = 3.46.1 → `sqlite_master` 系统表 1 张用户表 | **14/14 通过**（本地原生编译 + 运行实测） |
| 适配自检（M） | `test_package/test_layout.py`：三个库、6 个公开头、CMake 集成、许可、未夹带测试程序、`soci-config.h` 的 C++11 声明 | **13/13 通过** |

SOCI 自身的测试逻辑**未做任何修改**；只有一个作用在**第三方测试框架头**上的
可移植性补丁 `patches/0001-catch-urng-unsigned-result-type.patch`：

SOCI 4.0.3 自带 Catch **v1.9.6**（`tests/catch.hpp`，2017 年的单头文件版本），其中
`Catch::RandomNumberGenerator::result_type` 是**有符号**的 `std::ptrdiff_t`。
OHOS 的 libc++ 会静态断言拒绝 result_type 为有符号整型的 URNG
（`__libcpp_random_is_valid_urng`，LLVM D120630），于是 `Catch::RandomNumberGenerator::shuffle`
→ `std::shuffle` → `std::uniform_int_distribution::operator()<RNG>` 编译直接失败：

```
error: static assertion failed due to requirement
  '__libcpp_random_is_valid_urng<Catch::RandomNumberGenerator, void>::value'
```

补丁把该 typedef 改成 `unsigned int`（与紧随其后的 `min()=0` / `max()=1000000`
取值范围一致），洗牌语义不变；`operator()(n)`、`operator()()`、`std::shuffle` 的调用
路径都不受影响。验证：
* `patch -p1` 干净应用（上下文唯一）；
* 单独 TU 在 **C++11 与 C++17** 下都能编译并跑通 `Catch::RandomNumberGenerator::shuffle`
  （libstdc++，`shuffled sum=36` 校验通过）；
* 应用补丁后原生构建 + `ctest` 仍通过（`soci_empty_test` 1/1 Passed）。


## 本地验证的边界（如实说明）

本工作站（x86_64）**没有 OHOS NDK/toolchain**（`/data/service/hnp/bin/clang` 只存在于
CI 的鸿蒙 PC 上），因此本地无法跑 `conan create` 的 OHOS 交叉构建；本地的验证方式是
**用同一份源码 + gcc 原生复现 recipe 的 CMake 变量**（configure 选项、`SQLITE3_*`
缓存变量、`SOCI_CXX11`），跑通上游 ctest 套件与消费者用例；OHOS 侧的构建/真机执行由
平台 CI（`ci/conan/build_and_test.sh`，host/build profile 同为 `ohos-aarch64` →
原生构建 → `build()` 里的 ctest 与 test_package 都会真跑）完成。

**复现「未知平台」路径**：CI 的失败点在平台层而非 SOCI 源码层，因此本地直接把 CMake
的 `CMAKE_SYSTEM_NAME` 设成 CI 用的 `HarmonyOS` 来复现同一形态
（`cmake -DCMAKE_SYSTEM_NAME=HarmonyOS …`，CMake 4.2.3 + gcc 15.2，
`SOCI_EMPTY=ON`/`SOCI_SQLITE3=OFF` 以免依赖 sqlite3 头文件）：

| 形态 | 链接产物 | `readelf -d` |
|------|----------|--------------|
| 修前（现状） | `Linking CXX shared library ../../../lib/libsoci_empty.so`（无版本号） | 三个库**都没有 SONAME**；`libsoci_empty.so` 的 `NEEDED` = `../../../lib/libsoci_core.so`，`soci_empty_test` 的 `NEEDED` = `../../lib/libsoci_empty.so`；无 `RPATH/RUNPATH`；链接器即告警 `../../../lib/libsoci_core.so, needed by ../../lib/libsoci_empty.so, not found` |
| 修后（+SONAME 旗标 +`NO_VERSIONED_SONAME`） | 仍是无版本号实体文件（不建链） | `SONAME: libsoci_core.so`；`NEEDED` = `libsoci_core.so` / `libsoci_empty.so`（裸名字） |
| 修后 + `ctest`（不带 `LD_LIBRARY_PATH`） | — | 仍 `Failed`（无 RPATH，裸名字也搜不到） |
| 修后 + `ctest`（`LD_LIBRARY_PATH=<build>/lib`） | — | `1/1 Test #1: soci_empty_test ... Passed`，`test cases: 1 \| 1 passed` |

即：**SONAME 与 `LD_LIBRARY_PATH` 两处缺一不可**，这也是 `build()` 里两处改动的依据。

## 消费者用例与 CI 的 L1e（R34）

`conan test` 会重新编译并链接 test_package；CI 的 L1e 会把 `lib/`、`include/` 移走后
重跑 `conan test` —— 本测试必须因此编译失败，证明它**真正依赖**本包的产物
（库 + 头文件），而不是跑了个空壳脚本。
