# xgamma 1.0.8 测试报告

构建主机：HarmonyOS PC aarch64（B 机）· 日期 2026-09-24 · Conan 2.29.1 ·
profile `ci/conan/profiles/ohos-aarch64`（`-pr:h` 与 `-pr:b` 同指该文件）

## 计数口径

- **逻辑用例** = `test_package/test_xgamma.sh` 的 `[test N/9]` 条目，脚本内
  `discovered=9`；执行器自己打出的汇总行为唯一实测口径
  （`[summary] discovered=… passed=… skipped=… failed=…`），不以"配方里有
  `self.run`"充当测试跑过。
- **断言点数 `N_assertion = 20`**，推导（在交付文件上直接可复算）：
  `grep -oE 'rc -(eq|ne) 0' test_xgamma.sh | wc -l` = **9** 处退出码判定，
  `grep -oE 'grep -qi? ' test_xgamma.sh | wc -l` = **11** 处输出串逐字判定
  （含 test 5 的嵌套边界串 `0.100` / `10.000` 两处），9 + 11 = **20**。
- **上游静态数 `N_static = 0`**：对解包后的官方 1.0.8 源码树行首锚定逐项统计，
  不是"构建系统未注册"就推断"上游没有测试"——
  `grep -cE '^[[:space:]]*assert\(' xgamma.c` = 0；
  `Makefile.am` 行首锚定 `TESTS`/`check_PROGRAMS`/`check-local` = 0；
  `meson.build` 行首锚定 `test(` = 0；`configure.ac` 无 `AC_CONFIG_TESTDIR`；
  `find -type d -name tests|test` = 0；`find -name '*_test.[ch]' -o -name 'test_*.[ch]'` = 0。
  另按"少报"四类资产补查：`demo/examples` 目录 0、`*RUNTEST*` 脚本 0、`*/res`
  语料目录 0；源码树子目录仅 `man/`。
  `Makefile.in` 第 824-825 行的 `check-am:` / `check:` 是 automake 无条件生成的
  样板规则、不含任何用例，故 `N_registered = 0`。
- 本报告不混用 runner 数与原子用例数：上游无 runner，故不存在该层。

## Results

| 环境 | 测试组 | Passed | Failed | Skipped | Assertions | 结果 | 证据（日志:行） |
|---|---|---:|---:|---:|---:|---|---|
| B 机 OHOS armv8 · `conan-verify` G2（`conan create`） | test_package 9 条命令行断言 | 9 | 0 | 0 | 20 | PASS | `reports/conan-create.log:167-231` |
| B 机 OHOS armv8 · `finish` W3 本地 CI 模拟 | test_package 9 条命令行断言 | 9 | 0 | 0 | 20 | PASS | `reports/w3-local-ci.log:432-496` |
| B 机 OHOS armv8 · `memcap-run.py --probe` 复跑 | test_package 9 条命令行断言 | 9 | 0 | 0 | 20 | PASS（本窗 `peak=9MB`；W4 审计同环境独立复跑 `peak=10MB` ⇒ 登记上界 10） | `notes.md`「峰值 RSS」 |
| B 机 OHOS armv8 | 上游 `make -n check` | 0 | 0 | 0 | 0 | N/A（上游无套件） | `reports/w3-local-ci.log:498` |

三次独立执行（verify / W3 / 探针）给出的 `discovered=9 passed=9 skipped=0 failed=0`
完全一致；W4 独立审计复刻同一运行期环境重跑交付版脚本是**第四次**，逐项同值
（`peak` 由 9MB 变 10MB，测试计数不变）。**上游表合计 0 ≤ 适配后合计 9**，
满足"适配后 ≥ 上游"。

## Raw evidence（逐条，行号为 W3 日志真实行号）

| # | 命令 | 断言的可观察行为 | W3 日志行 | 实测 |
|---|---|---|---|---|
| 1 | `xgamma -version` | 打印 `xgamma 1.0.8` 且退出码 0 | 432-434 | PASS |
| 2 | `xgamma --version` | 同上（长选项同分支） | 435-437 | PASS |
| 3 | `xgamma -help` | 打印 `usage:` 横幅且退出码 0 | 438-452 | PASS |
| 4 | `xgamma -nosuchopt` | `unrecognized argument` + 非 0 退出 | 453-469 | PASS（rc=1） |
| 5 | `xgamma -gamma 0.05` | 越 `GAMMA_MIN` 被拒，且错误串打印边界 `0.100` / `10.000` | 470-472 | PASS（rc=1） |
| 6 | `xgamma -gamma 99.0` | 越 `GAMMA_MAX` 被拒 | 473-475 | PASS（rc=1） |
| 7 | `xgamma -gamma 1.0 -rgamma 1.0` | `cannot set both -gamma and -rgamma` | 476-482 | PASS（rc=1） |
| 8 | `xgamma -gamma`（缺值） | `-gamma requires an argument` | 483-489 | PASS（rc=1） |
| 9 | 裸 `xgamma`（只读查询路径） | `unable to open display` + 非 0 退出 | 490-492 | PASS（rc=1） |

