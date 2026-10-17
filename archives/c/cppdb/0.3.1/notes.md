# cppdb 0.3.1 — HarmonyOS PC 适配笔记

## 基本信息

- **软件**: cppdb（CppCMS 项目的 SQL 连接库）
- **版本**: 0.3.1（2013 年发布；对应 tarball `cppdb-0.3.1.tar.bz2`，251449 字节）
- **上游仓库**: https://github.com/artyom-beilis/cppdb（原始发布页 https://sourceforge.net/projects/cppcms/files/cppdb/）
- **构建系统**: CMake（上游 `cmake_minimum_required(VERSION 2.6)`，无 `enable_testing` 注册）
- **许可证**: BSL-1.0 或 MIT 任选
- **依赖**: sqlite3/3.49.1（制品仓状态 published，可直接引用）

## 源码获取与校验

- `conandata.yml` 使用 SourceForge 官方地址 `https://sourceforge.net/projects/cppcms/files/cppdb/0.3.1/cppdb-0.3.1.tar.bz2/download`（CI 会自动追加 SourceForge 镜像回退，无需手写镜像）。
- sha256 `d60eef5a732d8f84ef5e4a2845a8cefc543a6c75bf3782589c2cf6aa150b992e` 为实测值：从镜像下载 251449 字节（与官方文件大小一致），md5 `129f1d75f46114b79160b93807d5223f` 与 buildroot 上游记录完全一致。

## 上游分析

- 目录结构：`src/`（8 个 cpp：连接管理/池/驱动管理/dlopen 封装/互斥量/原子计数）、`cppdb/`（14 个公共头）、`drivers/`（4 个后端：sqlite3/postgres/mysql/odbc）、`test/`（4 个测试程序 + 各平台运行脚本）、`examples/example1.cpp`。
- 后端选择逻辑：CMakeLists 对每个后端做 `find_library/find_path`，找不到则自动禁用并打印提示；`SQLITE_BACKEND_INTERNAL=ON` 时把后端直接编进主库并通过静态 `initializer` 自注册（`driver_manager.cpp` 末尾），否则编译为 `libcppdb_<backend>.so` 运行时 dlopen。
- 线程/动态加载：`src/mutex.cpp` 非 Windows 分支无条件使用 pthread（musl 的 libc 自带，无需 `-lpthread`）；`src/shared_object.cpp` 用 `dlfcn.h`（仅模块模式运行时调用）。

## 上游测试清点（test/ 目录，静态审计）

| 测试程序 | 断言宏 | 离线可跑 | 说明 |
|----------|--------|----------|------|
| test_basic.cpp | 37 处 TEST（文件内自带 throw-on-failure 宏，只打印 `Ok`） | 是（sqlite 连接串） | 6 处在 2 轮 fetch 循环内，动态执行 43 次 |
| test_backend.cpp | 121 处 TEST + 10 处 THROWS（`test.h` 计数 harness，打印 `Tests: N failed: M`） | 是（sqlite 连接串） | mysql/pg/odbc 连接串需在线服务，本次不跑 |
| test_caching.cpp | 46 处 TEST + 1 处 THROWS（同上） | 是（dummy 驱动，无需任何数据库） | 含约 6 秒 sleep |
| test_perf.cpp | 0 断言（benchmark） | 上游 `run_test_linux_a.sh` 本来就不跑它 | 本次不跑 |
| **断言位置合计** | **215（204 TEST + 11 THROWS）** | | |

mysql/postgresql/odbc 的 6 组连接串需要在线数据库服务，OHOS 上无法补齐（无服务器、无 ODBC 驱动管理器），如实放弃，见 PR 补充说明。

## 适配改动

### 1. 补丁（patches/0001-cmake-minimum-version-cxx14.patch，可移植类）

- `cmake_minimum_required(VERSION 2.6)` → `3.5`：新版 CMake（4.x 起）拒绝低于 3.5 的兼容级别。
- `project()` 后固定 `CMAKE_CXX_STANDARD=14` + `REQUIRED ON`：上游 8 个文件使用 C++17 已移除的 `std::auto_ptr`，而 OHOS profile 默认 `compiler.cppstd=17`；放在 CMakeLists 里 late-set 可稳定覆盖工具链的 cppstd 设置。

