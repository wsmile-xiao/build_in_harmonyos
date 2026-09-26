# jaula 1.4.0 — OpenHarmony 适配记录（hw-9，真机 W3 已通过）

## 基本信息
- 软件：jaula（JAULA = JSON Analysis User Library Acronym），C++ JSON 词法/语法分析库
- 版本：1.4.0（上游发布 2009-01-11，tarball 内文件时间戳 Jan 12 2009）
- 构建系统：autotools（autoconf 2.61 **已预生成 configure**，19981 行 + automake 1.10 风格 + libtool 1.5 时代 `AC_PROG_LIBTOOL`，自带 ltmain.sh=libtool 2.2.4 Debian）
- 目标：ohos-aarch64（os=OHOS, arch=armv8, clang/clang++）
- 源码规模：全树 71 个文件；C++ 侧 18 个 `.cc` + 18 个 `.h` + 1 个 flex 源 `.ll`（**上游源码树清点口径**；本次实际编译范围见下——`make -C jaula` 只建库本体，`examples/` 的 2 个 `.cc` 不构建）
- 上游（官方托管，交付形态）：
  `https://downloads.sourceforge.net/project/jaula/jaula/jaula-1.4.0/jaula-1.4.0.tar.bz2`
  SHA256 `b041e40cd58ae77d1db8fccc25a32c3b55097fe93941c0cf1973f60c28586709`，333324 B（实测 HTTP 200）
- 项目主页：https://sourceforge.net/projects/jaula （取自包内 README:18 与 NEWS:10）
- License：LGPL-2.1-or-later（包内 COPYING 与 jaula.h 头部声明一致）

## 上游 URL 选型（为什么不用 Debian/Ubuntu pool 件）
候选池最初给的是 `https://mirrors.mivocloud.com/ubuntu/pool/universe/j/jaula/jaula_1.4.0.orig.tar.gz`
（e22ab944d2821f3109e29e4b572a317185b6e3579cb46d74c9a70f10a7158364 / 408075 B，实测 GET 200）。
核查结论：**该件不是上游发布物本体，而是 Debian 的重压缩产物**——官方 SourceForge 文件区
`projects/jaula/files/jaula/jaula-1.4.0/` 下只有 `.tar.bz2` 一种形态，没有 `.tar.gz`；
`.dsc` 为 `Format: 3.0 (quilt)`（`.orig` 未改内容，Debian 改动单独在 `.debian.tar.xz`）。
预检 PF7 源URL闸明确拦"镜像域名 / Debian 重打包 / 搬运源"，因此交付一律用官方 `.tar.bz2`
标量 URL + 其自身 sha256，镜像 URL 不入 `conandata.yml`。
可迁移性佐证：两棵树在本机 `diff -r` **逐文件完全一致**（`IDENTICAL`），所以本记录里所有
源码级取证对官方件同样成立。
副作用待办：dlcache 预缓存只能按 bz2 的 sha256 从 SourceForge 直取（镜像站无 bz2 形态），
CI worker 对 SF 的可达性需首构建时实证，不可达则按 §12.3 预置 + sidecar 登记官方 URL。

## 编译指导（含复用的知识库条目）
1. **三元组（E544 / E122 家族，本机已复现签名）**：本包 `config.sub` 时间戳 `2008-01-16`、
   case 风格。本机直跑得到：
   - `sh config.sub aarch64-unknown-linux-ohos` → `Invalid configuration ... machine `aarch64-unknown-linux' not recognized`
   - `sh config.sub aarch64-unknown-linux-gnu` → 原样回显（说明 **aarch64 CPU 层是认的**，
     拒绝发生在 **kernel/OS 后缀层**，与 E122 `linux-ohos` / E072 三元组校验同层）
   处置沿用 cityhash/1.1.1 的既有正解（经验汇总 §12.21、§5.3b 第 2 项）：只显式传
   `--build=aarch64-unknown-linux-gnu`、**不传 `--host`**（设备原生构建时 host 缺省等于 build）。
   `configure.in` 里没有 `AC_CANONICAL_*`，只有 libtool/automake 展开段在 2517/2534/2570 行
   调 config.sub，不传 --host 就不会触发对 OHOS 后缀的校验，**因此不需要任何源码补丁**，
   也不必上 E007 的整文件替换（proxyknife #9866 的 6k 行教训）。
   `config.guess`（2008-01-23）在全树没有任何 `aarch64` 分支，但显式给 `--build` 后不被调用，
   故 E160/E007 的 guess 层补丁在本包**不适用**（写在这里是为了防止后来者照抄）。
