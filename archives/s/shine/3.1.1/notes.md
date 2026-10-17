# shine 3.1.1 适配笔记

## 编译环境
- 构建系统: autotools（GitHub archive 无 configure，需 autoreconf 自举）
- 编译日期: 2026-09-17
- 编译器: clang/clang++（/data/service/hnp/bin/clang 15.0.4，OHOS armv8 aarch64）
- 状态: published（conan-verify 全部门禁通过）

## 编译步骤

本地探索性编译（worktree scripts + conan tool_requires 二进制）：
1. `tar -xzf shine-3.1.1.tar.gz`（官方 tag 3.1.1，SHA-256 565b8786...49e，git commit 97f188ef）
2. `autoreconf -fi`（需要 automake/1.18 + libtool/2.5.4，以 conan tool_requires 提供，
   修复 aclocal PERL5LIB 与 libtool m4 搜索路径后成功）
3. `./configure --prefix=$DEFAULT_PREFIX`：首错 E007（config.guess 不认识 HarmonyOS），
   按知识条目方案补丁 config.guess/config.sub 后通过；E114（config.status 的
   `mktemp -d` 临时目录在 HMDFS 上为 drwx--S--- 不可写），按知识条目把 ac_tmp 指向
   预建固定目录后通过
4. `make -j1` 通过：libshine.so.3.0.1 + libshine.a + shineenc CLI
5. `make check`：上游无测试目标（Nothing to be done for 'check'）
6. `make install DESTDIR=$TEST_PREFIX`：staging 含 lib/include/bin/pkgconfig 完整
7. conan create（ohos-aarch64 profile）：G1-G4/L2/L4/L5 全部 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方 tarball 无 configure | GitHub archive 只含 configure.ac/Makefile.am | 配方 build() 中 `autoreconf -fi` 自举；tool_requires automake/1.18 + libtool/2.5.4 |
| 2 | config.guess 无法识别 HarmonyOS（cannot guess build type） | E007 | 本地探索用仓库 patch-autotools-ohos.pl 补丁 config.guess/config.sub；配方用 `--build/--host=aarch64-unknown-linux-ohos` 三元组（config.sub 原生支持 *-linux-ohos，同 argp-standalone 先例） |
| 3 | config.status `mktemp -d` 临时目录 Permission denied | E114，HMDFS 上 077 umask 目录 drwx--S--- 不可写 | 本地探索：sed 改写 ac_tmp 指向预建固定目录；配方：build() 中把生成的 configure 里 `umask 077` 改为 `umask 022`（同 argp-standalone 先例） |
| 4 | 配方 G2 首错 layer3.h not found | basic_layout 分离 build 目录，Makefile.am 的 `-Isrc/lib` 相对路径失效 | 配方 layout() 设 `folders.source="."` + `folders.build="."`（in-source 构建） |
| 5 | test_package test_shine 段错误/断言失败 | ① 误把 44100Hz/8kbit 当 MPEG-I 有效（实际 MPEG-I 最低 32kbit）；② `shine_encode_buffer` 第二参数应为每声道指针数组，误传 `&buf` 强转 | 修正 test.c：改用 32kbit 断言 + 校验 8kbit 拒绝；用 `int16_t *chans[1]={buf}` 调用 |
| 6 | 本机无 automake/aclocal | 构建主机只有 autoconf 套件 | conan 制品仓 tool_requires automake/1.18、libtool/2.5.4（与 argp-standalone 同方案） |

## 源码修改

无（未修改上游源码，无 patches）。

## 依赖版本

- 运行时依赖: 无（仅 libc/libm）
- 构建依赖: automake/1.18（tool_requires）、libtool/2.5.4（tool_requires）

## 上游测试枚举与双口径台账（R51）

### 枚举方法
官方 tag 3.1.1 tarball 全文件清单逐项核对：C 侧无任何测试源文件/测试目标；
JS/WASM 绑定侧存在 `js/test/` 目录。autotools 侧 `make check` 无注册目标
（Makefile.am 无 TESTS/check_PROGRAMS，configure.ac 无 AC_CONFIG_TESTDIR）。