### 2. 后端与依赖（conanfile.py）

- `DISABLE_PQ/DISABLE_MYSQL/DISABLE_ODBC=ON`：只留 sqlite，找不到服务端依赖也不再探测，保证确定性。
- sqlite 路径通过 `-DSQLITE3_PATH=<sqlite3 包 include>/-DSQLITE3_LIB=<包内 libsqlite3.a 全路径>` 传入：CMake 的 find 命令对已定义变量跳过搜索，因此无需补丁即可让上游裸 `find_library/find_path` 命中 Conan 包。
- `shared=False`（默认）：`SQLITE_BACKEND_INTERNAL=ON`，后端 baked-in，无 dlopen；`package()` 删除 `.so`。`shared=True`：上游默认模块布局，`package()` 删除 `.a`。
- `package_info`：`libs=["cppdb"]`，`cmake_file_name/cppdb::cppdb`；静态模式追加 `requires=["sqlite3::sqlite3"]`（`.a` 不含 sqlite3 对象）。OHOS（musl）下不声明 `dl/pthread` 系统库（libc 自带）；Linux 分支保留两者。test_package 的消费者链接即是该假设的证伪实验：若静态链接报 `dlopen/pthread` 未定义，下一轮补上。

### 3. 第一层测试：build() 跑上游 sqlite 子集

`_run_upstream_sqlite_suite()` 复刻 `test/run_test_linux_a.sh` 的 sqlite 部分：`test_basic`/`test_backend` 各跑 4 种连接串变体（`''` / `;@use_prepared=off` / `;@pool_size=5` / 两者叠加）+ `test_caching`，共 9 轮。连接串统一追加 `;@modules_path=<构建产物目录>`（模块模式下 dlopen 走绝对路径；内置模式下驱动已预注册，该选项被忽略）。每轮输出全文打到 conan 日志：

- `test_basic`：要求退出码 0 且含 `Ok`（throw-on-failure 语义下退出码 0 即证明 37 处全过），每轮记 discovered+37/passed+37。
- `test_backend`/`test_caching`：解析 `Tests: N failed: M`，要求退出码 0、`Ok` 存在、`M==0` 且 `N>0`，实数累加。
- 汇总打印 `HMBS_UPSTREAM_TEST_RESULT`；任何偏离直接抛 `ConanException` 中断构建（失败无法静默通过）。

证伪说明：harness 本身是“失败即非零退出”（basic 抛异常、backend/caching 返回 1 且无 `Ok`），配方侧又对输出做三重校验（退出码 + 计数行 + `Ok` 关键字），不存在“空跑也 PASS”的静默跳过；`M>0` 或 `N==0` 都判失败。

### 4. 第二层测试：test_package（消费者 + 上游回放）

- `test.cpp`（6 个 `CHECK-OK`）：session 打开 → 建表 → 两次插入（rowid/affected）→ `COUNT(*)` → 按 id 查询校验值，全程真实 API。
- `test_upstream.cpp`（20 个 `UPSTREAM-OK`）：回放上游 sqlite 路径——版本查询、建表、绑定插入、null 标签、时间 round-trip、单行 `cppdb::row` 抓取、BEGIN/ROLLBACK/COMMIT、第二连接可见性、`@pool_size` 池化、DROP 收尾；与上游断点的对应关系见源码注释。
- `test()` 用子进程跑两个二进制（输出落盘并回显到日志），分别计数 `CHECK-OK`/`UPSTREAM-OK` 行：消费者 6/6 → `HMBS_TEST_PACKAGE_RESULT`；回放 20/20 → `HMBS_UPSTREAM_TEST_RESULT`（framework 标 `custom`，command 注明 replay 性质）。行数不符、缺 `ALL-OK` 尾行、退出码非零一律抛异常。标记在 `test()` 内每次都打，conan 缓存命中导致 `build()` 跳过时证据依然存在。

## 遇到的问题与解决