2. **shell（E386 家族）**：configure 就地钉 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh`，避开
   profile 指定的 hnp bash 在 HMDFS 构建目录 `getcwd()` 失败。
3. **flex 是宿主依赖，不只是构建工具（本包最关键的结构判断）**：
   `jaula/jaula_lexan.h:65` 公开头里 `#include <FlexLexer.h>`（且用了 flex 的
   `#define yyFlexLexer jaulaFlexLexer` 前缀改名技巧），而 `jaula_lexan.h` 经
   `jaula.h → jaula_parse.h → jaula_lexan.h` 传染到**每一个消费者**；同时
   `JAULA::Lexan : public ::jaulaFlexLexer`（`.ll` 里 `%option yyclass="JAULA::Lexan"` +
   `%option prefix="jaula"`）。**但基类实现不进 libfl**：真机 `nm` 实测 `libjaula.a` 的 40 条
   FlexLexer 符号为 **35 已定义(T) / 0 未定义(U)**，`libfl.a` 内该类符号 **0 条**，且 configure
   报 `checking lex library... none needed` ⇒ flex 随 `%option c++` 把基类实现直接生成进本包
   目标码，**消费者只需头、链接期不需要 `-lfl`**。因此配方同时声明
   `requires("flex/2.6.4")`（只给消费者传头）+ `tool_requires("flex/2.6.4")`
   （给构建期 PATH 上的 flex 可执行文件，因为 `jaula_lexan.ll` 是 `nodist_*_SOURCES`，
   扫描器源码不落盘、必须现场生成；configure.in 对 `LEX != flex` 与缺 `FlexLexer.h`
   都是 `AC_MSG_ERROR` 硬失败）。`package_info()` 里 `cpp_info.requires = ["flex::flex"]` 实测不传导（同包占两上下文），
   把这条链显式传给下游。
   归档树核查：`flex/2.6.4` 与 `2.6.4.2` 均已注册，其制品把 `FlexLexer.h` 放进 `include/`、
   并打包 `libfl.a`（读配方 package()/package_info() 确认）。二进制可用性仍待设备
   `preflight`/`conan download --only-recipe` 实证（禁通配判 binary）。
   另注：`configure` 必须带 `env="conanbuild"` 执行，否则 AutotoolsToolchain 汇总的
   flex `-I/-L` 进不去，`AC_CHECK_HEADERS(FlexLexer.h)` 会假性失败。
4. **只构建库本体**：顶层 `SUBDIRS` 由 configure.in 硬编码为 `"doc jaula examples"`。
   `examples/jparse.cc` 使用 C++17 已移除的 `std::auto_ptr`，`lextst` 又写死
   `LDFLAGS = -static`；`doc/` 在无 doxygen 时是空转目标。二者都不参与库与头文件的构建，
   故 `build()` 用 `make -C jaula -j1` 收敛范围。
5. **不跑 make install**：`doc/Makefile.in:551` 起的 `install-data-local` 有 8 条无守卫的 `test -n "$(DOXYGEN)" && ...` 短路行（第 552/553/559/560/561/567/568/569 行；同文件第 546 行还有一处在 `doc:` 目标里，全文共 9 处）
   `test -n "$(DOXYGEN)" && ...`；未启用 doxygen 时 `$(DOXYGEN)` 为空，该短路式返回 1
   （本机 `sh -c 'test -n "" && mkdir -p ./x'` 实测 rc=1），会让整条 `make install` 链
   `Error 1`。改为 `package()` 按产物实体拷贝，从设计上不触发它；同时静态打包规避
   libtool `.so/.so.0/.so.0.0.0` 三件套在 HMDFS 上的符号链接脆弱性（§12.21 cityhash 先例）。
6. **头文件目录层级不可压平**：上游 `include_HEADERS = jaula.h`、
   `pkginclude_HEADERS` = 其余 17 个头，且公开头内部一律 `#include <jaula/xxx.h>`；
   `package()` 按 `include/jaula.h` + `include/jaula/*.h` 两层摆放（excludes 掉重复的 jaula.h）。

