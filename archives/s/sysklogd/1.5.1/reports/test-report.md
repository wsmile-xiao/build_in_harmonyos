# sysklogd 1.5.1 verification report

本报告全部数字来自真机读数；每一节都给出可回查的日志路径或可复算的字段。**未实测的项目显式写"未实测"，不并入通过数。**

## Environment

- 设备：HarmonyOS PC（aarch64），构建主机 A 机
- conan：2.29.1；profile：`ci/conan/profiles/ohos-aarch64`（`-pr:h` 与 `-pr:b` 同值 ⇒ 非交叉注入路径）
- `CONAN_HOME`：`~/tmp/ch/home-主理-9-sysklogd`
- 上游源：`https://www.infodrom.org/projects/sysklogd/download/sysklogd-1.5.1.tar.gz`，`sha256 5166c185ae23c92e8b9feee66a6e3d0bc944bf673112f53e3ecf62e08ce7c201`，90011 B（真实下载算得，与 `conandata.yml` 声明一致）
- 语言 / 构建系统：C；**纯 Makefile**（tarball 内无 `configure`/`configure.ac`/`Makefile.am`）

## Gates

| 门禁 | 结果 | 凭据 |
|------|------|------|
| W0 `preflight_check.sh sysklogd/1.5.1` | RC=0，`[OK] 预检通过（无依赖需要检查）` | 本包无 Conan 依赖（`deps: []`） |
| W2 结构 / 补丁声明 | 通过：6 条补丁声明于 `conandata.yml` 并在 `build()` 内 `apply_conandata_patches` 真实应用；`manifest.patches_applied` 与盘上 `patches/*.patch` 计数一致 | `git grep` 于 HEAD；补丁头部无 `2000-01-01` 伪时间戳、新增行 `__OHOS__` 命中 `0×6` |
| W3 `conan create` + 本地 CI 模拟 | **通过**：`ohc-run.py finish` 输出含「W3 本地 CI 模拟通过」，`.ci-result.json` = `step: W3_local_ci, exit_code: 0` | `archives/s/sysklogd/1.5.1/.ci-result.json`、`1.5.1/reports/w3-local-ci.log` |
| W4 独立审计（第 2 轮，只读代理） | **PASS**：`P0=0 / P1=0 / P2=1 / P3=10`，`REPORT_RC=0` | 判决件 `1.5.1/reports/audit-result.json`（由独立审计代理撰写），findings `~/tmp/uc2/zhuli-10-sysklogd-r2/findings-r2.md` |
| rule5 diff 白名单 | 通过：变更仅 `archives/s/sysklogd/**` + `knowledge/drafts/DRAFT-sysklogd-1.5.1-*` | 见 PR 的 diff 清单 |

`.ci-result.json` 的两个防伪造字段可本地复算：`integrity_hash == sha256("<timestamp>:sysklogd:1.5.1:0").hexdigest()[:16]`（本次为 `a53a8632b41a22db`），`log_sha256 == sha256(reports/w3-local-ci.log)`（本次为 `704cf1d9db93e5862c4b8c1f97984e22ac9685705c2b69e7387d721b24b17d8d`）⇒ 该文件由 `finish` step[5/10] 产出，非手写。

## Which HEAD the build evidence is bound to

- 本报告对应的 `finish` 与 W3 读数产生于 **HEAD `d84984348e`**（分支 `feat/sysklogd-1.5.1`，与远端逐字一致）。
- W4 判级亦绑定 `d84984348e`；审计输入 `~/tmp/uc2/zhuli-10-sysklogd-r2/audit-input-r2.json` 经逐文件比对：`git show HEAD:<f>` 的 md5 与输入内 `file_contents` **17 文件全等、0 mismatch**。
- 该 HEAD 之后的提交只包含：`reports/audit-result.json`（判决件，按仓内先例 `git add -f`）、本 `test-report.md`、软件级 `archives/s/sysklogd/README.md`，以及 `finish` 自身刷新的元数据（`notes.md` 尾部"编译结束/最终状态"块）。**不改构建逻辑、补丁内容与测试断言。**

## Packaged artifacts

