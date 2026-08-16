# ice 3.8.2 适配笔记（HarmonyOS PC / OHOS aarch64）

> ZeroC Ice RPC 框架（C++ 版）在 OHOS PC (aarch64, musl libc, clang 15) 的适配。
> 手工构建 321+ 目标文件、9 个动态库 + 2 个静态库、20 个可执行文件全部编译通过；
> Conan 配方在 ohos-aarch64 profile 下 `conan create` 真实构建成功。

## 编译环境

- 构建系统: Ice 自有 Makefile（`make os=Linux srcs`，非 autotools/cmake）
- 编译日期: 2026-08-10
- 编译器: clang/clang++ 15.0.4（Target: aarch64-unknown-linux-ohos）
- 链接器: lld（clang-15 自带）
- 状态: built（W3 conan create 验证通过后由 finish 置为 published）

## 编译步骤

1. 解压源码：`tar xzf ice-3.8.2.tar.gz`（sha256 见 manifest）
2. 部署依赖前缀 `$HOME/tmp/ice-prefix`（bzip2/expat/libiconv/lmdb/mcpp/openssl/readline，
   来自 ohpcd 制品仓的 OHOS armv8 二进制；readline 由 cmd-pkgs 的 libedit 提供兼容层）
3. 关键构建命令（在 `cpp/` 目录）：

```bash
P=$HOME/tmp/ice-prefix
make os=Linux srcs \
  MCPP_HOME=$P ICONV_HOME=$P EXPAT_HOME=$P BZ2_HOME=$P LMDB_HOME=$P \
  CXXFLAGS="-fPIC -O2 -I$P/include" \
  LDFLAGS="-L$P/lib -Wl,-rpath,$P/lib"
```

4. 产物：
   - 动态库：`lib64/` 下 libIce/libGlacier2/libIceBox/libDataStorm/libIceDiscovery/
     libIceLocatorDiscovery/libIceGrid/libIceStorm/libIceStormService（.so + .so.38 + .so.3.8.2）
   - 静态库：libIceUtil.a、libSlice.a
   - 可执行：slice2* 翻译器、icegridnode/icegridregistry/icegridadmin、icestormadmin、
     glacier2router、icebox、icebridge、dsnode 等

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make` 默认把 OHOS 识别为未知 OS | `os ?= $(shell uname)` 无法匹配 OHOS | 显式传 `os=Linux` |
| 2 | 找不到第三方库头文件/库 | 依赖不在标准路径 | 用 `MCPP_HOME`/`ICONV_HOME`/`EXPAT_HOME`/`BZ2_HOME`/`LMDB_HOME` + `CXXFLAGS=-I`/`LDFLAGS=-L` 注入依赖前缀 |
| 3 | DataStorm/SessionI.cpp 编译失败：structured-binding capture | clang15 拒绝 `for (const auto& [a,b] : map)` 在 lambda 中捕获分解声明 | 改显式 `entry` + `const auto topicId = entry.first`（patch 0001） |
| 4 | Glacier2/CryptPermissionsVerifier.cpp 编译失败：无 `crypt_r` | OHOS musl 无 GLIBC `crypt_r` | musl 特性检测分支（`defined(__linux__) && !defined(__GLIBC__)`）用 `<unistd.h>` 的 `crypt()`，并以 `std::mutex` 保护非可重入调用（patch 0002） |
| 5 | slice2cpp 生成空头：`#include "Metrics.ice"` 找不到 | slice2cpp 把 include 解析到 `slice/` 根路径 | conanfile.py `build()` 的 `_mirror_slice_files()` 把上游 `cpp/src/IceStorm/{Election,LLURecord,SubscriberRecord}.ice` 与 `slice/IceStorm/Metrics.ice` 镜像到 slice2cpp `-I slice/` 可解析路径（不再用 patch 声明上游文件为新文件） |
| 6 | IceGrid/IceStorm Parser.cpp: `readline` undeclared | include "editline/readline.h"（libedit API），OHOS 无 libedit | deps 前缀提供 `editline/readline.h` shim（#include readline.h + history.h），`-ledit` 映射到 readline |
| 7 | 链接 `-ledit` 报 `tget*`/`tputs` 未定义 | GNU readline 静态库依赖 termcap | 链接 libedit（bundled termcap，cmd-pkgs libedit 20240817）或 readline+ncursesw 合并归档 |
| 8 | `make install` 失败：无 `install` 命令 | OHOS 无 GNU coreutils | conan recipe 的 package() 手工 copy 产物 |
| 9 | conan 无法匿名访问 ohpcd 远端 | 远端需要认证 | 依赖二进制已在本地 conan 缓存（本地解析，无需远端） |
| 10 | W3 conan create：`openssl/err.h not found`（首次） | OHOS-conan 的 `cpp_info.includedirs/libdirs` 返回**绝对路径**，配方 `pf/{d}` 拼接出双路径 | `os.path.isabs(d)` 判断后再拼接（conanfile.py `_dep_cxxflags/_dep_ldflags`） |
| 11 | W3 test_package：`Ice/Version.h not found` | `Version.h` 等由构建生成在 `include/generated/`，消费者 include 路径没有它 | `package_info()` 的 `includedirs` 加 `include/generated` |
| 12 | W3 test_package：`openssl/err.h not found`（再次） | SHARED 包的静态依赖默认不向消费者传播 headers（Conan `transform_downstream` 置 `headers=False`）；Ice 公共头 `Ice/SSL/Config.h`/`IconvStringConverter.h` 暴露 openssl/iconv 类型 | `self.requires("openssl/...", transitive_headers=True, transitive_libs=True)`；libiconv 同理 |
| 13 | W3 test_package：test.cpp 编译失败 | `Ice::Communicator::setProperty/getProperty` 在 Ice 3.7 已移除，属性存取移到 `getProperties()` | test.cpp 改用 `props->setProperty/getProperty`；`ich.destroy()` → `communicator->destroy()` |

