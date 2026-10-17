# osm2pgrouting 3.0.0 — OHOS 适配笔记

## 1. 这是什么

上游 pgRouting/osm2pgrouting 3.0.0（tag `v3.0.0`，注意上游 tag 带 `v` 前缀，
`refs/tags/3.0.0.tar.gz` 是 404）。CMake 工程，产出一个可执行文件
`bin/osm2pgrouting`，把 OpenStreetMap 的 `.osm` XML 导进 PostgreSQL/PostGIS
数据库，生成路径规划所需的拓扑表。安装时还会把 4 个 `mapconfig*.xml` 与
`COPYING`、`README.md` 放进 `share/osm2pgrouting/`。

`package_type = "application"`，因此软件级目录下有 `commands.json`（R38）。

## 2. 依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| libpq | 18.1 | PostgreSQL 客户端库（libpqxx 自己也会拉，这里显式声明） |
| libpqxx | 8.0.1 | C++ 客户端 `pqxx::connection` |
| expat | 2.8.2.1 | `xml::XMLParser` 的 SAX 解析后端（配置与数据文件都用它） |
| boost | 1.84.0 | `boost::program_options` 支撑整个命令行 |

**不依赖 libosmium**：上游确实带了 `cmake/FindOsmium.cmake`，但 `src/` 与
`include/` 里没有任何 `<osmium/...>` 引用——真正的 osmium 导入在
`tools/osmium/`，那是一个独立的辅助程序，顶层 CMakeLists 并不构建它。
（`FILE(GLOB ... "${CMAKE_SOURCE_DIR}/src/*/*.cpp")` 只收 `src/` 两层。）

expat 用 2.8.2.1 而不是仓库里更新的 2.8.4：`expat/2.8.4` 在 ohpcd 上没有
与本 profile 选项匹配的 OHOS 预编译包（`conan install --build=never` 直接报
Missing prebuilt package），而 2.8.2.1 有；同族的 `osm2pgsql/2.3.1` 也用的
2.8.2.1。

## 3. 唯一的补丁：`patches/0001-CMakeLists.txt.patch`

### 3.1 依赖发现必须绕开两个 bundled find 模块

上游 `CMakeLists.txt` 开头：

```cmake
LIST(APPEND CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake")
...
find_package(PostgreSQL REQUIRED)
find_package(PQXX REQUIRED)
include_directories(${PQXX_INCLUDE_DIR})
find_package(EXPAT REQUIRED)
```

`cmake/` 里那两个自定义模块探的都是**构建主机**：

- `FindPostgreSQL.cmake` 先 `find_program(pg_config)`，再 `find_path(... libpq-fe.h)`
  扫 `/usr/include/postgresql*`、`/usr/local/include/pgsql`、`$ENV{ProgramFiles}/PostgreSQL/*/include`；
- `FindPQXX.cmake` 扫 `/usr/include`、`/usr/local/include`。

在 OHOS worker 上，这要么什么都找不到（配置阶段直接 FAILED），要么更糟——
主机上恰好装了 libpq 就把**宿主的**头文件与 `.so` 编进来，产物在设备上根本
跑不起来，而且这种失败取决于 worker 上碰巧装了什么，表现为“跨 worker 抖动”。

补丁把三家都改成走 Conan CMakeDeps 生成的 config 包，`CONFIG` 关键字顺带
让 `CMAKE_MODULE_PATH` 里的同名模块不再被咨询：

```cmake
find_package(libpq CONFIG REQUIRED)
find_package(libpqxx CONFIG REQUIRED)
find_package(EXPAT CONFIG REQUIRED)
set(POSTGRESQL_LIBRARIES libpq::libpq)
set(PQXX_LIBRARIES libpqxx::pqxx)
set(EXPAT_LIBRARIES expat::expat)
```

文件后半段仍在用 `${POSTGRESQL_LIBRARIES}` 这类旧变量名去
`TARGET_LINK_LIBRARIES`，所以把 imported target 映射回这些名字即可——CMake 允许
把 target 当库名传，而且传递性的 include 目录与链接选项会一起跟过来，因此
`INCLUDE_DIRECTORIES(... ${POSTGRESQL_INCLUDE_DIR} ...)` 里那几个空变量无害。

Boost 同理：`find_package(Boost ${BOOST_MINIMUM_VERSION} REQUIRED COMPONENTS program_options)`
会被 CMake 内建 FindBoost（module 模式）截胡，改成 `find_package(Boost CONFIG REQUIRED COMPONENTS program_options)`
后命中 CMakeDeps 的 `BoostConfig.cmake`，`Boost::program_options` 目标存在。

### 3.2 C++ 标准必须抬到 20

上游按 PQXX 版本选标准：

```cmake
if (PQXX_VERSION VERSION_GREATER_EQUAL "7.0.0")
  set(CMAKE_CXX_STANDARD 17)
else()
  add_definitions(-DPQXX_DISCONNECT)
  set(CMAKE_CXX_STANDARD 14)
endif()
```

这条分支写于 PQXX 7 时代，libpqxx 8.x 要求 C++20（上游 requirements.json），
头文件里用了 concepts 与 `std::format`。而仓库共享的 OHOS profile
（`ci/conan/profiles/ohos-aarch64`）把 `compiler.cppstd` 钉在 17。