## 上游测试统计（口径）
- `N_static = 0`。判据是逐项统计注册入口而非"日志没跑"：全树 4 个 `Makefile.am` 中
  `grep TESTS|check_PROGRAMS|dist_check_SCRIPTS` **零命中**，上游根本没有自动化测试套件；
  `jaula/Makefile.am` 只有 `lib_LTLIBRARIES = libjaula.la`。
- `examples/` 的 `jparse`（bin_PROGRAMS）与 `lextst`（noinst_PROGRAMS）是**演示程序**，
  不注册为测试、无断言、恒返回 0，不得计入上游测试数，也不得当作"跑过 make check"。
- `N_registered = 0`，`N_executed = 0`（无入口可执行，非"跳过"）。
  **上游通过率不写 100%，写"无可执行上游套件 0/0"，并在 PR 正文的未执行说明里给判据。**
- `N_consumer = 3`（3 个真实消费者程序），`N_assertion = 32`
  （test_parse 14 / test_corpus 11 / test_errors 7）。
  三个程序均编译 + 链接打包产物 `libjaula.a` + 调用公开 API，用断言计数决定退出码：
  解析嵌套对象/数组、按 `dynamic_cast` 下转型取 `getData()`（string/int/double/bool/null）、
  内嵌上游语料做 repr 精确往返（`example1.json` 逐字原文，该文件本就是单行；`example3.json` 为压平缩进后的等价内容）（`"[ 100, 500, 300, 200, 400 ]"`）、
  编程式 `addItem`/`insertItem` 容器 API，以及 4 条负例——上游自带畸形语料
  `malformed_example3.json` 的前 2 个对象（上游共 7 个，截断即可稳定触发词法拒绝）、截断数组、`Value_String::set(Value_Number_Int)`、
  重复键，分别断言 `getCode()` 落在 SYNTAX/LEXAN、`BAD_DATA_TYPE`、`NAME_DUPLICATED`
  （异常码取自 `jaula_exception.h` 的 `ExCode` 枚举，`Value_Array::addItem` 与
  `Value_Object::insertItem` 的 `duplicate()` 深拷语义取自对应 .cc 实现）。
- **本机已做的编译级校验（不替代设备运行）**：三个 test_*.cpp 用真实公开头
  `g++ -std=c++11 -fsyntax-only` 全部 rc=0（FlexLexer.h 用最小桩，仅本机诊断用，不进交付），
  这排掉了 API 误用类失败，但不构成"测试通过"证据。

## 补丁清单
- `patches/0001-configure.patch`（+2/-2，`strip: 1`，`platform_only: True`）：只把 `configure`
  第 18391、18396 行两处 `umask 077` 放宽为 `umask 022`（E011/E114）。
  **生成方式**：由框架正门 `ohc-run.py refresh-patch --auto jaula 1.4.0` 生成（先经
  `init-build` 产出 `~/builds/jaula-1.4.0.orig` / `.work` 两份独立副本，只改 `.work`，
  工具逐文件 difflib 出补丁）——`manifest.yaml` 里 `patch_generation.method: per-file-difflib`
  就是该工具的自有标签，不是手工搓补丁；`finish` step [1/10] 复跑一次，仅刷新
  `source_work_hash`/`generated_at`。`patch_classification.guard: pending` 是工具留给
  人工编辑的默认值（已合入的 cityhash 1.1.1 同为 pending），本窗不自造取值。
  除该补丁外无其它补丁：本包 `configure` 随 tarball 预生成（autoconf 2.61），
  三元组与 shell 问题都在配方命令行侧解决。
- 修因证据链（真机原始日志，可按轮次回溯 `~/tmp/uc2/hw-9/logs/`）：
  `build2.log` 内 `./config.status[869]: can't create ./confYD6b6b/subs-1.sed: Permission denied` 与 `./config.status[2135]: can't create ./confYD6b6b/out: Permission denied`
  与 `sed: couldn't open file ./confYD6b6b/subs-1.sed: Permission denied` 两串，
  （build2.log 第 215/218/219 行逐字），后随 `make: *** No targets specified and no makefile found`；
  补上 022 放宽的 `build3.log` 起，同一位置出现 6 行 `config.status: creating ...`
  （根/`doc/`/`jaula/`/`examples/` 的 Makefile + `doc/Doxyfile` + `config.h`）且编译正式开始。