执行器汇总行原文：

```
w3-local-ci.log:494  [summary] discovered=9 passed=9 skipped=0 failed=0
w3-local-ci.log:495  OK: 9/9 checks passed, 0 skipped (no X server path)
w3-local-ci.log:496  HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_xgamma.sh","discovered":9,"passedCount":9,"skipped":0}
w3-local-ci.log:498  HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none",…,"discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,…}
```

第 9 条的实测输出逐字含上游格式的两个空格
（`xgamma:  unable to open display ''`），本轮该机 `DISPLAY` 未设置、无可达 X
server，故该条**真实执行**而非跳过（`skipped=0`）。

## 构建真实性与预下载（防"缓存命中伪装成验证通过"）

| 判据 | 实测 |
|---|---|
| `Building from source` | `w3-local-ci.log:208` 命中 1 次（`grep -c 'Building from source'` = 1） |
| `Calling build()` | `w3-local-ci.log:218` 命中 1 次（`grep -c 'Calling build('` = 1）；其上 `:207` 为 `Installing package xgamma/1.0.8 (9 of 9)`、其下 `:215` 为 `Generators folder:` |
| `- Cache` 归属（w3） | `grep -c -- '- Cache' reports/w3-local-ci.log` = **45**；其中属 xgamma 的三条是 `:167`、`:378`（**配方 revision 级**条目，不含二进制 id）与 `:398`（`:208` 那次编译完成并打包**之后**的再安装），其余 42 条属依赖包（libx11/libxxf86vm/…）⇒ 无一条表示"本包没编译" |
| Pre-download 步骤 | `w3-local-ci.log:99` 启动、`:103` 完成（2 个文件），`:527` 结束还原为官方 URL |
| `conan create` 日志（**不可作真编译证据**） | `reports/conan-create.log` 实测 `grep -c 'Building from source'` = **0**、`grep -c 'Calling build('` = **0**、`grep -c -- '- Cache'` = **44**；其 `:63`/`:84`/`:113`/`:133` 行把 `xgamma/1.0.8@ohpcd/stable`（含二进制包 id）明确列为 `- Cache`、`:97`/`:146` 为 `Already installed! (7 of 7)` ⇒ 该日志是 `conan test` 复跑、**被测二进制恰恰命中缓存**，与"非缓存真编译"结论相反。它的有效用途只有一个：证明 test_package 断言可重放（测试段 `:167-231`、汇总行 `:229`）。旧版本本节把"1 次 / 1 次 / 45 处全属依赖"归给该文件属引用错位，已订正为 `w3-local-ci.log:208 / :218` |
| 证据适用边界 | 两份日志的 `grep -c 'Calling source'` 均为 **0** ⇒ conan 复用了已有源码目录，上表判据只支撑"**编译 / 链接 / 测试真实执行**"，**不**支撑"源码按 conandata 重新获取"；后者由 `notes.md`「最终方案」的两条官方 URL 取证 + 独立 `curl`/`cmp`/`sha256sum` 支撑（见本文件「Integrity」节），两件事不互相顶替 |
| 交付版 conandata | 构建期被框架改写成本地路径属正常副作用，退出时还原；本轮 md5 前后一致（`2140c0a8…`），且 `grep -Ec 'file://\|gh-proxy\|ghfast'` = **0** |

### 降级项（框架侧既存口径，未执行不并入通过、分母不删）

| 判据 | 实测位置 | 客观说明 |
|---|---|---|
| L2 smoke test 跳过 | `w3-local-ci.log:511` `[warn] L2: xgamma --version/--help failed (non-blocking)` → `:515` `L2_RESULT=skip: xgamma version/help failed` | 框架 smoke test 的判据是**裸跑** `xgamma --version` / `--help`（不带 test_package 的 LD_PRELOAD/LD_LIBRARY_PATH 运行库注入），该机取不到 `libXxf86vm.so.1` 故失败；与本报告第 2 条断言（同一二进制、带运行期注入、`:435-437` PASS）不是同一执行条件。非阻塞项，本包不改框架、不把 L2 记为通过 |
| L1c 样板输出 | `w3-local-ci.log:503` `[ok] L1c: Upstream official tests (make check/ctest) executed in build phase` | 该行判据只是"构建阶段跑过 make check"，不代表存在用例：同一日志 `:498` 的 `HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",…,"discovered":0,"executed":0,…}` 才是本包真实上游测试状况（0 用例），与 `test_package/MANIFEST.yml` 的 `upstream_tests_exist: false` 及账本 `N_static=0 / N_registered=0` 一致 ⇒ L1c 的 ok **不可**读作"上游有测试被执行" |

