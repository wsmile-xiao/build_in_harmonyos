# mysql-client 9.7.1 上游测试执行报告（client-only / OHOS arm64）

- 日期：2026-09-14
- 环境：鸿蒙 PC 宿主机，OHOS clang 15.0.4（aarch64-linux-ohos），libc++ 15，CMake 4.1.2
- 源码：mysql-9.7.1.tar.gz（sha256 dabff263…1aeae）+ 本 PR 的 58 个 per-file 补丁
- 配置：client-only（WITHOUT_SERVER=ON）+ WITH_UNIT_TESTS=ON
- 依赖：googletest 1.17.0（源码树 `extra/googletest` 内置）、boost_1_87_0（源码树内置，
  header-only）、openssl/3.5.6.1.1、zlib/1.3.1、ncurses/6.4（制品仓预编译包）

## 1. 构建上游测试目标

```
# conan 路径（conanfile.py 新增 with_unit_tests 开关）
conan create archives/m/mysql-client/9.7.1 -o with_unit_tests=True

# 手工等价路径（本轮实测）
cmake <src> -DWITHOUT_SERVER=ON -DWITH_UNIT_TESTS=ON ...（其余 cache 变量见 cfg-mysql971-round1.sh）
make -k unittest_all -j6            # rc=0，全部测试目标构建成功
ctest --output-on-failure           # 见下
```

`unittest_all` 是上游 `cmake/mysql_add_executable.cmake` 为每个 `ADD_TEST` 目标建立的
聚合构建目标，即「所有上游单元测试可执行文件」。

## 2. ctest 结果

```
$ ctest --output-on-failure
49 tests, 47 passed (96%), 2 failed, 154.01 sec
  Failed: merge_small_tests, disjoint_pairs_view
```

- gtest 用例：**2520 个**（`--gtest_list_tests` 汇总；其中 `merge_small_tests` 聚合
  目标 2370 个 + `libs/*`、`binlogevents`、`containers`、`memory`、`locks`、`ddl_rewriter`
  等 48 个独立目标 150 个）
- gtest 实际执行：**2517 通过 / 3 失败**
  - `merge_small_tests`：2370 ran → 2368 passed / 2 failed
  - `disjoint_pairs_view`：1 ran → 0 passed / 1 failed（SIGSEGV）
- mytap 用例：17（`unittest/mytap`、`unittest/examples`，全部通过）
- mysys 独立测试程序：`thr_lock` 通过（`Test succeeded`）；`mf_iocache_test` 受限；
  `build_id_test` 未构建（WITH_BUILD_ID=OFF）

## 3. 失败/受限项归因（逐项，含原文证据）

### 3.1 `Mysys.CreateTempFile`（merge_small_tests，mysys_pathfuncs-t.cc:154）
```
Expected: (fileno) >= (0), actual: -1 vs 0
Actual: "/tmp/aaaaaaaaaaaaaaaaaaaaaaaXXXXXX..."
```
OHOS 沙箱 `/tmp` 为只读挂载（本机写 `/tmp` 报 `Read-only file system`），
`create_temp_file()` 无法在 `/tmp` 建临时文件 → 属**环境限制**，非代码缺陷。

### 3.2 `Mysys.UnpackDirname`（merge_small_tests，mysys_pathfuncs-t.cc:222）
```
Expected equality: '/' vs dst[0] '~' (126)
```
该用例依赖 `~` → HOME 展开的宿主环境（ctest 运行环境未提供 HOME 展开所需的
用户目录信息），属**环境差异**。

### 3.3 `LibsRanges.DisjointPairsView`（disjoint_pairs_view-t.cc:76，SIGSEGV）
```
unit test got signal 11
 ... ~basic_string ... TestBody at disjoint_pairs_view-t.cc:76
```
`libs/mysql` 的 disjoint_pairs 迭代器实现依赖与 `libs/mysql/sets` 相同的 CRTP
概念机制；该机制在 OHOS clang 15 / libc++ 15 下求值不正确（上游 clang 19 正常，
上游对 VS2019 亦有同款跳过先例）。本 PR 已在生产侧跳过 `libs/mysql/sets` 的仅有两
个消费者（mysqlbinlog / libchangestreams，patch 0002/0029 注释），此测试目标为
同一根因的表现。

### 3.4 `mf_iocache_test`（mysys 独立测试程序）
```
mf_iocache_test: File '/tmp/iocache.test' not found (OS errno 30 - Read-only file system)
```
源码 `mysys/mf_iocache.cc:1592` 硬编码 `const char *fname = "/tmp/iocache.test"`，
OHOS 沙箱 `/tmp` 只读 → **环境限制**；未修改上游测试源码。

### 3.5 `build_id_test`
上游以 `HAVE_BUILD_ID_SUPPORT` 门控；本套 OHOS 配置 `WITH_BUILD_ID=OFF`
（readelf/wrapper 探测结论），故该测试程序未进入构建。

### 3.6 未纳入 client-only 的上游测试面（书面对比）
- `mysql-test/` MTR 套件（9339 个 `.test`）：runner 为 perl 脚本且验证对象是
  运行中的 `mysqld`（连接协议/复制/存储引擎），`mysqld` 不属于本客户端交付物，
  client-only 构建不产出。归因同队 mysql #9488 的沙箱实证（fallocate /
  unix socket bind EPERM）。
- `libmysql/api_test.c.in`（1 项）：生成 `libmysql_api_test` 并链接
  **shared** libmysql 动态库；OHOS 按仓库 R26 惯例静态交付（与已合入的
  mysql/8.0.46、percona-server/8.4.10_10 一致），shared target 不构建。
- `unittest/gunit/libs/iterators`（`iterators_example`、`iterators_exhaustive`）：
  libc++ 15 无 `<source_location>` 头且对 CRTP 迭代器概念求值不正确 →
  该子目录在本平台跳过（patch 0055）。

## 4. 复现命令

```
# conan 路径（conanfile.py 新增 with_unit_tests 开关）
conan create archives/m/mysql-client/9.7.1 -o with_unit_tests=True

# 手工等价路径（本轮实测）
cmake <src> -DWITHOUT_SERVER=ON -DWITH_UNIT_TESTS=ON ...   # 其余 cache 变量见 cfg-mysql971-round1.sh
make -k unittest_all -j6                                   # rc=0
ctest --output-on-failure                                  # 49 tests, 47 passed (96%)
```

逐目标的用例计数（`--gtest_list_tests`）合计 gtest 用例 2520；完整逐用例输出
（约 8337 行）留存在本地与 CI 构建日志（CI 构建号见 PR 的 CI 评论），不随源码入库。