关键一点：**光在 toolchain 里改没用**。CMakeLists 里的 `set(CMAKE_CXX_STANDARD 17)`
建的是普通变量，会遮蔽 toolchain 写进 cache 的那个同名变量，最终 `-std` 还是 17。
所以配方两头都做：补丁里把这两行直接换成

```cmake
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
```

配方 `generate()` 里同时把 cppstd block 也设成 20
（`toolchain.blocks["cppstd"].values["cppstd"] = "20"`），与 `libpqxx/8.0.1`
的写法一致，免得 profile 的 17 从别的路径再渗进来。

## 4. 运行期

- 二进制动态链接 `libexpat.so` 与 `libpq.so`，静态链接 `libpqxx.a`。因此
  **只要能跑起来，就说明 expat + libpq + libpqxx 这一整条运行期栈都被加载器
  解析成功了**。
- `test_package/test.sh` 里把 `LD_LIBRARY_PATH` 做成
  `/system/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}` —— 前置而不是覆盖：
  设备上的 libc++_shared.so 在 `/system/lib64`（`date/3.0.5`、`libpqxx/8.0.1`
  先例），而依赖目录由 test_package 的 VirtualRunEnv 提供，两者都不能丢。
- 用 `bash` 而不是 `/bin/sh` 跑测试脚本：OHOS 的 `/system/bin/sh`(mksh) 执行
  ELF 不太可靠，profile 里给了 `CONFIG_SHELL`。
- **执行前必须给二进制签名**。OHOS 拒绝执行**未签名**的 ELF：内核回 EPERM，
  shell 报 `Operation not permitted`、退出码 **126**。它与文件权限无关
  （`chmod 755` 已做过仍 126），也与"二进制躺在 conan 包缓存里"无关 ——
  把同一份文件拷到任何可写目录仍然 126，缺的是 **`.codesign` 段**。
  CI #55334 的 22 条断言里有 14 条 fail，全部源自这一条：
  `# exec failed: rc=126 … test.sh: line 59: …/bin/osm2pgrouting: Operation not permitted`。
  修法：`test.sh` 把已安装的二进制 staging 出去后调用
  `/data/service/hnp/bin/binary-sign-tool sign -inFile X -outFile X -selfSign 1`。
  调用前加 `env -u LD_LIBRARY_PATH`：conan 环境会把 OHOS SDK 的 `llvm/lib`
  塞进 `LD_LIBRARY_PATH`，签名器自己的 `NEEDED libc++.so` 于是命中
  `std::__1` 那份，成串 `Error relocating … symbol not found`、退 127
  （`knowledge/drafts/DRAFT-binary-sign-tool-buildenv-ldlibrarypath.md`）。
  仓内先例：`archives/s/sound-juicer/3.40.0/test_package/test.sh`（shell 侧同款做法）、
  `archives/g/glade/3.40.0/test_package/conanfile.py` 的 `_sign()`
  （Python 侧，另加一步 `llvm-objcopy --remove-section .codesign`）。
  签名只能对 **staging 副本**做：就地改包内文件会污染已 compute 的包清单。

## 5. 验收测试为什么这么写

上游没有测试套件（见 `test_package/MANIFEST.yml` 的审计证据），所以 22 条断言
全部是**补全的消费者侧功能验证**，且都是可观测行为，不 grep 二进制：

- `--version` / `-v` → `This is osm2pgrouting Version 3.0.0`；
- `--help` → 打印 `Allowed options` 且列出 `--file`、`--dbname` 两个必需项；
- 不带参数 → 上游 `notify(vm)` 抛 `required_option`，被内层 catch 接住后
  **返回 0** 并把选项表打出来（这是上游行为，断言就照实写 0）；
- `--definitely-not-an-option` → 外层 catch，**返回 1** 且报 unrecognised；
- `-f /dev/null -d <db> -h 127.0.0.1 -p 1` → 先回显 COMMAND LINE CONFIGURATION
  （证明 boost 的 `variables_map` 真的把值绑上去了），再对 127.0.0.1:1 发起真实
  `pqxx::connection`，被拒绝后返回 1。这一步把 boost → libpqxx → libpq → socket
  整条链路走通，且**不需要真实 PostgreSQL 服务端**（CI worker 上没有）。
- 安装产物：4 个 `mapconfig*.xml` + `COPYING` 存在且非空，且
  `mapconfig_for_cars.xml` 以 `<?xml` 开头（expat 要消费的就是这个声明）。

在无 bin/ 的情况下重跑（CI 的 L1e 破坏性检查）会返回非零：staging 那一步
`cp` 失败即 `exit 1`（同时把上一次的副本先 `rm -f` 掉，杜绝残留副本假通过）。

## 6. 已知限制

- 没有可用服务端，因此**配置解析 / 数据解析 / 建表**这些需要数据库的分支无法在
  CI 中执行；测试覆盖到“连上之前”的全部路径。
- `--conf` 的默认值 `/usr/share/osm2pgrouting/mapconfig.xml` 是上游写死的
  绝对路径，与本包实际安装位置 `share/osm2pgrouting/` 不一致。这是上游行为，
  未做改动；使用时请显式传 `-c`。
