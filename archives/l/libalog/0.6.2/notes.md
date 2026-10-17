# libalog 0.6.2 适配笔记

- 申请人：momimgya；队伍：干。
- 上游：Alog（codelabs.ch Ada 日志框架），https://www.codelabs.ch/alog
- 源码：https://www.codelabs.ch/download/libalog-0.6.2.tar.bz2，
  sha256=4f6f41aa85f7dec4bc2b4e10a26957514247eee4b5a498762fddab1714768425
  （2026-09-26 从官方 URL 下载实测 57212 字节并计算）。
- License：LGPL-2.1-or-later（上游 LICENSE 文件为 LGPL Version 2.1）。

## W0 依赖检查

- 无制品仓依赖。两个外部输入均在构建时从官方源获取并做 sha256 校验：
  - GNAT 工具链：Alpine v3.20 main aarch64 gcc-gnat 13.2.1 等 21 个 apk
    （与 ada-bar-codes/005 完全相同的清单与校验值，真机已验证）。
  - 上游测试框架 Ahven 2.8：https://www.ahven-framework.com/releases/ahven-2.8.tar.gz，
    sha256=6ead94fbd1b95454e959cc2a343acfb2f733bcbf10d9a286214d1dec1b9e8e0c
    （取自作者官方 sha256-sums.txt，本地下载验签一致）。
- 制品仓 gcc-ada/9.5.0 为原生 OHOS GNAT，主配方与测试包均以
  tool_requires 消费（adacgi/1.6、libgmpada/1.6 先例），另加
  binutils/2.46.0 提供 as/ld/ar（libgmpada/1.6 先例）；gcc-ada 的
  bin/gcc 包装器在 baked sysroot 缺失的 runner 上全部调用失败，
  C 胶水改走 aarch64-OHOS 门禁的编译器选择，Ada 调用经
  fixed-ohos-gcc 垫片直调 gcc.real（见“第四轮/第五轮”）。

## 构建系统分析

- 上游构建：alog.gpr（static/dynamic 二选一）+ alog_tests.gpr（tests/coverage/profiling），
  由 Makefile 经 gprbuild/gprinstall 驱动；无 configure/CMake。
- OHOS/Alpine 均无 gprbuild（ada-bar-codes/005 已向 APKINDEX 核验），故用 gnatmake
  直接复刻两个模式：
  - static：gnatmake -c src/alog*.adb → obj/static-obj，设备 clang 编译
    src/glue_syslog.c → 同一 obj 目录，ar 归档为 libalog.a
    （复刻 alog_common.gpr Languages Ada+C）。
  - tests：gnatmake tests/test_runner.adb（-I src/tests/Ahven，-largs 链接静态库）
    → obj/test_runner。
- 省略项（均为纯诊断开关，不影响产物语义）：GPR 的 -gnatygAdISuxo/-gnatVa/-gnatwal/
  -gnatf/-gnatwe（为 GNAT 4.x-9 时代编写，GNAT 13 会报新警告）；C 胶水的 -Werror。
  保留 -O2 -gnatn、-fstack-check 的替代由 GNAT 默认栈检查覆盖。
- 安装布局对齐上游 gprinstall 参数：libalog.a + *.ali → lib/，*.ads → include/alog/。

## 上游测试盘点（总数 81，口径 auto）

- tests/test_runner.adb 串起 13 个 Ahven Testcase；Add_Test_Routine 注册数：
  helper 5、log_request 1、protected_container 3、maps 3、facility 7、
  facility-fd 11、facility-syslog 1、transform 1、transform-casing 2、
  logger 16、tasked_logger 11、active_logger 14、policy 6，合计 81。
