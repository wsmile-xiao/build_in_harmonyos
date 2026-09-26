# presage 0.9.1 适配笔记

## 编译环境
- 构建系统: autotools（tarball 自带 configure/Makefile.in，全程无需 autoreconf）
- 编译日期: 2026-09-24
- 编译器: clang/clang++ 15.0.4（/data/service/hnp/bin，设备无 gcc/g++）
- 状态: built

## 编译步骤

原生构建（SKILL Step 2，全链 rc=0）：

```bash
export CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++
export CFLAGS="-O3 -pipe -DNDEBUG" CXXFLAGS="-O3 -pipe -DNDEBUG"
export CPPFLAGS="-I<sqlite3|tinyxml|ncurses|cppunit conan 包>/include（四依赖绝对路径）"
export LDFLAGS="-L<shim> -L<四依赖 conan 包>/lib"
export PATH="$SHIM:$PATH"          # shim 内含 cppunit-config 与 libcurses.a → libncursesw.a
./configure --prefix=$DEFAULT_PREFIX --disable-python-binding
make -j2 && make install DESTDIR=$TEST_PREFIX
HOME=$TASK_DIR/test-home make check    # 上游测试全程沙箱 HOME
```

conan 面（conanfile.py）：generate() 写两个 shim 并注入 PATH/LIBRARY_PATH/extra_ldflags，
并把 sqlite3 依赖的 bin/ prepend 进 PATH（sqlite3 **CLI** 面，见问题表 #14——上游测试
`system("sqlite3 …")` 直接消费该程序，设备 harmonybrew 版掩盖、CI worker 无此程序），
configure（仅 --disable-python-binding——conan 注入的 shared 四旗已被 generate() 滤除=零开关原生同形 .so+.a，见问题表 #13；CFLAGS 含 -O3 -pipe -DNDEBUG）
→ make -j1 → **make check（build() 内跑上游测试面，L1）** → package（COPYING→licenses/ + install）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `cannot guess build type; you must specify one` | config.guess 为 2012-02-10 版，`UNAME_SYSTEM` case 不识别 `uname -s` = HarmonyOS（config.sub 2012-04-18 版已认 aarch64-unknown-linux-gnu，无需改） | 补丁 0001：把 `aarch64:HarmonyOS` 并入既有 `aarch64:Linux:*:*` 分支（+1/-1） |
| 2 | config.status 报 `can't create ./confXXXXXX/subs1.awk: Permission denied` → `could not setup config files machinery` | 知识 E011 族：`(umask 077 && mktemp -d ./confXXXXXX)` 产出 0700 临时目录，HMDFS uid 映射（属主 20001006 ≠ 进程 uid）后当前进程不可写；且 GNU mktemp 恒 0700、单纯放宽 umask 对其无效（DRAFT-6507） | 补丁 0002：禁用 mktemp 分支强制走 `tmp=./conf$$-$RANDOM` mkdir fallback（HMDFS 落盘组可写，普通 fs 下 owner=creator）+ 两处 umask 077→002（toybox mktemp/回退路径同步放宽）；设备与 worker 双实现通吃 |
| 3 | `make check` 中 coreTestRunner 与 ProfileManagerTest **SIGSEGV（Signal 11）**，崩溃点 14/17 点漂移（非确定性表象） | 上游 bug：`ProfileManager::get_user_home_dir()` 写成 `if (!my_passwd) { result = my_passwd->pw_dir; }`（注释本意是"拿到 passwd 才读 pw_dir"）。OHOS 无 passwd 库 → `getpwuid()` 返回 NULL → 空指针解引用；常规 Linux 因 getpwuid 命中走 else 分支而长期掩盖。gdb 被 SELinux 拒（ptrace denied），用「逐 suite 二分驱动 + SIGSEGV handler backtrace + addr2line -O0 重建」定位到 profileManager.cpp:235 | 补丁 0003：删 `!` 恢复注释本意（`if (my_passwd)`），NULL 时正确落到 $HOME 分支 |
| 4 | **94 个 CPPUNIT_TEST 存在假绿面**：conan cppunit 包无 `cppunit-config` 可执行 → `AM_PATH_CPPUNIT`（m4/cppunit.m4 只认该程序名）判 not found → HAVE_CPPUNIT 空 → testRunner 系列不构建、全部上游单测静默跳过，`make check` 仍绿 | m4 宏探测机制与 conan 包交付物形态不匹配（taglib FindCppUnit 同族、本例为 m4 形态） | conanfile generate() 生成 `conan-shims/cppunit-config`（应答 --cflags/--libs/--version）并 prepend PATH，HAVE_CPPUNIT 正常置位，7 个 runner 全构建全跑 |
| 5 | `presage_demo`（ncurses 演示）被上游可选分支静默跳过 | `AC_CHECK_LIB([curses])` 链接 `-lcurses` 基名，conan ncurses 6.6 只交付 `libncursesw.a` 等 *w 名 | generate() 内 `libcurses.a → libncursesw.a` symlink 进 shim 目录（LIBRARY_PATH + extra_ldflags 双通道注入，clang LIBRARY_PATH 已探针验证），4 个主工具 + presage_demo 全部落地 |
| 6 | configure 阶段 `C++ compiler cannot create executables`（config.log 实证 `g++: inaccessible or not found`） | autoconf `AC_PROG_CXX` 候选表（g++ c++ gpp aCC CC cxx cc++ cl.exe FCC KCC RCC xlC_r xlC）**不含 clang++**，14 候选全落空后回退默认 g++，而设备只有 clang | 原生构建显式 `CC=clang CXX=clang++` 绝对路径；conan 面由 profile `tools.build:compiler_executables` 提供，配方无需额外处理 |
| 7 | （W0-③ 裁量登记，bcp #7 同格式）平台判据 grep 唯一命中：`apps/gtk/gprompter/scintilla/lexers/LexPascal.cxx:94` 含 `asm` 字样 | **注释行**（Scintilla Pascal 关键字表里的 asm 一词，非代码）+ **死块**（该文件在 apps/gtk/gprompter 捆绑 scintilla 内，apps/gtk 由 configure 按 gtk+-2.0 探测条件构建，OHOS 无 gtk2 ⇒ 不进构建面）——注释+死块双重不触达，按 bcp 先例裁量收窄、不打补丁，真实原生构建即兜底探针（已全量编译通过） | 登记不修。**复发条件：若未来启用 gtk app 构建（引入 gtk2 dev 依赖）、或该 TU 进入 src/ 构建面 → 必须重核（补一轮编译探针/平台判据复扫）** |
| 8 | 采信轮首红（G2）：`AttributeError: 'PresageConan' object has no attribute 'buildfolder'`（generate() line103） | Conan1→2 属性名迁移坑：`self.buildfolder` 是 Conan1 命名，Conan2 正确属性为 **`self.build_folder`**（带下划线，conan/internal/model/conan_file.py:307）；同族空值坑=generate() 阶段 `self.folders.*` 可能未完全解析（integrit 的 `folders.package` 空值同族）。G1 静态完整性查不出这类属性名错误、只在真跑 generate() 时炸 | 一行修为 `self.build_folder or os.getcwd()`（仓内防御同款）+ 全文件核属性作用域：generate() 内不用 `self.package_folder`（本配方 cu./nc.`package_folder` 是**依赖对象**全解析属性、不受此坑影响），`self.source_folder`/`self.package_folder` 仅出现在 package()/test() 合法作用域；py_compile + 采信轮二轮验证 |
| 9 | 采信轮 R2 红（C++ 代差族·本包第 1 红）：`error: ISO C++17 does not allow dynamic exception specifications [-Wdynamic-exception-spec]` ×20 → `autotools.make Error 2` | **flag 差分读数**：原生构建全量日志 `grep -c -- '-std='` = **0**（clang15 默认 gnu++14，`-dM -E` 实证 `__cplusplus 201402L`）vs conan 构建行注入 **`-std=c++17`**（profile `compiler.cppstd=17`）→ 上游 2019 代码 `throw (PresageException)` 动态异常规格在17档被 clang 判 error。探针：裸 `-std=c++17` rc=1/stderr 376B；`-std=c++17 -Wno-dynamic-exception-spec` rc=0/stderr 0B；真实 5 个核心 TU（presage.cpp/profileManager.cpp/selector.cpp/smoothedNgramPredictor.cpp/contextTracker.cpp）带豁免全 rc=0（无其它 C++17 移除特性残留） | **A 案（编排方倾向+探针实证）**：`tc.extra_cxxflags.append("-Wno-dynamic-exception-spec")`（必须 extra_cxflags 实例列表、非 property cxxflags——xplc 实测坑），保留 cppstd=17 settings 与 package_id 语义不动。**三案边界**：bcp build2=消费面（test_package std 降档）；本单 A=**主库编译面诊断豁免**（xplc `-Wno-c++11-narrowing` 同手法）；B=`tc.cppstd="-std=gnu++14"` 原生同形钉档（探针亦可行但属降档、settings 标签与实编不符，已撤销） |
| 10 | 采信轮 R3 红（链接期族·本包第 1 红）：`ld.lld: undefined symbol: __cxa_rethrow / std::terminate() / typeinfo for std::length_error` → `bindings/c presage_c_demo` 链接失败（`make check` 期） | **shared/static 分叉差分读数（四方证据）**：①conan 树 `libpresage.so` 计数=0；②configure 收到 `--disable-shared`×2 + `--enable-static`×2；③关 shared 的就是本配方（原 line61 模板默认 `shared:False` + line94-95 R26 块注旗）；④libtool `.la` 分叉实证——conan `dlname='' library_names='' old_library='libpresage.a'`（纯静态）vs 原生 `dlname='libpresage.so.1' library_names='…so.1.1.1…'`（TP 安装树 `libpresage.so.1.1.1`=1927744B 在位）。原生链接行 `--tag=CC … .libs/libpresage.so -Wl,-rpath` （链接期不解 C++ 符号、libc++ 走 NEEDED 运行期）；conan 落 `.libs/libpresage.a` → CC 驱动静态链把全部 libc++ 符号顶到链接期 | **定案=共享选择面（原生对齐）**：`default_options shared: False→True` → R26 块不再注旗 → configure 与原生完全同形（libtool 默认 .so+.a 双产物、demo 链 .so）。**不采用**「加 -lc++」掩盖静态化（编排方裁定：.so 缺失影响 package 交付面与 L4/L5 读数；-lc++ 方案已探针证可行但归档为非默认变体 `shared=False` 的预案：原生 .o+.a+conan 同形依赖集+`-lc++` 链接 rc=0/stderr 0B，不带则 rc=1 复现原错） |
| 11 | 采信轮 R4 红（test_package 资源面族·本包第 1 红）：`test() line49 shutil.copyfile → FileNotFoundError: …/test_package/share/presage/database_en.db` | **根目录误用**：test_package 语境里 `self.package_folder` 是**测试包自身**的 package 目录（cmake_layout 把 CMAKE_INSTALL_PREFIX 指到 `test_package/` 实证），不是被测包缓存目录；`@PKGDIR@` 配置生成同源共错。取证三问：A) `find test_package -name '*.db'` 空=设计即无 fixture（运行时从被测包树取）；B) 地面真相=W0 TP 安装树 `share/presage/` 含 database_en/es/it.db（上游 make install 必收件，发货面无缺）；C) 错在 src 根（db_src 用了测试包根） | `tested = self.dependencies["presage"]`，`pkg` 与 `db_src` 均改取 `tested.package_folder`；`db_dst=self.build_folder/consumer_lm.db` 父目录=build 目录本就存在（无需 mkdir）；发货面按上游 install 真相核过、package() 无需补收 |
| 12 | R4 并发发现：**conan 面 93 单测假绿实锤**（E694 草稿预言形态）——`checking for cppunit-config... no` → `WARNING: CppUnit not found` → runner 全不构建 → 7 处 `All 0 tests passed` + 仅 `PASS: integration.sh`，G2 差点以零单测通过 | 双因：①shim 文件与 PATH 注入**都在**（conanbuild.sh 确 source `conanbuildenv_presage_shims.sh`、脚本内 `export PATH=…/conan-shims:…` 逐字在档），但 `cppunit-config` 落盘 **660 无执行位** → AC_PATH_PROG 按可执行性判 no；②执行位丢失根因=**conan `tools.files.chmod` API 用错**：签名 `chmod(conanfile, path, read, write, execute)` 第三参是布尔不是 POSIX mode，`chmod(self, path, 0o755)` 被解析成 `read=0o755`（真值）→ 只动读位、从不给执行位 | 改 `os.chmod(cfg_path, 0o755)`（真 syscall）+ 移除误导性 import；R5 判据=`checking for Cppunit - version >= 1.9.6... 1.15.1` 且 7 runner `OK (N tests)` 求和=93（不再是 All 0） |
| 13 | R4 并发发现：configure 实收 `--enable-shared --disable-static`（与「零 shared 开关」定案不符）、`ar cru .libs/libpresage.a`=0 静态未产 | conan `internal/model/pkg_type.py`：`package_type=library`（抽象型）+ shared 选项 → **`deduce_from_options()` 按选项值推断有效类型**——shared=True 推断 SHARED → `AutotoolsToolchain._default_configure_shared_flags` 注入该对旗。**shared 修复闭环读数**（共享面已生效证据）：R4 日志 `libpresage.so` 计数 13、`--tag=CXX … -Wl,-soname -Wl,libpresage.so.1 -o .libs/libpresage.so.1.1.1`、demo 链接 `--tag=CXX … -rpath //lib`、symlink `.so.1/.so` 生成行、test_presage 消费链接 `Built target` 全通 | generate() 顶部对 `tc.configure_args` **滤除四类 shared 旗**（enable/disable × shared/static）使 configure 回到零开关=原生同形（libtool 默认 .so+.a 双产物）；**原 R26 模板块整块移除**（否则 shared=False 变体把静态旗加回、与唯一权威冲突；R26 本义=系统同名库，本包不适用，deps 静态由各自包 option 决定）。shared 选项保留、仅作用于有效 package_type（消费侧链接偏好）与 package_id |
| 14 | CI 红（build 57994 / buildbot build 66615，conan-build-test `results=2`）：`make check` 中 SqliteDatabaseConnectorTest **3/14 断言失败**、首错 `sh: sqlite3: inaccessible or not found` → `FAIL: dbconnectorTestRunner` → `Error in build() method, line 191 (autotools.make target="check")`。机器人自分类「编译失败」为**误标**（实际是测试期 CLI 缺失，编译/链接全绿） | 上游 `assertDatabaseDumpEqualsBenchmark` 用 `system("sqlite3 <db> \".dump\" > dump")` 调 **sqlite3 CLI**（sqliteDatabaseConnectorTest.cpp:437）并断言 `command_exit_value == 0`（:438）；设备 PATH 里唯一 sqlite3 是 `~/.harmonybrew/bin/sqlite3`（3.53.0）→ 本地恒绿（device-facts §一.4 掩盖族），CI worker PATH 无 sqlite3 → command not found → testInsertNgram/testUpdateNgram/testIncrementNgramCount 三条红、其后测试目录被 make check 中止 | **本地 CI 同形复现**（去 harmonybrew 的 PATH，`command -v sqlite3` 为空）逐字复现同一签名后修复：generate() 把依赖 `sqlite3/3.53.4` 的 `bin/`（自带 sqlite3 3.53.4 CLI，实测可执行）prepend 进 PATH（与 cppunit-config shim 同一 conanbuildenv 脚本通道）→ 设备与 worker 解析同一二进制；判据=CI 同形 PATH 下 `make check` 全目录跑完、dbconnectorTestRunner `OK (14 tests)` |