- 包内文件 **10 个**（由独立审计代理以 `conan cache path` 定位已打包目录后 `find <pkg> -type f` 实测）
- `sbin/syslogd` **55744 B**、`sbin/klogd` **43392 B**
- 二者均为 `ELF arm64 dynamic not stripped`
- 包内直接执行：`syslogd -v` → 输出 `syslogd 1.5.1`、**RC=0**；`klogd -v` → **RC=1**，此为非失真：pristine 上游 `klogd.c:1030-1032` 的 `-V` 分支本身就 `exit(1)`，`test_package/test_runner.sh:81-88` 按 `rc=1` 判定该断言通过
- ⚠ `conan-verify` 的 **G4 属降级 PASS**（`scripts/ohc/conan_verify.py:737` 仍按旧三层缓存结构取 package ID，在 conan 2.29.1 下打印「无法找到程序包 ID」却记 PASS、L2/L4/L5 跳过）⇒ **本节不把 G4 当独立产物证据**，上面四件为手工补验（先例 E478）

## test_package

- 消费者程序 1 个 + `test_runner.sh` 的 **13 条断言**
- 实测：**12 通过 / 1 SKIP / 0 失败**，`SUMMARY checks=13 failures=0 skips=1`、`VERDICT=PASS`
- 独立复跑（与 CI 逐字同参数 `-pr:h/-pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --build="sysklogd/*"`）：`conan create` **RC=0**，产生新包 id `6b129b068851896169fae42d399fa922d239ce8a`，日志 `~/tmp/uc2/zhuli-10-sysklogd-r2/conan-create-r2.log`（含 `Building from source` + `Calling build()` + 真实 clang 编译行，非缓存假绿灯）
- SKIP 的那 1 条 = `klogd` 运行期内核日志读取：需 `CAP_SYSLOG`，且 pid 文件路径在编译期固定 ⇒ 本设备不满足前提，记 SKIP 不并入通过

## Test ledger (rule4 / R51：声明数必须 ≤ 实测数)

| 维度 | 数量 | 依据 |
|------|------|------|
| 上游测试用例（静态，分母） | **5** | 上游 `Makefile:78` 注册的 `test` 目标一次产出 4 件（`syslog_tst`、`ksym`、`oops.ko`、`tsyslogd`），另计 `tklogd`（`-DTESTING` 变体）⇒ 按"宁高勿低"申报 5；注册口径为 `make test = 1 目标 / 5 产物` |
| 上游可执行数 | **0** | 见下逐项原因，全部为具体环境限制而非"跳过即通过" |
| 适配后新增断言（`test_package`） | 13 | 实测 12 通过 / 1 SKIP / 0 失败 |
| 失败 | 0 | — |

上游 5 项逐项不可执行原因：

1. `oops.ko`：需构建外部内核模块。设备 `ls /lib/modules` **RC=1**、`/usr/src` 不存在 ⇒ 无内核构建树；HarmonyOS PC 亦不加载未签名外部 `.ko`。
2. `ksym`：依赖内核符号来源。**其运行期前提未实测** ⇒ 本报告按"未实测"处理，不预设结论。
3. `syslog_tst` / 4. `tsyslogd`：运行需 `/dev/log` 与真实 syslog 通道 ⇒ 无头环境不具备。
5. `tklogd`：`-DTESTING` 变体，同上受 `CAP_SYSLOG` 与 pid 路径限制。

## Known limitations of this delivery

1. `klogd` 的运行期内核日志读取未在本平台真机验证（`CAP_SYSLOG` 前提不成立）⇒ 对应断言记 SKIP。
2. `G4` 为工具降级 PASS（见上），包内容真实性改由手工 `find`/尺寸/ELF 判读/包内执行支撑。
3. `conan-verify` 的 L2（平台功能 smoke）、L4（checksec）、L5（产物基线）在本报告口径下**未实际执行**（`ohc/conan_verify.py` 的 cache 路径问题导致跳过），不作为安全或基线结论。
4. `packaging/` 与 `.staging-verified` 由流水线在建 PR 前生成，不入本 PR。

## Result

**W0 / W2 / W3 / W4 全部通过**（W4 第 2 轮 `P0=0 / P1=0`）；测试口径为 **上游分母 5 / 可执行 0 / 新增 13 断言 12 通过 + 1 SKIP / 失败 0**，声明数与实测数同源。