## 已知限制（草案，最终按设备实测收敛后写入 PR 正文）
- 仅支持静态打包（`shared=False` 默认）：共享形态未经验证，且 libtool 2.2.4 老脚本 +
  HMDFS 符号链接链在 OHOS 上风险高。
- `examples/`（jparse、lextst）不随本配方构建：`jparse.cc` 依赖 C++17 已移除的
  `std::auto_ptr`，`lextst` 写死 `-static`。这不是 OHOS 特有问题，属上游代码年代问题。
- 公开头使用**动态异常规范**（`throw(...)`，9 个公开头共 13 处），C++17 起该语法被移除 ⇒
  消费者的 `-std` 必须 ≤ C++14（`test_package/CMakeLists.txt` 显式钉 `CXX_STANDARD 11` 并注释原因）。
  本机 g++ 6.3 在 `-std=c++17` 下未把这 13 处升级为 error（该版本尚不给诊断，GCC 7+ 才报
  `ISO C++17 does not allow dynamic exception specifications`），**故此条对设备 clang 15 的影响尚未实证**，
  列入下面"待设备实证"第 1 项，不作为已成立结论。
- 上游语言 RFC 4627 时代的 JSON 解析器（2009 年停更），无 unicode 转义完善支持；
  本次只验证行为契约，不改上游语义。

## 待设备实证清单（恢复连接后的第一优先，逐条留最小证据包）
1. clang 15 默认 `cppstd` 下**库自身源码**编译是否因 13 处动态异常规范报错。若报：按 §12.53
   家族在 `configure()` 里 `del self.settings.compiler.cppstd`（回落 gnu++14），并在本文件补
   实测诊断行；若这是知识库首次以"公开头传染给消费者"的形态记录 ⇒ 按 §6.2⑦ 第 3 条升 B=create。
2. flex 生成链：`make -C jaula` 时 `%option c++` 生成的扫描器是否含 `register`（C++17 报错，
   同 §12.53 家族）；以及 `lex.jaulascanner.cc` 与 automake `.ll` 规则、`ylwrap` 的命名是否吻合。
3. `AC_CHECK_HEADERS(FlexLexer.h)` 在 `env="conanbuild"` 下确实通过（若不过，说明 tool_requires
   的 include 未进 CPPFLAGS，改走显式 `-I`）。
4. ~~`libjaula.a` 的 `yyFlexLexer` 未定义引用能否由 `libfl.a` 满足~~ → **已否证**：`nm` 实测
   `libjaula.a` 的 FlexLexer 符号 35 已定义 / 0 未定义，`libfl.a` 内该类符号 0 条，configure 亦报
   `checking lex library... none needed` ⇒ 基类实现由 flex 生成进本包，**不依赖 libfl**；
   `package_info()` 因此只转递 flex 的 include 目录，不再塞 `libdirs`/`libs`。
5. 消费者运行期：OHOS 未签名 ELF 的加载与自签流程；三个 test 程序的实际退出码与断言计数。
6. `config.status`/umask 家族（E011/E114）与 HMDFS getcwd（E386）是否在本包真撞；
   未撞则不配送，**不得按"老 autotools 包必然撞"空走**。
7. `preflight` 的 `configure_options` 解析与 `manifest.yaml` 对齐（本表已按仓库惯例填写）。

## 路径 B 判断（§6.2①，W0b 阶段结论）
- **结论：`B判定=hit`**（本 PR 不携带知识草稿；§6.2⑦ 第 1 条一 PR 一知识，且无可复用新增机制成立）。
- **症状签名命中**：`Invalid configuration 'aarch64-unknown-linux-ohos': machine 'aarch64-unknown-linux' not recognized`
  —— 本机对**本包自带的** config.sub 直接跑出该串，且 经验汇总 §5.3b 第 2 项正是
  "以 2008-01-16 版为例"、连验证命令 `sh config.sub aarch64-unknown-linux-ohos` 都同源；
  知识库条目侧对应 **E122**（config.sub kernel-os 段不认 `linux-ohos`）与 **E072**（三元组校验）。