## 源码修改

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001-config.guess.patch | config.guess | `aarch64:Linux:*:*)` → `aarch64:Linux:*:* \| aarch64:HarmonyOS:*:*)`（+1/-1，platform_only） |
| 0002-configure.patch | configure | mktemp 分支 `(umask 077 && mktemp -d …)` → `(umask 002 && false)` 强制走 mkdir fallback；回退 `(umask 077 && mkdir "$tmp")` → `umask 002`（+2/-2，platform_only） |
| 0003-src-lib-core-profileManager.cpp.patch | src/lib/core/profileManager.cpp | `if (!my_passwd)` → `if (my_passwd)`（+1/-1，上游逻辑 bug，platform_only） |

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| sqlite3 | 3.53.4 | ngram 数据库（硬依赖，configure AC_MSG_ERROR 缺失即停） |
| tinyxml | 2.6.2 | profile XML 解析（系统版探测命中则用系统版，未命中回退内置，本例 conan 版命中） |
| ncurses | 6.6 | presage_demo 演示（可选面，缺省跳过；本例 shim 后构建） |
| cppunit | 1.15.1 | 单元测试框架（仅 build() 的 make check 消费，visible=False 不传播） |

均静态（R26 默认 shared=False）；`conan install --build=missing` 双 profile 绝对路径实证 rc=0。