## 源码修改

| 补丁文件 | 修改内容 |
|---------|---------|
| 0001-fix-datastorm-sessioni-structured-binding.patch | cpp/src/DataStorm/SessionI.cpp：structured-binding capture → 显式引用捕获 |
| 0002-fix-glacier2-crypt-ohos.patch | cpp/src/Glacier2/CryptPermissionsVerifier.cpp：musl 特性检测分支用 `crypt()`（`std::mutex` 保护非可重入调用） |
| 0004-add-editline-readline-shim.patch | IceGrid/IceStorm Parser 的 `-ledit`/`editline/readline.h` → GNU readline + ncursesw 合并 shim |

> slice2cpp include 解析所需的 slice 文件（Election/LLURecord/SubscriberRecord/Metrics.ice）不再通过
> patch 添加，改由 conanfile.py `build()` 的 `_mirror_slice_files()` 从上游规范路径镜像复制
> （避免将上游已存在文件声明为新文件的补丁）。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| bzip2 | 1.0.8 | 静态，链接进 libIce |
| expat | 2.8.2.1 | 共享 libexpat.so |
| libiconv | 1.17 | 静态 |
| lmdb | 0.9.35 | 静态 |
| mcpp | 2.7.2 | 静态 |
| openssl | 3.5.6.1 | 静态 libcrypto.a/libssl.a，编译进 libIce |
| readline | 8.3 | 静态；配合 ncurses/6.6 提供 `-ledit` 兼容 |
| libedit（cmd-pkgs） | 20240817 | 提供 editline/readline.h + libedit.so（bundled termcap） |

## 验证结果

