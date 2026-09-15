# notes.md — combat/0.8.1 移植笔记（OHOS aarch64 / musl / clang）

## 1. 上游与源码

- Combat 0.8.1 = "Combat — CORBA Scripting with Tcl"（Frank Pilhofer），
  2011-08-01 发布，为最终版本（0.8 起退役 Combat/C++，本体纯 Tcl）。
- 上游原站归档仅 HTTP 且证书 SAN 不匹配；采用 Debian 源码池同一 orig 归档：
  `https://deb.debian.org/debian/pool/main/c/combat/combat_0.8.1.orig.tar.gz`
  SHA256 `1923fa19f55a03f720f0444d6edffe7dad246c2c4be82453b8d2c5b4922d99a8`
  （设备侧下载复核一致，归档顶层目录 combat-0.8.1/）。
- License：TCL（LICENSE.txt，与 Tcl/Tk 自带许可同款宽松条款）。

## 2. 包结构（打包布局）

```
<pkg>/bin/{idl2tcl,iordump}        sh/Tcl 双语包装脚本
<pkg>/lib/combat/                  orb/*.tcl + pkgIndex.tcl（combat 0.8）
<pkg>/lib/combat/itcl/             Itcl 4.3.2 分发（见 §4）
<pkg>/lib/tclkill/                 pkgIndex.tcl + kill.so + unixkill.tcl
```

放在 lib/ 下使 CI L1e 破坏性负测试可真实命中产物（bin/、lib/ 被移走后
test_package 必然失败）。

## 3. 补丁（3 个，全部最小可解释）