| # | 问题 | 根因 | 解决 |
|---|------|------|------|
| 1 | 上游 `find_library(sqlite3)` 在 Conan 沙箱里找不到系统包 | 上游不支持 find_package，且 OHOS 无系统 sqlite3 | 用 `-DSQLITE3_LIB/-DSQLITE3_PATH` 覆盖（find 跳过已定义变量），零源码改动 |
| 2 | `std::auto_ptr` 在 C++17 下编译失败 | 2013 年代码 + profile 默认 cppstd=17 | 补丁固定 C++14（8 个文件改 unique_ptr 风险更高，暂不做） |
| 3 | 上游测试大多要连在线数据库 | mysql/pg/odbc 需服务端 | 只跑 sqlite 子集（9 轮）+ caching；其余如实声明未跑，不虚报 |
| 4 | `test_basic` 无计数输出，无法做“执行数”统计 | 文件内自带宏只打印 `Ok` | 按静态 37 处记数（退出码 0 即全过），循环内 6 处注明动态执行两次 |
| 5 | 真机 CMake `PTHREAD_LIB ... set to NOTFOUND`（musl 无独立 libpthread） | OHOS musl 的 pthread 在 libc 内，`find_library(pthread)` 返回 NOTFOUND；`DL_LIB` 有 `if()` 守卫而 `PTHREAD_LIB` 无条件链接 | 曾用 `0002` 补丁加 `if()` 守卫，但与 `0001` 同改 CMakeLists.txt 时行号漂移 7 行导致真机 `Failed to apply patch`（`actual: \t${INTERNAL_SOURCES}`）；改用 `conanfile.build()` 内 `replace_in_file` 按字符串匹配加守卫（幂等、无行号依赖），`conandata.yml` 仅保留 `0001` |
| 6 | 真机 `test_basic` 池化变体（`;@pool_size=5`）报 `Failed in 185 sql.once_called()==have_pool` | 配方曾给每个变体分配独立 `basic_%d.db`；池化变体在全新文件上 `DROP TABLE` 必抛异常，被 `throw_guard` 标 `recyclable=false`，`close()` 后连接被销毁而非回池，`open()` 拿到新连接则 `once_called()==false`。上游 `run_test_linux_a.sh` 四个后缀共用一个 `test.db`，变体 0 留下表，后续 `DROP` 成功才进池 | 四个 `test_basic` 变体改共用一个 `basic.db`（套件开始时删一次，与上游共用 `test.db` 一致）；`test_backend` 走 `driver_manager` 直连、无池化断言，保持独立文件。全部变体照跑、断言口径不变 |
| 7 | 真机 `source()` 偶发 `IncompleteRead`（212725/251449 字节）后重试成功 | SourceForge 镜像跳转偶发断流；CI 自带镜像改写不对 SourceForge 生效（`get_mirrors` 原样返回） | `conandata.yml` 的 `url` 改为有序列表：`downloads.sourceforge.net` 直链在前（同一归档的直接文件端点）、官方 `/download` 页在后保底；`sha256`/`filename` 不变 |
| 8 | test_package 的 `test_upstream.cpp:74` 在真机 clang 下 9 个编译错误（`ostream` 与 `int` 的 `==` 非法等） | `UCHECK(cond, name)` 宏内 `<< name` 未加括号，而 73/74 行以三元式 `n == 0 ? "11-..." : ...` 作 `name` 实参；`<<` 优先级高于 `==`/`?:`，展开后变成 `(cout << ...) << n == 0 ? ...`，即 `ostream == int` | 宏的两个输出点改为 `<< (name)`（`test.cpp` 的 `CHECK` 同改；调用点全为字面量，行为不变）。用例计数不变：单轮恰好 20 行 `UPSTREAM-OK`（6 + 每行 4×2 + 6） |

## 验证结果（待真机预检回填）

- `conan create`（ohos-aarch64）：待 HMBS 真机预检执行，届时从日志摘录 `Tests:` 行与两个 HMBS 标记的实数。
- 本地未跑 conan（本机 Windows，按任务守则不在本机验证）。

## 交付与注意事项

- 产物（static 默认）：`lib/libcppdb.a` + `include/cppdb/` + 许可证；`shared=True` 时为 `libcppdb.so(.0/.0.3.1)` + `libcppdb_sqlite3.so(.0/.0.3.1)`。
- `test_perf`（benchmark，无断言）与 `example` 仅编译不运行，与上游脚本行为一致。
- 若真机日志显示静态消费者链接缺 `dlopen/pthread` 符号，在 `package_info` 的 OHOS 分支追加系统库（当前假设 musl 自带）。