### 测试入口台账（全目录口径）

| 条目 | 类型 | 是否独立上游用例 | 能否运行 | 结果/原因 |
|------|------|-----------------|---------|-----------|
| Makefile.am TESTS/check_PROGRAMS | 构建目标 | 否（无此目标） | — | 上游 C 库无测试注册；`make check` 输出 Nothing to be done for 'check' |
| src/bin、src/lib（*.c/*.h） | 库/工具源码 | 否 | — | 生产代码，非测试 |
| js/test/node/encode.coffee | 用户测试源（node） | **是** | 否 | node 运行时崩溃（见下） |
| js/test/node/rounds.coffee | 用户测试源（node） | **是** | 否 | node 运行时崩溃（见下） |
| js/test/browser/encode.js + index.html | 用户测试源（browser） | 是（浏览器端） | 否 | 需浏览器 + node，node 不可用 |
| js/test/lib/rounds.js | 测试辅助库 | 否（helper） | — | 供 rounds 测试复用的辅助模块 |
| js/test/lib/encode.wav | 测试 fixture | 否（数据文件） | — | 输入样例数据 |
| js/test/node/package.json | 测试清单 | 否（清单） | — | scripts.test 声明 `coffee ./encode.coffee && coffee ./rounds.coffee`（2 个独立入口） |
| js/dist/libshine.js | 编译产物（emscripten） | 否 | — | 非测试 |

### 双口径统计

- `source_declared_total` = 2（node 侧 package.json scripts.test 声明的
  encode.coffee + rounds.coffee 两个独立用户测试入口；browser 侧为浏览器手动测试入口，单独列出不计入自动执行口径）
- `configured_executable_total` = 0（当前 OHOS 配置实际实例化/注册的可执行用例数：C 侧 0；JS 侧依赖的 node 运行时在本机启动即崩溃，无法实例化）
- `executed_passed_total` = 0
- 失败数 = 0
- 未运行/未实例化 = 2（全部上游独立入口）

**全量通过率：0/2 = 0%**（另列当前配置可执行集合：0/0 无实例化项）。
全部未运行入口均因同一硬阻塞：node 运行时在 OHOS 平台不可用。

### 未运行入口逐项证据（硬阻塞）

- 入口：js/test/node/encode.coffee、js/test/node/rounds.coffee（及 browser/encode.js）
- 命令：`cd $HOME/tmp/builds/shine-3.1.1.orig/js/test/node && npm install && npm test`（package.json 声明）
- cwd：`/storage/Users/currentUser/tmp/builds/shine-3.1.1.orig/js/test/node`
- 退出码：node 139（Signal 11）/ V8 Fatal error
- 首条错误：`node -e 'console.log(1)'` 启动即崩溃：
  `# Fatal error in , line 0 / # Check failed: 12 == (*__errno_location()).`（npm、coffee 同样崩溃）
- 绝对日志：
  - `/storage/Users/currentUser/tmp/shine-tests/logs/node-probe.log`（node 探针崩溃）
  - `/storage/Users/currentUser/tmp/shine-tests/logs/npm-install.log`（npm install 崩溃）
- 具体缺失条件：node v24.13.0（/data/service/hnp/bin/node）与 OHOS musl 运行时
  的 errno 定位不兼容，进程无法启动；coffee-script 1.6.3 亦需 node 运行
- 阻塞归属：平台/运行时（node 二进制本身在此环境不可运行，非 shine 代码缺陷；
  与 C 库适配无关——这些入口测试的是 emscripten WASM 绑定而非本配方交付的
  libshine C 库 + shineenc CLI）
- 恢复条件：设备安装可正常运行的 node 运行时后，重新 `npm install && npm test`
  即可运行两个入口；或由分析端在其他有 node 的机器运行 WASM 绑定测试

## 验证结果

```bash
# conan-verify（G1-G4 + L2/L4/L5）—— 全部 PASS
ohc-run.py conan-verify shine 3.1.1
# test_package 消费者测试通过（10 断言 + 输出校验）
conan create ... --build=missing  # G2 PASS，test_shine 通过
# 本地冒烟
LD_LIBRARY_PATH=$TEST_PREFIX/storage/Users/currentUser/usr/local/lib \
  ./.libs/shineenc --help   # 输出 usage，正常
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/s/shine/3.1.1/conanfile.py | Conan 配方（autoreconf 自举 + E007/E114 处理 + in-source 构建） |
| archives/s/shine/3.1.1/conandata.yml | 官方源 URL + SHA-256 565b8786...49e |
| archives/s/shine/3.1.1/test_package/ | 消费者测试（test.c 调公开 API 编码正弦波并校验 MP3 帧同步字） |
| archives/s/shine/commands.json | CLI 声明（shineenc，R38） |
| reports/conan-verify-report.md | 门禁验证报告 |

## 知识候选台账与七轴查重（路径 B 判定）

### 候选总览

| 候选 | 真实错误 | 根因 | 修复 | 验证 | 四范围查重结果 |
|------|---------|------|------|------|---------------|
| K1 config.guess 不识 HarmonyOS | `configure: error: cannot guess build type` | E007：config.guess 无 HarmonyOS 分支 | 本地探索用 patch-autotools-ohos.pl；配方用显式双三元组 `--build/--host=aarch64-unknown-linux-ohos`（config.sub 原生支持） | conan-verify G2 PASS | 正式知识 doc/E007.md 精确命中 → **exact_duplicate，复用** |
| K2 HMDFS mktemp 077 临时目录 | `config.status: can't create ./confXXXXXX/subs1.awk: Permission denied` | E114：HMDFS 上 umask 077+mktemp 建出 drwx--S--- 不可写 | build() 中把生成的 configure 内 `umask 077`→`umask 022` | conan-verify G2 PASS | 正式知识 doc/E114.md 精确命中 → **exact_duplicate，复用** |
| K3 设备缺 automake/aclocal/libtoolize | `autoreconf: error: aclocal failed`；conan 包 automake 缺 `Automake::Config`（PERL5LIB） | 构建主机仅 autoconf 套件；conan automake 二进制包 perl @INC 不含包内模块 | tool_requires automake/1.18 + libtool/2.5.4（配方层）；本地探索用 PERL5LIB 指向包 share | conan-verify G2 PASS（tool_requires 生效） | 正式知识 E116（compile-automake-from-source）部分覆盖 perl @INC；本候选新增差异 = 配方层 tool_requires 声明解决（argp-standalone 同方案，已入仓先例） → **partial，既有先例，仅登记观察** |
| K4 conan libtool 包 libtoolize pkgauxdir 损坏 | `libtoolize: error: $pkgauxdir is not a directory: '//share/libtool/build-aux'` | conan libtool 包前缀计算为根目录 | 本地探索用系统 libtoolize 2.4.7 绕开；配方仍用 tool_requires（CI 环境自带） | 本地探索 autoreconf 成功 | 正式知识 E514（libtoolize aux-dir 启发式）触发面不同 → **trigger_overlap，登记观察，无新增草稿** |
| K5 autotools Makefile.am 相对 include 路径需 in-source 构建 | `src/bin/main.c:24:10: fatal error: 'layer3.h' file not found` | basic_layout 分离 build 目录，Makefile.am `-Isrc/lib` 相对源码根的路径在 out-of-source 下失效 | 配方 layout() 设 `folders.source="."` + `folders.build="."`（in-source） | conan-verify G2 PASS（修复后 layer3.h 找到） | 正式知识 E340/E392/E470 均为 cargo/cmake/raw-makefile 场景，autotools+Makefile.am 相对 -I 未见覆盖 → **combination_novelty，路径 B 新建草稿** |
| K6 test_package generators 属性与 generate() 重复实例化 | `ConanException: CMakeDeps is declared in the generators attribute, but was instantiated in the generate() method too` | Conan 2 不允许同生成器两处声明 | test_package 改 a52dec 模式：`generators="VirtualRunEnv"` + generate() 内显式 CMakeDeps/CMakeToolchain | conan-verify G2 PASS | 正式知识索引未见该签名；E447 为 SDL vendored Find 模块，不同触发面 → **solution_overlap(仅概念)/combination_novelty，路径 B 新建草稿** |
| K7 L0d stub_test_method（test() 无 self.run） | CI L0 gate: `stub_test_method` | CI 要求 test() 内含显式 `self.run` 实际执行逻辑 | test() 改 `self.run("./test_shine", env="conanrun")` | W3 L0 PASS | 正式知识 E472（sign-elf-and-sdl-dummy-headless-test）含 self.run for L0d 门禁 → **trigger_overlap，复用 E472 要点，无新增差异** |
| K8 node 运行时在 OHOS 启动即崩溃 | `node -e 'console.log(1)'` → `Fatal error: Check failed: 12 == (*__errno_location())`，Signal 11 | OHOS musl 与 node v24 的 errno 定位不兼容 | 无本地修复（平台/运行时阻塞）；JS/WASM 绑定测试如实记为硬阻塞 | node-probe.log 证据（exit 139/Signal 11） | 正式知识 E029 为 bash malloc，不同 → **boundary_novelty，登记候选观察（非适配知识，属平台阻塞证据）** |

### 七轴查重汇总

| 候选 | exact | causal | trigger_overlap | solution_overlap | combination_novelty | boundary_novelty | test_migration_novelty | 判定 |
|------|-------|--------|-----------------|------------------|---------------------|------------------|------------------------|------|
| K1 | ✅ E007 | — | — | — | — | — | — | reuse_existing |
| K2 | ✅ E114 | — | — | — | — | — | — | reuse_existing |
| K3 | ❌ | 部分(E116) | ✅ | ✅ | — | — | — | path_a_no_knowledge（先例已入仓，仅登记） |
| K4 | ❌ | ❌ | ✅(E514 触发面不同) | 部分 | — | — | — | path_a_no_knowledge（观察） |
| K5 | ❌ | ❌ | ❌ | ❌ | **✅ 新建** | — | — | **new_draft（路径 B）** |
| K6 | ❌ | ❌ | ❌ | 部分(概念) | **✅ 新建** | — | — | **new_draft（路径 B）** |
| K7 | ❌ | ❌ | ✅(E472) | ✅ | — | — | — | path_a_no_knowledge（复用 E472） |
| K8 | ❌ | ❌ | ❌ | ❌ | — | ✅(平台阻塞) | — | path_a_no_knowledge（观察，非知识草稿） |

### 关系字段与决定

- `reuse_existing`: K1(E007)、K2(E114)、K7(E472)
- `new_draft`: **K5（autotools in-source build 相对 include 路径）、K6（test_package 生成器两处声明）** → 建立同 stem 的 .md/.kv 草稿对
- `path_a_no_knowledge`: K3、K4、K8（真实观察，跨库复用价值低或已有先例，不建草稿）
- 关系：K5 与 K6 无直接因果；K5 `similar_to` E392（raw makefile build_folder 概念）、E340（cargo basic_layout）；K6 `similar_to` E472（test_package 结构）；K8 `caused_by` 平台 node 运行时，`prerequisite_of` 未来任何含 JS 绑定测试的 OHOS 包
- 适用边界/反例：K5 仅适用于 Makefile.am/CMake 相对源码根 include 路径的 autotools 包（纯库 + VPATH 安全项目不受影响）；K6 仅 Conan 2（Conan 1 无此限制）

- shine 是库 + CLI 双产物：libshine（lib + 头 + pkg-config）与 shineenc 可执行。
- 上游无 C 侧测试；JS/WASM 绑定测试依赖 node 运行时（本机不可用，硬阻塞已记录）。
---

**编译结束**: 2026-09-17 20:58
**最终状态**: built