1. `0001-insert-tclsh-8.6-probe.patch`（24 个文件）：入口脚本为 sh/Tcl
   双语 polyglot，上游硬编码 `tclsh8.5` 探测。按上游自身模式（注释行以
   `\` 结尾续行、无反斜杠的 if 行既是 sh 语句又是 Tcl 注释块终结）插入
   `tclsh8.6` 探测分支，保留上游 8.5/cygwin 分支不变。
   注意：`sh -n test/1/dotest` 在未打补丁的上游文件上同样报语法错误
   （polyglot 尾部 Tcl 代码不是合法 sh），非本补丁引入。
2. `0002-orb-combat-bundled-itcl.patch`：combat.tcl 在 `package require
   Itcl` 前优先 `lappend auto_path [file join [file dirname [info script]] itcl]`，
   发现随包分发的 orb/itcl/（见 §4）。
3. `0003-tclkill-generic-kill-so.patch`：tclkill/pkgIndex.tcl 按平台名探测
   预编译 kill-<plat>-<mach>.so；OHOS 上 `tcl_platform(os)=HarmonyOS` 算出
   的名字（kill-h-aarch64.so）不存在。补丁在其后追加覆盖：存在通用
   kill.so（本 recipe 编译）则优先使用，否则维持上游平台探测/unixkill 回退。

## 4. Itcl 是事实上的硬依赖（关键发现）

- combat.tcl 在 Itcl 缺失时回退 `package require tcl++`，但 **0.8.1 归档
  并不携带 tcl++**（全树检索无 `package provide tcl++`）→ 无 Itcl 则
  `package require combat` 直接失败。Scout 阶段"有纯 Tcl tcl++ 回退"
  的判断需修正。
- tcl/8.6.16 已发布包的 `lib/itcl4.3.2/` 只有 libitcl4.3.2.so + stub 静态
  库（其 recipe 按 `*.so*`/`*.a` 通配拷贝，未收录 Itcl_Init 必需的
  itcl.tcl/itclHullCmds.tcl/itclWidget.tcl）；裸 load 报
  "Can't find a usable itcl.tcl"。
- 解决（本包自包含，不改动 tcl 包）：从与已发布 .so 同源同版本的 Tcl
  8.6.16 源码包（URL/SHA256 与 tcl recipe conandata 相同，URL 可达性已被
  该包 CI 验证）提取三个库脚本，随包放入 `lib/combat/itcl/`，并生成
  pkgIndex.tcl：load 前设 `ITCL_LIBRARY` 指向该目录（Itcl_Init 按编译期
  前缀与环境变量查库脚本）。消费者 `package require combat` 零额外配置。
- 独立 itcl 发行包两个 URL 均失效（sourceforge 404、core.tcl-lang.org 无
  uv/itcl4.3.2），故取自 Tcl 源码包内置 pkgs/itcl4.3.2（版本严格一致）。

## 5. tclkill 扩展编译

- 设备 clang + `-DUSE_TCL_STUBS -I<tcl>/include kill.c libtclstub8.6.a
  -Wl,-z,now`（stubs 静态链 → kill.so 无对 libtcl8.6 的 DT_NEEDED；
  BIND_NOW 对齐 musl 约束）。实测 load 后可对真实子进程发 SIGTERM。
- 若无 kill.so，上游 pkgIndex 回退 `unixkill.tcl`（exec kill），功能等价。

## 6. test_package（真实 IIOP 回环）

`test_combat.tcl`：以 server 模式 spawn 子进程（`corba::init -ORBHostName
127.0.0.1` 消除主机名解析差异），RootPOA activate 后写 server.ior；客户端
`string_to_object` 后做 long 属性写读往返（42 / -1234567），再用 kill 扩展
回收服务端。conan create（CI 同参数）实测 4 项 PASS。

## 7. 上游测试真实运行结果（设备实机，TCLLIBPATH 指向 conan 打包产物）

按上游 `test/Makefile` 的 TESTDIRS 集合运行 1,2,3,4,5,6,7,10,11
（8=上游未实现 DSI，9=需外部 COS Naming Service，README.txt/Makefile 双证）。

口径（自洽闭合）：9 个目录共定义 192 个用例 = 执行 187 + 上游 `{knownBug}`
标记静默跳过 5（均为 pristine dotest 自带标记，非本 run 添加）；执行
187 = 通过 186 + 失败 1（async-1.2）。tcltest 以 `-verbose {body error
pass}` 运行（上游 dotest 原样），skip 不打印日志行。

| 目录 | 定义 | 通过 | 失败 | 说明 |
|---|---|---|---|---|
| test/1 | 35 | 31 | 0 | ptypes-1.3/2.3/3.3/4.3 为 pristine test/1/dotest 自带 knownBug 标记（L66/81/98/113）被 tcltest 跳过（上游范围检查未实现） |
| test/2 | 28 | 28 | 0 | |
| test/3 | 12 | 11 | 0 | unions-1.4 为 pristine test/3/dotest 自带 knownBug 标记（L93）被 tcltest 跳过（上游范围检查未实现，同上） |
| test/4 | 24 | 24 | 0 | |
| test/5 | 22 | 22 | 0 | |
| test/6 | 9 | 8 | 1 | **async-1.2 失败**（见下） |
| test/7 | 24 | 24 | 0 | |
| test/10 | 21 | 21 | 0 | |
| test/11 | 17 | 17 | 0 | |
| 合计 | 192 | 186 | 1 | 187 执行 + 5 上游 knownBug 跳过；187 = 186 过 + 1 败 |

**async-1.2**（parallel sleep，多 ORB -async 并行请求 + request wait/get）：
`corba::request get` 抛 `IDL:omg.org/CORBA/BAD_PARAM:1.0 COMPLETED_MAYBE`
（pristine orb/orb.tcl `get_async_reply` 的 `reqids_completed` 查询未命中
该 aid）。原始执行 + 2 次留痕复跑（rerun1/rerun3，共 3 次执行）均确定性
复现。移植回归排除依据（异步路径触及面核验）：
本 run 三个补丁均不触及异步/GIOP 机制——0001 为 24 个入口脚本的解释器
探测行、0003 仅 tclkill/pkgIndex.tcl；orb 内唯一改动是 combat.tcl 的 Itcl
发现 2 行（补丁 0002），不在异步路径上。该用例为三路并行 sleep 2/1/0 +
wait/get 竞态结构，疑似与 Tcl 版本计时/事件循环差异或设备回环时序相关
（上游按 Tcl 8.5 验证；设备无 Tcl 8.5 可 A/B 对照，归因未做验证）；
test/README.txt 的已知失败说明未收录该用例，属上游未文档化缺陷。

## 8. 风险与已知限制

- 消费者契约：Tcl 侧需 `lappend auto_path $COMBAT_ROOT/lib/combat
  $COMBAT_ROOT/lib/tclkill`（与上游 auto_path 用法一致）；
  `COMBAT_ROOT` 由 runenv 提供。
- bin/iordump、idl2tcl 需 tclsh8.6 在 PATH（由依赖 tcl 包的 runenv PATH
  提供）；iordump 的"兄弟 orb/ 目录"自动发现仅在上游源码树布局生效，
  打包布局下依赖 auto_path/环境（已在其 usage 与 README 说明）。
- L2 smoke 对 iordump/idl2tcl 的 `--version/--help` 为非阻塞 warn
  （两工具无该选项，usage 退出码 1）。

## 9. 验证记录

- conan create（CI 同参：-pr:h/-pr:b ohos-aarch64、--build=missing、
  --build=combat/*）：PASS（test_package 4 项 PASS）。
- 权威 CI `ci/conan/build_and_test.sh archives/c/combat/0.8.1`：
  见 run 日志 `/storage/Users/currentUser/tmp/oh-device-porting-v2/combat-0.8.1/ci-run1.log`。
- 上游测试日志：`/storage/Users/currentUser/tmp/oh-device-porting-v2/combat-0.8.1/upstream-logs/`。