- **解法命中**：cityhash/1.1.1 的既有正解（§12.21、E544-draft 所记机制）—— 只传
  `--build=aarch64-unknown-linux-gnu`、不传 `--host`；本包实测该三元组被 config.sub 原样接受，
  等效性成立且**不丢任何依赖探测信息**（未改用 `AC_CHECK_LIB` 类替代探测）。
- **层次修正（不新增知识，只防误引）**：E544 的表述偏"CPU 层不认 aarch64"，本包属
  **OS/kernel 后缀层**（aarch64-unknown-linux-gnu 被接受），引用时按后者写，避免混引被打回。
- **明列不适用**：E007 / E160（config.guess 层，显式 `--build` 时根本不调用；且 §5.3b 前言
  指出 `patch-autotools-ohos.pl` 只覆盖 2018+ field 风格 config.sub / 2017+ config.guess，
  本包 2008 case 风格照抄即空走）。
- **create 候选（挂起，等实证，不在本轮申报）**：①"公开头含 13 处动态异常规范 ⇒ C++17 消费者
  连编译都进不去"的**头文件传染**形态；②"`test -n "$(DOXYGEN)" && ...` 无守卫短路 ⇒
  `make install` 必败"的 doxygen 时代 autotools 包通用坑；③"`jaula_lexan.h` 把 `FlexLexer.h`
  写进公开头 ⇒ flex 必须按宿主依赖建模**传头**；链接维另以 nm 定，本包实测不需要 libfl"。三条均已 grep 知识库确认**无既有条目**，但按
  §6.2⑦ 第 3 条"证据从严、禁止空走"，必须有设备实测症状 + 已验证修法才升 create；
  本包设计上已绕开 ②（不跑 make install），故 ② 只有改走 make install 才成立。

## 真机实证回填（2026-09-25 12:20–12:50，hw-9，鸿蒙 PC / clang 15.0.4 / conan 2.29.1）

上面"待设备实证清单"7 项已全部有结论（构建 `CREATE_RC=0`，memcap 峰值 **278MB**/预算 2048MB，用时 149s）：

| 项 | 结果 | 凭据 |
|---|---|---|
| 1 DES + cppstd=17 | **撞上**，已修 | `jaula_value.h:110:45: error: ISO C++17 does not allow dynamic exception specifications`；修=`rm_safe("compiler.cppstd")` → 编译行无 `-std=` → clang 15 回落 gnu++14 |
| 1b auto_ptr | **比草案更严重**：不止 examples，**库自身** `jaula_parse.cc` 有 6 处 `std::auto_ptr`（gnu++14 下仅 `-Wdeprecated-declarations` 告警，6 warnings generated） ⇒ cppstd 上限是本包硬约束而非偏好 |
| 2 flex 生成链 | 通过：`configure: checking for flex... flex`，生成的扫描器参与编译，jaula/ 的 16 个手写 `.cc` + 生成的 `jaula_lexan.cc` = 17 个 TU 全过；未见 `register` 报错（flex 2.6.4 + gnu++14 无该问题） |
| 3 FlexLexer.h 探测 | **先撞后修**：`configure: error: Header not found` → 根因是 conan 2.29 的 `AutotoolsToolchain` 不注入宿主依赖 flags，须另生成 `AutotoolsDeps`（§5.3 API 坑集既有记录，判 hit）。修后 `CPPFLAGS` 内含 `-I<flex>/include` |
| 3b E386/umask | **撞上**：`config.status[2135]: can't create ./confYD6b6b/out: Permission denied` + `sed: couldn't open file ./confYD6b6b/subs-1.sed: Permission denied`，导致 6 个输出（根与 `doc/`/`jaula/`/`examples/` 的 Makefile + `doc/Doxyfile` + `config.h`）全部静默写不出——打上补丁后同一位置恰好出现 6 行 `config.status: creating ...`（build3.log 第 218-223 行逐条可点验） ⇒ E011/E114 命中，`0001-configure.patch` 放宽两处 `umask 077→022`（与 cityhash 合入先例同形；configure 内 18391/18396 行与 §5.3 记录逐字一致） |
| 4 libfl 是否必需 | **否证并已收紧**：`nm` 实测 `libjaula.a` 的 FlexLexer 符号 35 已定义(T)/0 未定义(U)、`libfl.a` 内该类符号 0 条，configure 报 `checking lex library... none needed` ⇒ 基类实现已在包内，消费者只需头。`package_info()` 已从「展开 includedirs+libdirs+libs」收紧为「只展开 includedirs」 |
| 5 消费者运行 | **32/32 断言通过**：`test_parse 14/14`、`test_corpus 11/11`、`test_errors 7/7`；负例 `malformed_example3.json` 被拒且 `getCode()=3`（LEXAN_ERROR，落在断言允许的 SYNTAX/LEXAN 集合内） |
| 6 M13 | **不成立已坐实**（三条源码级证据，且真机 `make install` 未走，无任何 install 缺失报错） |
| 7 configure_options/manifest | 已回填（status: built、patches_applied、knowledge_gained） |