- 运行方式：cwd=源码根（./data/*.ref 相对路径），Ahven 2.8 Text_Runner 输出
  `Passed : N`（及数量>0 时的 Failed/Errors/Skipped 行）为唯一计数源；
  解析器见 conanfile.py _parse_ahven_summary（行锚定正则，无字符串数数，
  缺失 Passed 行则直接失败不猜数）。
- facility-syslog 仅测 set/get origin，不需要 syslog 守护进程；FD/helper 测试
  读写本地文件，真机以 HMBS 注入的 TMPDIR 为准（默认源码根可写）。

## test_package（3 断言）

- alog_smoke.adb：Logger+FD facility 写两条消息到 ./alog_smoke.log 并回读校验
  （文件非空、含消息一、含消息二），打印 checks_passed=N。
- run_tests.sh：POSIX sh 包装器透传执行真实二进制（L0c 门禁可识别）。
- test_package/test() 另重取上游源码 + Ahven，针对已打包的库重新编译运行
  完整 81 例并输出 HMBS_UPSTREAM_TEST_RESULT（防 build() 缓存导致标记丢失）。

## 本轮状态（2026-09-26）

- 策略周期 2（与前三轮不同路线）：前三轮（解包重写→完整性守卫→签名严格门禁）
  均假设“gnat1 文件字节被签名/改写损坏”，本轮真机证据（signed gnat1 -v
  rc=-11 且 loader/dynamic 探针干净、无 Error relocating）证伪了该假设——
  门禁能拦下崩溃但修不好崩溃，且重试因覆盖签名文件 EPERM 从未执行。
  新假设：文件字节正常，崩溃来自进程环境——round-35 引入的 qsort_r
  LD_PRELOAD 垫片（仅链接期 ld 需要）被预加载进 BIND_NOW 的 gnat1，
  与上一轮门禁用全量 env 探针把垫片致崩误判为文件损坏。
- 改动（主配方与 test_package 同步，未提交）：_gnat_env 新增 with_shim 开关，
  编译器功能探针/激活全局 env/测试二进制运行一律 shim-free，垫片仅在真实
  链接命令（主配方 tests 链接、test_package 两处链接）前后临时导出；
  _restore_pristine_file 改为 unlink 后 O_EXCL 重建，修复签名文件覆盖 EPERM
  导致重试死路；签名门禁改用 clean env 结果，full-env 探针仅记录诊断。
- 真机证据：待 HMBS 预检验证（是否有效由下一次真机结果判定）。

## 第三轮同指纹修复（2026-09-26，新路线：废弃 Alpine 自引导，改用原生 gcc-ada）

- 前次结果比较：上轮栈加固＋差分分诊已完整执行——post-stack 探针仍 rc=-11
  （栈假设被证伪）、bare-env 探针 rc=-11（GNAT 驱动变量假设被证伪）、兄弟
  cc1 探针 rc=-11（cc1 走标准 objcopy＋签名路径却同错，证明两条签名路径对
  大体积后端皆坏）、NEEDED 回读为空（签名重建损坏 .dynamic 的活证据）。
  同一文件/环境修补范式已穷尽，必须换路线。
- 新路线：删除全部 Alpine 13.2.1 自引导代码（约 2000 行：apk 下载解包、
  patchelf 改写、双轨签名、垫片、分诊），改用制品仓原生 OHOS GNAT
  gcc-ada/9.5.0（tool_requires），与已合入的 adacgi/1.6、libgmpada/1.6 完全
  同模式：HNP bin 前置 PATH、gnatmake 直接构建、产物仅 binary-sign-tool
  自签（adacgi _sign_program 原样复用）、C 胶水改用 gcc-ada 自带 gcc。
- 真机证据：待 HMBS 预检验证（是否有效由下一次真机结果判定）。

- 仓库修复：删除 7 天前的残留 .git/index.lock（0 字节陈旧锁），重建 index；
  HEAD 已指向 feat/libalog-0.6.2（= upstream/main），配方为首轮新建文件。
- 真机证据：尚无。本轮新建配方树（conanfile.py/conandata.yml/manifest.yaml/
  notes.md/test_package/），等待 HMBS 真机预检给出第一组实测数据后再迭代。
- 已知风险（待真机验证）：
  1. GNAT 13 编译 2014 年 Ada 代码可能报新错误（非警告类），需按真机日志修补丁；
  2. glue_syslog.c 依赖设备 clang 的 syslog.h，若缺失则切 Alpine gcc -I 兜底；
  3. Tasked/Active logger 测试依赖 musl pthread/tasking，若有平台差异按 gaps 上报；
  4. codelabs.ch 小站点下载若在 CI 超时，按守则加镜像并保留官方回退。

## 第四轮同指纹修复（2026-09-26，新路线：绕行 stale 的 gcc 包装器）

- 前次结果比较：上轮“废弃 Alpine、改用原生 gcc-ada”已完整执行——
  真机首个新失败是 `build()` 的 `_build_c_glue`（`gcc -c
  glue_syslog.c` exit 1），且日志同时出现 `GCC Ada OHOS sysroot is
  unavailable: .../ohos-sdk_26.0.0.18/ohos/native/sysroot`。该报错来
  自 gcc-ada 包内 `bin/gcc` 签名包装器：它先查 `gcc.real
  -print-sysroot`（打包时 baked），再判定
  `$sysroot/usr/lib/aarch64-linux-ohos` 是否存在，不存在则直接
  exit 1——**所有** gcc 调用（含纯 `-c` 编译）都过不了。adacgi 只做
  `gnatmake -c` 且合入时 SDK 路径尚匹配，故未暴露；SDK 轮转后工具
  链整体失效，“原样使用 gcc-ada”假设被证伪。
- 新路线（与上轮“整体沿用 gcc-ada 调用方式”不同）：解耦两条调用
  路径——① C 胶水改用 profile C 编译器（HNP clang，
  `tools.build:compiler_executables["c"]`，ohos-aarch64 profile 保
  证存在），不再经过 gcc-ada 包装器；② 所有 gnatmake 调用前用只
  读探测选出本机真实可用 sysroot（含 usr/include + Scrt1.o 的首
  个候选；baked 值、clang resource-dir 推导、OHOS 环境变量、
  `ohos-sdk.org/*/ohos/native/sysroot` 版本 glob），写入
  `fixed-ohos-gcc/gcc` 垫片（直调 `gcc.real` 并显式
  `--sysroot/-B/-isystem/availability` 定义，复用包装器的
  link/compile 分类与 libunwind 注入逻辑），以
  `export PATH=<垫片>:$PATH &&` 前缀运行全部 gnat 命令。
  主配方与 test_package 同步修改（未提交）。探测全程打
  `[sysroot-probe]` 日志：成功则给出选中值，失败则如实报环境故障
 （含全部候选布局事实）走 infra 路由，不伪造通过。
- 真机证据：待 HMBS 预检验证（是否有效由下一次真机结果判定）。

## 第五轮修复（2026-09-26，新路线：不再假设 HNP 存在）

- 前次结果比较：上轮“fixed-ohos-gcc 垫片＋profile clang 编译 C
  胶水”已完整执行——真机用新探针给出了设备真相，直接证伪了上
  轮的两个隐含假设：① conf 钉死的 `/data/service/hnp/bin/clang`
  在该预检 runner 上根本不存在（`profile clang not found`）；
  ② baked sysroot 整棵树缺失（`include=False triplet_lib=False`，
  唯一候选即 baked 值本身）。因此上轮的 clang 直编与“必能发现
  sysroot”分支都走不通，`No usable OHOS sysroot` 成为首个新失败。
- 新路线（与上轮“SDK 必在某处、clang 必可用”不同）：对
  `/data/service/hnp` 做零假设——① build() 首步新增
  `_device_truth` 只读探针（conf 原值、HNP 祖先链存在性、HNP
  bin 列表、PATH 工具命中、常见 SDK 根、OHOS 环境变量、
  binutils 依赖存在性，全打 `[device-truth]` 日志）；② C 编译器
  改 `_select_c_compiler`：conf 值存在即用，缺失时经 PATH 发现，
  但每个候选必须过 `-dumpmachine` 双门禁（含 `aarch64` 且含
  `ohos`），杜绝 Linux host gcc 静默污染 libalog.a，无匹配则报
  明确环境故障走 infra 路由（已验证经验“profile 钉死编译器缺失
  时探测回退”的 Ada 场景适配）；③ 新增
  `binutils/2.46.0 tool_requires`（libgmpada/1.6 先例），as/ld/ar
  走 Conan 工具链包而非固定设备路径；④ sysroot 探测拓宽来源
  （多路 clang 推导、/opt SDK glob），找不到时返回
  `(None, None)`，垫片降级为直通模式（`-c` 可继续，链接失败则
  暴露为真实链接器错误而非包装器拦截）。
- 真机证据：待 HMBS 预检验证（是否有效由下一次真机结果判定；
  若宽探针仍无 SDK 痕迹，则如实判定为 runner 工具链缺失的环境
  故障，停止等待恢复）。

## 第六轮修复（2026-09-26：配方自身的源码布局假设错误）

- 前次结果比较：上轮工具链策略已逐项验证通过——真机日志显示
  shim 写入成功（sysroot 经 harmonybrew 的
  `Cellar/ohos-sdk/26.0.0.18_1/native/sysroot` 命中 triplet
  libdir）、binutils bindir 落定、harmonybrew clang
  （`aarch64-unknown-linux-ohos`，过双门禁）被选中、C 胶水
  `RUN: ... clang -c ... glue_syslog.c` 已执行无报错。新的首个
  失败是配方自身逻辑：`no compilable library units found`——
  `_library_units` 扫描了 source 根目录，而发布包解压后根下只有
  `src/tests/data/...` 子目录、零 `.adb` 文件（与 C 胶水路径
  `src/src/glue_syslog.c` 及 package() 从 `src/` 取 `*.ads` 的事实
  一致：可编译单元与 specs 同在上游 `src/` 子目录）。
- 改动（主配方，未提交；测试包无此函数无需同步）：`_library_units`
  改扫 `src/` 子目录（subunit 判定逻辑不变），空结果报错改为同
  时打印 `src/` 路径与根目录清单以便定位；另对 C 编译器候选做
  保序去重（conf 值与 HNP 路径相同时日志不再重复打印）。
- 真机证据：待 HMBS 预检验证（是否有效由下一次真机结果判定）。

## 第七轮修复（2026-09-27，新路线：--GCC 显式驱动，废弃 PATH 垫片）

- 上一方案为何无效：第六轮沿用了第四/五轮的“PATH 前缀垫片”假设——
  即 gnatmake 经 PATH 解析 gcc 驱动。上轮真机证伪了它：shim 写入成功、
  C 胶水（harmonybrew clang）编译通过、单元扫描修复生效，但首个 Ada
  编译 `gcc -c ... alog-active_logger.adb` 仍死于包装器报错
  `GCC Ada OHOS sysroot is unavailable: .../ohos-sdk_26.0.0.18/...`。
  该报错只存在于 gcc-ada 包内 `bin/gcc` 代理（ELF proxy →
  `gcc.ohos-wrapper` 脚本，先查 `gcc.real -print-sysroot` 的 baked 值再
  判定目录存在性，不存在则对一切调用直接 exit 1）；垫片自身从不打印此
  行，故失败调用走的是包装器而非垫片。根因：gnatmake 以绝对路径调用其
  同目录 sibling `bin/gcc`（不经 PATH 查找），`export
  PATH=<垫片>:$PATH &&` 对 Ada 驱动选择无影响（仅对 as/ld/ar 有效）。
  源码证据：`archives/g/gcc-ada/9.5.0/conanfile.py` `_install_driver_wrapper`
  （sysroot 检查 + exit 1）与 `_build_signed_shell_proxy`
  （bin/gcc 为相对定位 wrapper 的 ELF 代理）。
- 新路线（与此前三轮“PATH 拦截”不同）：不再依赖 PATH 拦截 gcc——
  ① `_ensure_gcc_shim` 改为返回垫片文件绝对路径并每次重写（build 目录
  可能被复用）；② 全部四处 gnatmake 调用（主配方 static 编译 + tests
  链接、测试包冒烟 + 上游重编）显式传递 `--GCC=<垫片>`（gnatmake 转发
  至编译/绑定/链接全程）；③ PATH 前缀降级为仅含 binutils（as/ld/ar），
  无目录时省略 export；④ 垫片链接分支加 `[ -n "$sysroot" ]` 守卫，修复
  直通模式下 `cd "$sysroot/.."` 误进 `/..` 的旧 bug。主配方与测试包同步
  修改（未提交）。
- 真机证据：待 HMBS 预检验证（是否有效由下一次真机结果判定；关键观察
  点是 gnatmake 命令行是否带上 --GCC 且 Ada 编译不再报 wrapper 拦截）。

## 第八轮修复（2026-09-27：链接阶段也绕行包装器）

- 前次结果比较：第七轮的 `--GCC=<垫片>` 已被真机证实有效——日志显示全部
  Ada/Ahven 编译（`.../fixed-ohos-gcc/gcc -c ...`，含 alog 各单元与 Ahven
  源）成功通过，C 胶水亦 OK。但首个新失败下移到链接阶段：裸
  `gnatlink .../test_runner.ali -O2 -o obj/test_runner ...` 再次触发
  `GCC Ada OHOS sysroot is unavailable`（`gnatmake: *** link failed`）。
  结论：gnatmake 不把自身的 `--GCC` 转发给其派生的 gnatlink（打印的
  gnatlink 命令行无 `--GCC` 即证据），故“只传 --GCC 即覆盖全程”的假设
  被证伪——本轮是同一原理向新失败点的延伸，而非重复旧修改。
- 改动（主配方与测试包同步，未提交）：`_ensure_gcc_shim` 在垫片同目录下
  额外生成 `gnatlink` 包装脚本（`exec <real-gnatlink> --GCC=<垫片> "$@"`，
  单 token 路径、无嵌套空格解析问题），返回 `(垫片, 链接包装)` 双路径；
  四处 gnatmake 命令统一追加 `--GNATLINK=<包装>`（与 `--GCC` 并列）。
  编译/绑定路径零变化。
- 真机证据：待 HMBS 预检验证（是否有效由下一次真机结果判定；关键观察点
  是 gnatlink 是否经包装调用垫片 gcc 并完成 test_runner 链接）。

## 第九轮修复（2026-09-27：垫片补传 gcc 私有库 -B 路径）

- 前次结果比较：第八轮的 `--GNATLINK` 包装已被真机证实有效——日志显示
  `gnatbind` 通过、`.../fixed-ohos-gcc/gnatlink ... -o obj/test_runner`
  已执行且 `gnatlink: error when calling .../fixed-ohos-gcc/gcc` 证明链接
  确经垫片调用 `gcc.real`。包装器拦截指纹至此彻底消失；新的首个失败是
  下游真实链接错误：`ld: cannot find crtbegin.o / cannot find -lgcc /
  cannot find crtend.o`（`collect2: error: ld returned 1`）。缺的恰是
  gcc 私有文件（sysroot 的 Scrt1.o 等未被抱怨），而垫片相对包装器正好
  少传了一面旗：包装器 `set -- "-B$package_root/lib/gcc/$target/$version/"`
 （源码证据：`archives/g/gcc-ada/9.5.0/conanfile.py`
  `_install_driver_wrapper` 末段）。编译阶段不需 gcc 私有目标文件故此前
  未暴露——这是新指纹，不是旧修改的重复。
- 改动（主配方与测试包同步，未提交）：`_ensure_gcc_shim` 从 `gcc.real`
  路径反推包根，枚举 `lib/gcc/aarch64-linux-ohos/*/` 选中含 `crtbegin.o`
  的版本目录（不硬编码 9.5.0），垫片追加 `pkg_gcc_lib` 变量与前置
  `set -- "-B$pkg_gcc_lib/" "$@"`（顺序与包装器最终旗序一致：包 -B 在前、
  sysroot -B 在后）；找不到则打明示 warning。诊断行
  `[shim] gcc private lib: ...` 随日志输出。
- 真机证据：待 HMBS 预检验证（是否有效由下一次真机结果判定；关键观察点
  是 test_runner 链接是否通过；若转报 libunwind 缺失或目标机 mismatch，
  按新证据再处理）。

## 第十轮修复（2026-09-27：test_package Ada 可见性，与工具链无关的新指纹）

- 上一方案为何无效/无需重复：第九轮的“垫片补传 -B 私有库路径”已被真机
  证实有效——本轮日志显示主配方 static 编译、test_runner 链接、签名、
  `upstream test_runner exit=0 passed=81 failed=0` 及
  `HMBS_UPSTREAM_TEST_RESULT ... passed 81/81` 全部通过，包装器拦截与
  crtbegin.o 缺失指纹均消失。同一工具链假设不可再沿用；首个新失败下移到
  test_package 冒烟程序编译：
  `alog_smoke.adb:80:47: operator for type "Ada.Directories.File_Size" is not
  directly visible`（`gnatmake compilation error`）。这是 Ada 语言可见性
  规则问题，与 sysroot/垫片/gnatlink 全无关——继续改垫片或 PATH 只会重复
  旧路线，违反“换路线”要求。
- 根因：`alog_smoke.adb` 仅 `with Ada.Directories` 而无任何 `use`，第 80 行
  `Ada.Directories.Size (Log_Name) > 0` 对私有整型 `File_Size` 使用 `>`
  操作符时该操作符不可见（GNAT 报错原文即建议 use clause；Ada RM 8.4：
  私有类型操作符需 `use type` 才直接可见）。上游库自身不受影响（其源码
  内部有正确的 use type），仅消费者冒烟程序写法触发，属配方测试代码 bug。
- 改动（仅测试代码，未碰工具链与测试口径，未提交）：`test_package/
  alog_smoke.adb` 在 `procedure Alog_Smoke is` 声明区追加一行
  `use type Ada.Directories.File_Size;`（使 `>`/`/=` 等操作符可见的最小
  规范写法；三断言逻辑与 `checks_passed` 输出零变化）。
- 真机证据：待 HMBS 预检验证（是否有效由下一次真机结果判定；关键观察点
  是 test_package `alog_smoke` 编译链接通过并输出 `checks_passed=3` 与
  `HMBS_TEST_PACKAGE_RESULT` 标记）。

## 第十一轮修复（2026-09-27：test_package 上游重编缺 up-obj 目录）

- 前次结果比较：第十轮的 `use type Ada.Directories.File_Size;` 已被真机证实
  有效——本轮日志显示 `alog_smoke` 编译链接通过且 `[ok] signed .../alog_smoke`
  成功，File_Size 指纹消失。首个新失败下移到同一 build() 内第二处 gnatmake：
  `gnatmake ... -D .../test_package/up-obj ... test_runner.adb` 报
  `gnatmake: cannot find object directory ".../up-obj"`（Error 4）。这是与上轮
  完全不同的目录准备问题：上轮修的是 Ada 语言可见性，本轮是 gnatmake `-D`
  要求目标目录必须预先存在（主配方 build() 内两处调用均有
  `mkdir -p obj/static-obj obj/static-lib` / `mkdir -p obj &&` 前缀，
  测试包第二处漏写）。重复改 Ada 源码无法触及该失败，故换路线。
- 根因：`test_package/conanfile.py` build() 第二个 `self.run` 直接以
  `-D <build>/up-obj` 调用 gnatmake，但从未 `mkdir -p` 该目录；
  全新 build 文件夹下该目录不存在即报上述错误（真机 RUN 行与报错行即证据）。
- 改动（仅测试包 build 命令，未碰工具链/断言/计数口径，未提交）：
  第二处 gnatmake 命令前加 `mkdir -p {obj} && `（与主配方 `mkdir -p obj`
  同模式；`{obj}` 仍为 `up-obj` 绝对路径）。
- 真机证据：待 HMBS 预检验证（是否有效由下一次真机结果判定；关键观察点
  是 test_runner 重编通过并输出双标记 `HMBS_TEST_PACKAGE_RESULT` 与
  `HMBS_UPSTREAM_TEST_RESULT 81/81`）。