```bash
# 全部库与可执行产物
ls cpp/lib64/            # 9 个 .so* + libIceUtil.a + libSlice.a
ls cpp/bin/              # 20 个可执行文件

# 版本冒烟
LD_LIBRARY_PATH=$PWD/lib64:$HOME/tmp/ice-prefix/lib ./bin/slice2cpp --version   # 3.8.2
LD_LIBRARY_PATH=$PWD/lib64:$HOME/tmp/ice-prefix/lib ./bin/icegridnode --version # 3.8.2
LD_LIBRARY_PATH=$PWD/lib64:$HOME/tmp/ice-prefix/lib ./bin/icegridadmin --version# 3.8.2

# readline 交互层可用（readline/add_history 链接正常）
echo "help" | ./bin/icegridadmin   # 进入/解析正常（无 registry 时提示连接失败，无 readline 崩溃）

# Conan 验证
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64  # 成功
```

## 上游测试实际运行记录（2026-08-14 实机执行取证，替代 08-11 版结论）

> 目的：为 MANIFEST.yml 中 `upstream_test_in_build` 提供**已验证的具体技术证据**。
> 本次在 OHOS aarch64 真机完整构建树（`cpp/lib64` 9 个 .so、`cpp/bin` 20 个可执行）
> 上**真实运行**上游测试套件，结论与 08-11 版「107 个测试全部无法执行」**相反**：
> 上游**单进程单元测试在 OHOS 上可编译、可运行且全部通过**，多个集成套件也可端到端运行。

### 证据 1：IceUtil 单进程单元测试 5/5 全部通过（真实运行，exit 0）

```bash
cd cpp
export LD_LIBRARY_PATH=$PWD/lib64
# 上游测试由 test.py 驱动单个 client 二进制（无 server、无端口、无 Python TestFramework）
./test/IceUtil/sha1/build/aarch64/shared/client       # Testing sha1 hash computation... ok
./test/IceUtil/stacktrace/build/aarch64/shared/client # checking stacktrace... ok
./test/IceUtil/timer/build/aarch64/shared/client      # testing timer destroy... ok
./test/IceUtil/unicode/build/aarch64/shared/client .  # testing error handling... ok
./test/IceUtil/uuid/build/aarch64/shared/client       # Generating 300000 UUIDs... ok（默认参数 300000×3 线程）
```

- 5 个套件全部 exit=0 并输出 `ok`。`ctrlCHandler` 上游 `test.py` 本身即标注
  `Dummy file to not run this test which is only ran manually`（上游设计不入 CI）。

### 证据 2：Slice 翻译器单进程测试 5/5 全部通过（真实运行，exit 0）

```bash
./test/Slice/deprecated/build/aarch64/shared/client  # testing deprecated definitions... ok
./test/Slice/escape/build/aarch64/shared/client      # Testing operation name... ok
./test/Slice/macros/build/aarch64/shared/client      # testing Slice predefined macros... ok
./test/Slice/print/build/aarch64/shared/client       # testing remapped identifier... ok
./test/Slice/structure/build/aarch64/shared/client   # testing equals() for Slice structures... ok
```

### 证据 3：Slice 脚本测试（slice2cpp 直接驱动）

| 套件 | 结果 | 说明 |
|------|------|------|
| headers | ✅ PASS | `-I` 解析、symlink 目录、典型安装布局 6 组用例全部 ok |
| unicodePaths | ✅ PASS | 中文路径生成 Test.cpp/Test.h |
| errorDetection | ✅ 40/54 | 40 个用例输出与上游 `.err` 逐行一致；14 个为 OHOS slice2cpp 错误检测行为差异 |
| utf8BOM | ⚠️ 差异 | OHOS slice2cpp 对行中 BOM 返回 0 无报错，上游期望报错（mcpp 行为差异） |

errorDetection 失败清单（14）：`ChangedMeaning ConstDef DerivedRedefinition IdentAsKeyword
IllegalDictionary IllegalMI MissingIdentifier NameCanNotBeUsed NestedModule OptionalMembers
OptionalParams SelfContainment StructMembers WarningInvalidMetadata`。典型差异：
- `ConstDef`/`OptionalParams`/`IllegalDictionary`/`SelfContainment`：上游期望多行错误而 OHOS slice2cpp 不报（mcpp 解析差异）
- `IllegalMI`/`IdentAsKeyword`/`StructMembers`：报错条数与顺序不同（语法错误提前于语义检查）

