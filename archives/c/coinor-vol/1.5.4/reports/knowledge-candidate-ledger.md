# coinor-vol 1.5.4 知识候选台账（四范围查重 + 七轴 + 路径判断）

生成时间: 2026-09-08T11:55Z
查重范围: 正式知识 knowledge/doc/、图谱 knowledge/graph/（index.tsv + E*.kv）、
草稿 knowledge/drafts/ + knowledge/DRAFT-*、既有库归档 archives/（含同族
coinor-dylp/coinor-osi/coinor-cbc 等）

## 候选 1：2007 版 config.guess/config.sub 无法识别 HarmonyOS/aarch64

- 真实错误: `configure: error: cannot guess build type; you must specify one`
  （config.guess timestamp=2007-05-17，UNAME_SYSTEM=HarmonyOS 无匹配分支）
- 根因: COIN-OR 项目自带 2007 版 GNU config.guess/config.sub，无 HarmonyOS 分支，
  无 aarch64 CPU 与 linux-musl OS 识别
- 修复: 4 个最小补丁（0001/0002 顶层 + 0003/0004 Vol/ 子目录），config.guess 加
  HarmonyOS/HongMeng + aarch64:Linux 分支；config.sub 加 aarch64/aarch64_be CPU
  与 linux-musl kernel-os 识别（3 处）
- 验证: 补丁后 `./config.guess` 输出 aarch64-unknown-linux-musl；configure rc=0；
  conan-verify G2 干净构建 PASS
- 适用范围: 所有自带 2007-era config.guess/config.sub 的 COIN-OR 递归工程
- 四范围查重:
  - graph: E007（config.guess HarmonyOS 分支）、E072（config.sub ohos 三元组）、
    E122（config.sub kernel-os linux-ohos 校验）、E160（config-guess-harmonyos-patch）、
    E205（config.guess/config.sub OHOS triplet）、E268（config.sub linux-ohos 校验）
    → 高覆盖
  - doc: E007.md/E072.md/E160.md/E205.md 均为既有正式文档
  - drafts: 无新草稿命中（既有 E017 ghproxy 等与本候选无关）
  - archives: coinor-dylp/1.10.4 manifest knowledge_gained 已记录同类问题
- 七轴: exact_duplicate=no；causal_duplicate=yes（与 E007/E160 根因同源）；
  trigger_overlap=high；solution_overlap=high（同为 patch-autotools-script）；
  combination_novelty=low（顶层+子目录双份为 COIN-OR 递归工程共性，dylp 已实践）；
  boundary_novelty=low；test_migration_novelty=none
- 关系: similar_to=E007,E072,E160,E205,E268；caused_by=E007
- 路径判断: reuse_existing（复用 E007/E160 等既有知识；不新建草稿）

## 候选 2：HMDFS 上 config.status mktemp/umask 077 权限失败

- 真实错误: `./config.status: can't create ./confstatXXXXXX/out: Permission denied`
- 根因: HMDFS 目录强制 setgid，umask 077 创建 drwx--S--- 使属主也无法写入
- 修复: sed 修补 config.status（顶层+Vol/）：mktemp→mkdir -p ./conftmp、umask 077→022，
  重跑 config.status
- 验证: config.status rc=0，Makefile/inc/config_vol.h 正常生成；conan-verify G2 PASS
- 适用范围: 所有在 HarmonyOS/HMDFS 上使用 configure/config.status 的 autotools 工程
- 四范围查重: graph E129（root_cause/rec 与本次完全一致）、doc/E129.md 既有
- 七轴: exact_duplicate=yes（E129 完全覆盖）；其余轴均 no/none
- 关系: similar_to=E129
- 路径判断: reuse_existing（E129）

## 候选 3：C++17 下 register 关键字位于安装的公共头文件

- 真实错误: `error: ISO C++17 does not allow 'register' storage class specifier`
  （VolVolume.hpp 3 处：VolMax/VolAbs 模板 + factor() 局部变量）
- 根因: 2003 年代 C++ 代码使用 register 存储说明符；OHOS profile cppstd=17 下从
  warning 升级为 hard error；且该关键字位于**安装到 include/coin/ 的公共头文件**，
  消费者包含头文件时同样编译失败
- 修复: 0005 补丁源码移除 3 处 register（非 toolchain-flag，因公共头文件消费者
  无法被库构建期 -Wno-error 保护）
- 验证: clang++ -std=c++17 -stdlib=libc++ 编译 rc=0 无警告；conan-verify G2 PASS；
  test_package 消费者（-std=c++17 包含头文件）1/1 Passed
- 适用范围: 所有 2003 年代 C++ 库在 cppstd=17 下，且 register 位于被安装公共
  头文件（消费者受影响）的场景