新增加固（草案未预料）：**automake 1.10.x（本包由 1.10.1 生成）的 `DEFAULT_INCLUDES` 不含 `$(top_srcdir)`**
（实测 `Makefile:79 DEFAULT_INCLUDES = -I. -I$(srcdir) -I$(top_builddir)`），而本包公开头一律
`#include <jaula/xxx.h>` ⇒ VPATH 构建下无一层 -I 可解析。真机首错
`jaula_bad_data_type.h:32:10: fatal error: 'jaula/jaula_exception.h' file not found`。
修法取 make 命令行覆盖 `AM_CXXFLAGS=-I<源码根>`（零改上游、不覆盖 AutotoolsDeps 的 CPPFLAGS）；
备选 in-source layout（与 `DRAFT-kakasi-2.3.6` 同路径）。

**路径 B 判定改判（覆盖上文 hit 结论）**：`B判定=create(新草稿：DRAFT-jaula-1.4.0-automake-default-includes-lacks-top-srcdir)`，`B草稿=DRAFT-jaula-1.4.0-automake-default-includes-lacks-top-srcdir`（.kv/.md 同 stem 成对）。
理由：草案阶段的 config.sub/E122 那条确为 hit，但真机另撞出一条 0 命中机制
（`grep -c DEFAULT_INCLUDES|top_srcdir 经验文档/*.md` = 0；仓库 `knowledge/` 全库检索仅命中
`DRAFT-10251-libnfc-*`（写了 `-I$(top_srcdir)` 却被**空 per-target** `*_CPPFLAGS` 顶掉，签名与根因均不同）
与 `DRAFT-kakasi-*`（Makefile 完全不支持 VPATH，报 `No rule to make target`）——
按 §6.2② 第 3 条"只写同族不算依据"，本条是第三种独立签名）。
`draft-review` 结论 = **create**（TOP3 相似 0.16 / 0.09 / 0.08，无等价条目），
`.kv`/`.md` 同 stem 成对随本 PR 提交，`graph validate` 无本条引入的错误。

**未随本 PR 的第二条机制**（按 §6.2⑦ 第 1 条一 PR 一知识，转 `经验文档/B草稿库/` 货源）：
"工具包（flex/bison/gperf 类）的**公开头**进入宿主包 include 闭包 ⇒ 必须 `requires` +
`tool_requires` 双声明，且 `cpp_info.requires` 在 flex 同时占 build/host 两上下文时
不被 CMakeDeps 传导（真机证据：`jaula-release-armv8-data.cmake` 的
`jaula_INCLUDE_DIRS` 只有本包 `include/`，消费者报 `'FlexLexer.h' file not found`），
须按依赖实体把 flex 的 include 目录展开进 `cpp_info.includedirs`（只展开头，链接期实测不需 libfl）"。知识库 `grep FlexLexer|yyFlexLexer|libfl` = 0 命中。

## 已知限制（真机确认后的最终口径）
- 消费者必须以 `-std<=C++14` 编译：本包 9 个公开头含 13 处动态异常规范，且库自身依赖
  `std::auto_ptr`；`test_package/CMakeLists.txt` 已显式钉 `CXX_STANDARD 11` 并注释原因。
- 仅静态打包（`shared=False`）；共享形态未验证。
- `examples/`（jparse、lextst）不随配方构建（`make -C jaula`），库与头文件的产出不依赖它们。
- 上游无自动化测试套件，`N_static=0`；本包功能正确性由 3 个消费者程序 32 条断言承载。

---
（`## 编译结束 / 最终状态` 收尾块由 `ohc-run.py finish` 生成，不手填。）