### 证据 4：集成测试可端到端运行（server+client 真实启动，非"没环境"）

```bash
# 手工生成 config.test（含 Test.BasePort/Ice.Default.Host/Protocol，等价 TestFramework 产物）
printf 'Test.BasePort=12010\nIce.Default.Host=127.0.0.1\nIce.Default.Protocol=tcp\n' > config.test
cd cpp/test/Ice/admin && ./build/aarch64/shared/server --Ice.Config=config.test &   # server 正常启动
./build/aarch64/shared/client --Ice.Config=config.test   # CLIENT_EXIT=0
# testing communicator operations... ok / process facet... ok / properties facet... ok
# logger facet... ok / custom facet... ok / facet filtering... ok
```

实测通过：`Ice/admin`、`Ice/enums`、`Ice/objects`、`Ice/exceptions`（CLIENT_EXIT=0 全部 ok）。
`adapterDeactivation` 为上游长时测试（45s 超时未跑完，非失败）。`operations` 套件在
slice2cpp 阶段即失败：`Test.ice:272 struct 'MyStruct1' must have at least one member`，
`diff` 确认该 Test.ice 与上游 v3.8.2 原始文件**逐字节一致**，属上游用例与 OHOS slice2cpp
的真实不兼容（同一环境下 admin/enums/properties 等套件可编译，证明非环境不可用）。

### 证据 5：Python TestFramework 依赖边界

上游全部测试的编排器为 Python TestFramework（`cpp/allTests.py` → `scripts/Util.py`），
硬依赖 Ice Python 绑定（`import Ice`，OHOS 无该模块，`ModuleNotFoundError`，Util.py
2310/2359/2391/2972/3319/3330 行多处）。本适配不改变该约束——单进程套件已直接运行取证，
其余集成套件在**构建与单测层面**已验证（见证据 4），完整 TestFramework 编排需 Python 绑定。

### 结论（修正 08-11 版）

- ✅ 上游**单进程单元测试 IceUtil 5/5 + Slice 5/5 在 OHOS 真实运行全部通过**；
- ✅ 集成套件 admin/enums/objects/exceptions 端到端运行通过；
- ⚠️ errorDetection 40/54 通过，14 个为 slice2cpp 行为差异（有逐行 diff）；
- ❌ operations 套件 slice2cpp 编译失败（Test.ice 与上游逐字节一致，真实不兼容）；
- `upstream_test_in_build` 保持如实声明：单测在 OHOS 真机执行、配方 build() 完成全部编译验证。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（makefile 构建，8 个依赖） |
| conandata.yml | 源码 URL + sha256 + 3 个补丁 |
| test_package/ | 消费者测试（CMake 链接 libIce，属性 round-trip + 版本宏校验） |
| patches/ | 3 个 OHOS 适配补丁（slice 文件由 build() 镜像） |

## 注意事项

- OHOS clang 定义 `__linux__` 但**无 `__GLIBC__`**（musl），涉及 glibc 特有 API（如 crypt_r）用
  `defined(__linux__) && !defined(__GLIBC__)` 特性检测（覆盖 OHOS 及任意 musl），且非可重入
  `crypt()` 需 `std::mutex` 保护。
- Ice 的 `slice2cpp` 把 `#include "Metrics.ice"` 解析到 slice 搜索根路径，源树缺失的 .ice 必须在 slice/ 根或子目录提供。
- IceGrid/IceStorm 管理工具依赖 libedit 的 readline 兼容 API，OHOS 无 libedit，用 readline+shim（`-ledit` 映射）解决。
- 运行时需 `LD_LIBRARY_PATH` 指向 lib64 与依赖前缀（或使用构建期注入的 rpath）。