- 四范围查重:
  - graph: E293（root_cause 同源 register/C++17）→ 部分覆盖；E293 rec_approach=
    toolchain-flag（-Wno-error=register），仅解决库自身构建，未覆盖"安装在公共
    头文件 → 消费者包含失败"边界；其 fallback source-patch 只针对 src/*.cpp
  - doc: E293.md 无 header/consumer/安装 相关内容（grep 0 命中）
  - drafts: 无 register-installed-header 草稿（grep 无命中）
  - archives: 本次 coinor-vol 为实测案例
- 七轴: exact_duplicate=no；causal_duplicate=yes（根因与 E293 同源）；
  trigger_overlap=high；solution_overlap=partial（E293 primary=toolchain-flag 在本场景
  不充分；source-patch 为其 fallback，但未区分安装头文件消费者边界）；
  combination_novelty=low；**boundary_novelty=yes**（新边界：register 位于安装公共
  头文件 → 必须源码补丁而非 toolchain-flag，消费者包含头文件是决策关键）；
  test_migration_novelty=none
- 关系: similar_to=E293；caused_by=E293 场景扩展
- 路径判断: **new_draft（路径 B）**——已验证、可跨库复用（任何 2003 年代 C++ 库
  安装公共头文件均适用）、查重为部分覆盖且存在边界新增差异

## 候选 4：conan relocatable 打包破坏 .la dependency_libs 绝对路径

- 真实错误: `libtool: link: cannot find the library '//lib/libCoinUtils.la'`
  （恢复 osiUnitTest 构建时）
- 根因: conan relocatable 打包把依赖 .la 的 dependency_libs 绝对路径改写为
  //lib/xxx.la，libtool 无法解析
- 修复: 恢复 libOsi.la/libOsiCommonTests.la 内真实绝对路径（仅在测试恢复验证
  场景；正式配方 requirements 为空，不涉此）
- 验证: osiUnitTest 链接成功（后运行阻塞于外部数据，见测试台账）
- 适用范围: autotools+libtool 消费 conan 静态依赖 .la 元数据的场景
- 四范围查重: graph E236（root_cause 完全同源，rec=scoped-la-free-static-archive-
  directory，fallback=regenerate-relocatable-libtool-metadata）、E443/E448 相关；
  doc/E236.md 既有
- 七轴: exact_duplicate=partial；causal_duplicate=yes（E236 同源）；
  solution_overlap=high；其余 no/none
- 关系: similar_to=E236,E443
- 路径判断: reuse_existing（E236 已覆盖，不新建草稿）

## 候选 5：上游 osiUnitTest 测试入口依赖外部 Sample 数据不可得

- 真实错误: `Coin6001E Unable to open mps input file ../../Data/Sample/exmip1.mps`
  → SIGSEGV
- 根因: COIN-OR Data/Sample（exmip1.mps）为独立外部数据包（Dependencies svn
  external），registry 无包且官方 GitHub/SVN 源不可达（404）
- 修复: 无配方侧修复；记录恢复条件（发布 Data/Sample 数据包后以 -mpsDir 运行）
- 验证: 依赖恢复尝试已证明构建链路完整（osiUnitTest 构建成功）
- 适用范围: 外部数据依赖阻塞类测试入口
- 四范围查重: 既有知识未覆盖具体 Data/Sample 包缺失；属外部阻塞非适配知识
- 路径判断: path_a_no_knowledge（外部数据阻塞，非可复用适配知识，不建草稿）

## 候选 6（R02 新增）：配方硬编码 TMPDIR=$HOME/tmp 在 CI worker 上不可写/不存在

- 真实错误: `checking for C compiler default output file name... configure: error: C compiler cannot create executables`
  （conan build() Error 77）；config.log 首错 `clang-15: error: unable to make temporary file:
  Read-only file system`（或 `No such file or directory`）
- 根因: 配方为规避 HMDFS /tmp 只读（E002），把 `TMPDIR` 硬编码为 `$HOME/tmp`，
  但 CI worker 沙箱下该路径不存在或对构建用户不可写；clang 需要 TMPDIR 创建临时文件，
  失败导致 configure 首个 C 编译测试无法产出可执行文件
- 修复: `build()` 中改用候选列表（`$HOME/tmp` → conan `build_folder/.tmp`），用
  **真实文件写入探测**（HMDFS 忽略 chmod 与 `os.access(X_OK)`，见 E046/R49）选择首个
  可写目录，均失败才回退 `$HOME/tmp`