## Not covered（未覆盖，不计入通过、也不从分母静默删除）

gamma 的**服务端往返**路径：`xgamma.c` 第 209-228 行
`XF86VidModeQueryVersion` / `QueryExtension` 版本门、第 230-235 行
`XF86VidModeGetGamma`、第 252-265 行 `XF86VidModeSetGamma` 与读回打印。**未执行，
原因两条**：

1. **环境不具备**：需真实 X server 且服务端加载 XFree86-VidModeExtension >= 2.0；
   构建机 `DISPLAY` 未设置、`/tmp/.X11-unix` 不存在，该路径无法执行（第 9 条断言的
   实测输出 `unable to open display ''` 正是这一前提的直接证据）。
2. **安全红线主动不执行**：xgamma 会修改真机 gamma，而构建机是用户正在使用的机器。
   规则要求"读法或等价型"且调用后立即读回断言恢复；本包裸执行路径经源码可证**只读**
   （第 245-249 行 `/* Not changing gamma, all done */ … goto finish` 跳过第 252 行
   SetGamma），已在第 9 条覆盖；而**写入**分支一旦执行就会留下显示状态副作用，
   故主动不执行，也不并入通过。

因此本包的能力边界是"参数解析与取值域判定 + 只读查询"，
**GUI/服务端副作用写入路径未覆盖**。

## Integrity

- 官方包 sha256：`96ab71ea6a6791538324bb4d2014627816d83178a0ac79335d8c9ef25ce59f1d`
  （170632 字节 gzip）。**本轮未因任何构建期报错改动过一个字符。**
- 源码 URL：`xorg.freedesktop.org/pub/individual/app/xgamma-1.0.8.tar.gz`（主）与
  `xorg.freedesktop.org/archive/…`（兜底）。两条均为 x.org **官方主机的官方路径**，
  实测返回**字节完全相同**的同一个官方包；不含镜像/代理前缀（R39）。选 `/pub/`
  为主的理由是它不命中 CI 预下载"镜像优先 + 不校验状态码"的改写正则 —— 取证与
  失败方案见 `notes.md`「W3 预下载把 x.org 源换成死镜像」一节。
- 上游源码与测试文件：**未修改**（`patches_applied: []`，0 补丁）。
- 验证命令：
  `python3 scripts/ohc-run.py conan-verify xgamma 1.0.8` → G0/G1/G2/G3/G4 全 PASS、RC=0；
  `python3 scripts/ohc-run.py finish xgamma 1.0.8 built` → W3 `.ci-result.json` `exit_code: 0`。
- W3 判决文件：`step=W3_local_ci`、`timestamp=2026-09-24T02:50:17.736028`、
  `exit_code=0`、`integrity_hash=649a85bf6fb9777d`、
  `log_sha256=9fb840d98b68695ef013392d57eb11da04f9a220fd1a7b8c279c9511d57c2f4d`。
  注：`conandata.yml` 的 mtime（02:50:17.688）是 `finish` 退出时把构建期被改写的 URL
  还原为官方 URL 所致，**最后一次人工改动早于该时刻**，内容 md5 与部署时一致。
- 资源占用（手册/05 ⓓ，`memcap-run.py --probe` 实测）：同一交付版套件**两次独立实测**
  —— 本窗 `MEMCAP[probe] peak=9MB budget=0MB rc=0`；W4 独立审计在同一台 B 机复刻同一
  运行期环境重跑得 `peak=10MB budget=0MB rc=0`，两次的
  `[summary] discovered=9 passed=9 skipped=0 failed=0` 逐项相同。差 1MB 属 `--probe`
  采样间隔抖动 ⇒ **`max_rss_mb` 登记取观测上界 10**（`manifest.yaml` /
  `test_package/MANIFEST.yml` / `notes.md` / 本文件四处同值），不以单点 9 当硬上界；
  单条进程 1-2MB。xgamma 不接受输入文件，输入规模恒为 0，故 `--scale` 取 1、不外推。
- 五维账本同源：`N_static=0` / `N_registered=0` / `N_executed=9`
  （通过 9 · 失败 0 · 跳过 0 · disabled 0）/ 未执行分类见上 /
  `N_consumer=9`（`N_assertion=20`）——同值写在
  `notes.md`、`test_package/MANIFEST.yml`、`manifest.yaml`、本节与回报五处。