## 验证结果

```bash
# 原生全链（沙箱 HOME 下 make check）
rc.configure=0 rc.make=0 rc.install=0 rc.check=0

# make check：automake TESTS 单元 9/9 全 PASS（0 FAIL / 0 SKIP）
#   testRunner(0 注册) + coreTestRunner(31) + tokenizerTestRunner(16)
#   + contextTrackerTestRunner(11) + predictorsTestRunner(11)
#   + newPredictorsTestRunner(7) + dbconnectorTestRunner(14) + toolsTestRunner(3)
#   + integration.sh(KSR=81.6364)
# 计数四口径（不混用）：
#   源码文本宏 94（任务卡口径，含 1 个上游注释停用 testSanitizeString）
#   有效注册宏 93 == 框架实跑 93（逐 runner OK 行求和）
#   断言宏静态清点 292（91+188+3+7+3，cppunit 成功路径不打印运行期断言数）
#   integration.sh 为独立 shell 单元（语料 = 随包 COPYING，非 fixture 捏造）

# 消费者（test_package 等价探针，TP 阶段树）
new_with_config rc=0 / predict rc=0 count=6（the,and,of,to,a,i）
config SUGGESTIONS=6 / learn rc=0
```

## 注意事项

- **计数口径**：N（上游总数）= 94（源码文本宏，审方独立清点同口径）；N′（实际运行）= 93；差额 1 = `databaseConnectorTest.h:43,165` 上游注释停用的 `testSanitizeString`。automake TESTS 单元 9 全绿；test_package 消费者 6 断言单列（rule12 鸿蒙行），不进上游分母。
- **prefix=/ 配置链**：conan 约定 `--prefix=/` + DESTDIR 安装使内嵌 `/etc/presage.xml`、`/share/presage/*` 绝对路径在消费端不可达；ProfileManager 加载顺序为 内建默认 → /etc → $HOME/.presage → 用户指定（argv）。test_package 在 test() 内按 package_folder 现场生成 profile（@PKGDIR@/@WRITEDIR@ 双占位），ngram 库/dejavu/arpa 全部重定向到 build 目录副本 —— 消费者运行**零包体变更、零真实 HOME 写入**。
- 原生安装树 6 个可执行（presage_demo/presage_demo_text/presage_simulator/text2ngram + dbus 两件），软件级 commands.json 已建（archives/p/presage/commands.json）；L2 smoke 对 --version 失败为 warn 不阻塞（上游工具不带 --version 参数属正常）。
- help2man/swig/python-dev/doxygen/gtk2 设备与 CI 均缺失 → man 页不重建（tarball 自带 .1 不安装，双端一致）、python binding 显式禁用、doc/gtk 条件跳过。