- 验证: 只读/不存在 TMPDIR 下同一 configure 命令复现 Error 77（与 CI 完全一致，
  两日志 sha256 见 notes.md R02 补记）；修复后 conan create rc=0、test_package 1/1 Passed；
  回退探测单测（HOME=/tmp 只读 → 正确回退 build_folder/.tmp）通过
- 适用范围: 所有在 HarmonyOS/HMDFS 或 CI worker 沙箱上需要设置 TMPDIR 的
  autotools/conan 配方（E002 建议的直接设 `$HOME/tmp` 在 worker 上不充分）
- 四范围查重:
  - graph: E002（/tmp 只读 → TMPDIR=$HOME/tmp，rec_auto_fix=true）**部分覆盖**：
    E002 建议的目标目录本身在 CI worker 上不可写/不存在的场景未覆盖；
    E046（HMDFS 忽略 chmod/os.access）为探测方式依据；R49（build_folder 私有 prefix）
    提供回退候选
  - doc: E002.md 只有 set-env-var 一条建议，无"候选探测 + build_folder 回退"
  - drafts: 无 TMPDIR 探测回退草稿（grep 无命中）
  - archives: 无同类实测归档（libmysofa/asterisk-srtp 等 TMPDIR 案例均假设
    $HOME/tmp 可写）
- 七轴: exact_duplicate=no；causal_duplicate=partial（与 E002 同族"临时目录不可写"）；
  trigger_overlap=high（clang unable to make temporary file）；solution_overlap=partial
  （E002 的 set-env-var 建议单独使用不充分，须加写入探测 + build_folder 回退）；
  combination_novelty=low；**boundary_novelty=yes**（新边界：E002 建议的目标目录本身
  可能不可写，且 HMDFS 下必须真实写入探测而非 os.access）；test_migration_novelty=none
- 关系: similar_to=E002,E046；caused_by=E002 场景扩展
- 路径判断: **new_draft（路径 B）**——已验证（本地复现 CI 首错 + 修复后全量通过）、
  可跨库复用（任何需设置 TMPDIR 的 HMDFS/CI 配方）；草稿 stem:
  `coinor-vol-1.5.4-tmpdir-writable-probe-fallback`

## 台账汇总与路径决定

| 候选 | 决定 | 依据 |
|------|------|------|
| 1 config.guess/sub HarmonyOS | reuse_existing | E007/E160/E205 完整覆盖 |
| 2 config.status umask/mktemp | reuse_existing | E129 精确覆盖 |
| 3 register 位于安装公共头文件 | **new_draft** | E293 部分覆盖 + boundary_novelty |
| 4 conan .la relocatable | reuse_existing | E236 覆盖 |
| 5 外部 Sample 数据 | path_a_no_knowledge | 外部阻塞非适配知识（R03 已解决数据，非知识项） |
| 6 TMPDIR 写入探测 + build_folder 回退 | **new_draft** | E002 部分覆盖 + boundary_novelty（R02 新增） |
| 7 C++17 移除 std::bind2nd | **new_draft** | E293 同族部分覆盖 + boundary_novelty（R03 新增） |

R03 更新（2026-09-10）：候选 7 为启用上游测试（COIN_HAS_OSITESTS）时 OsiVol
接口层编译错误的沉淀，草稿 `coinor-vol-1.5.4-std-bind2nd-removed-cpp17`
与 coinor-vol 归档同 PR 交付。候选 5 依赖数据已通过官方 Data-1.0.7.tgz 解决
（见 upstream-test-ledger.md 第三节），不再作为阻塞项。

## 候选 7（R03 新增）：C++17 移除 std::bind2nd 仿函数适配器

- 真实错误: `OsiVolSolverInterface.cpp:471: error: no member named 'bind2nd' in namespace 'std'`
  （OsiVol 接口层，R03 启用 COIN_HAS_OSITESTS 后暴露）
- 根因: std::bind2nd/bind1st/ptr_fun 等旧仿函数适配器 C++11 标记 deprecated、
  C++17 正式移除；2003 年代代码 `std::transform(... std::bind2nd(std::multiplies<double>(), k))`
  在 OHOS 固定 cppstd=17 下编译失败
- 修复: 0006 补丁用 lambda 替换（`[this](double v) { return v * objsense_; }`）；
  注意捕获陷阱——成员函数内访问成员变量必须显式 [this]，写 [member] 会报
  "does not name a variable" / "this cannot be implicitly captured"
- 验证: 替换后含 OsiVol 接口层 make rc=0、libOsiVol.a 构建成功、osiUnitTest 构建
  并实跑 3/3 (100%)（日志 sha256 见 notes/台账）；完整 conan create rc=0
- 适用范围: 所有 2003 年代 C++ 库在 cppstd=17 下使用 bind1st/bind2nd/ptr_fun/
  mem_fun 的代码（含被安装头文件与接口层）
- 四范围查重:
  - graph: E293（C++17 旧特性移除族）部分覆盖——E293 针对 register 关键字；
    bind2nd 为标准库 API 移除且 C++17 下为硬错误（无 toolchain-flag 兜底），
    知识库无 bind2nd/bind1st/ptr_fun 条目（grep 0 命中）
  - doc: 无 bind2nd 相关文档
  - drafts: 无（R03 新建）
  - archives: 无同类实测（libs 集内未见过期适配器案例）
- 七轴: exact_duplicate=no；causal_duplicate=partial（与 E293 同族"C++17 旧特性
  移除"，但具体物不同）；trigger_overlap=low（错误签名完全不同）；
  solution_overlap=partial（同需源码补丁，但 register 可 toolchain-flag 降级、
  bind2nd 无 flag 兜底）；combination_novelty=low；**boundary_novelty=yes**
  （新边界：绑定适配器移除 + lambda 捕获的 [this] 陷阱）；test_migration_novelty=none
- 关系: similar_to=E293；caused_by=C++17 标准库移除
- 路径判断: **new_draft（路径 B）**——已验证（OsiVol 编译 + osiUnitTest 构建实跑）、
  可跨库复用（任何 2003 年代 C++ 库）；草稿 stem:
  `coinor-vol-1.5.4-std-bind2nd-removed-cpp17`

任务类型为知识库扩展（路径 B）：候选 3 满足"已验证、可跨库复用、查重部分覆盖且
存在新增差异"，必须建立同 stem 的 .md/.kv 草稿。草稿 stem:
`coinor-vol-1.5.4-register-installed-public-header-cpp17`（按既有 pangomm
草稿命名风格 `lib-version-slug`）。

## R04 补记（2026-09-10）：CI 链接失败 .la relocatable 路径解析——E236 真实存在且精确覆盖

- 真实错误（CI 首错）：`libtool: link: '//lib/libCoinUtils.la' is not a valid libtool archive`
  → `make[2]: *** [Makefile:400: libOsiVol.la] Error 1`
- 根因：CI 从 ohpcd 远端下载 coin-or/coinutils 二进制包后，依赖 .la 经 conan
  relocatable 处理残留 `//lib/xxx.la` 绝对路径引用；libtool 链接 libOsiVol.la
  时无法解析该路径。r03 本地复验消费的依赖缓存路径与 CI 远端下载路径不同，
  故本地通过而 CI 失败。
- **知识条目存在性重新判定（按真实证据）**：任务头称"知识库中 E236/E443 条目
  实际不存在，引用无效"，但实际核实 **E236.kv/E236.md 与 E443.kv/E443.md 均存在
  且登记于 index.tsv**（grep E236/E443 行命中 2）。E236 error_signature
  `library .*\.la was moved|is not a valid libtool archive` **精确匹配**本次首错，
  root_cause 与 match_keywords（`libdir='//lib'`、relocatable）同源；其 rec_approach
  = `scoped-la-free-static-archive-directory`（复制 .a 到无 .la 的私有目录 + -L -lname
  注入，不改缓存），且 forbid 修改依赖缓存 .la（保证可复现、不污染共享包）。
- **修复方案（采用 E236 rec）**：conanfile.py `_osi_configure_args()` 把依赖
  `libCoinUtils.a/libOsi.a/libOsiCommonTests.a` 复制到 build_folder
  `.dependency-archives`（无 .la 元数据），configure 以
  `-L<archdir> -lCoinUtils/-lOsi/-lOsiCommonTests` 注入（zlib 以真实路径追加），
  **不改动 conan 依赖缓存**。
- 验证：独立 CONAN_HOME 从 ohpcd 远端实际下载二进制包
  （coin-or/0.108.12#44987604:7f71754881#40b4e5d3、coinutils/2.11.13#6d91c7be:4b97726413#e79a289b8a）
  后完整 conan create rc=0，`creating libOsiVol.la`（原 Error 1 消失），
  osiUnitTest 构建成功，test_package 1/1 Passed；osiUnitTest 3 入口实跑 3/3 (100%)
  （日志 sha256 9ac3de06...）。
- 七轴：exact_duplicate=yes（E236 精确覆盖：同 error_signature、同根因、同 rec、
  同 forbid）；其余轴均 no/none
- 关系: similar_to=E236；caused_by=E236 场景复现
- 路径判断: **reuse_existing（E236）**——E236 真实存在且完整覆盖，按
  knowledge-reuse-governance 复用其 rec 方案，不新建草稿；r03 台账中"E236/E443
  覆盖"的引用实际有效（与任务头"不存在"陈述相反，已按证据修正）。