# 测试报告 — trojan 1.16.0

> **项目**: trojan 1.16.0（HTTPS 代理，server/client 一体）
> **测试日期**: 2026-09-21（首次全链）/ 2026-09-25（CI 失败修复后强制重建复验）
> **测试环境**: HarmonyOS PC（aarch64-linux-ohos，OHOS SDK 26.0.0.18，clang 15.0.4，conan 2.29.1 OHOS 适配版）
> **测试类型**: 上游注册测试（`add_test`/`ctest` 等价形式，`build()` 内实跑）+ 消费者测试（conan test_package）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游静态注册测试（CMake `add_test`） | 2 | 100% 已执行 |
| 上游可执行测试入口 | 2 | 100% |
| 通过 (PASS) | 2 | 100% |
| 失败 (FAIL，修复后复验) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |
| 消费者测试检查链 | 1 条链 / 5 个检查点 | 100% |

**核心功能通过率**: ✅ **2/2 上游测试 + 5/5 消费者检查点（100%）**

> 上游 `CMakeLists.txt`（L124–128，非 Windows 分支）`enable_testing()` 后注册
> `LinuxSmokeTest-basic` 与 `LinuxSmokeTest-fake-client` 两条测试，COMMAND 均为
> `bash tests/LinuxSmokeTest/<脚本> <构建目录>/trojan`。本配方在 `build()` 内以
> `self.run()` 逐脚本直跑，命令形式与 `add_test` 的 COMMAND 一致（同一 bash 调用、
> 同一二进制参数），任一脚本非零退出即 `conan create` 中止。

---

## 二、测试结论

### 2.1 总体评价

✅ **通过** — 上游两条端到端冒烟与消费者 TLS 握手链全部通过；产物（`bin/trojan`、
示例配置、man 页、文档）齐全。历史 CI 失败（2 次，根因单一）已修复并复验。

### 2.2 历史失败与修复（如实记录）

| # | 环境 | 现象 | 根因 | 修复 |
|---|------|------|------|------|
| 1 | CI worker CI-008（PR #11779 构建 #60109，2026-09-24 21:57） | `build()` line 82 `ConanException: Error 1`，smoke 无输出即退出（106.8 s） | CI worker PATH 中无 coreutils `yes`（其基础 PATH 仅 `/data/app/bin:/system/bin:/system/sbin:/vendor/bin:~/.local/bin`；同日志 pre-download 阶段 9 次报 `No such file or directory: 'curl'` 佐证该镜像用户级工具稀疏） | 0002 补丁：`-subj/-batch` 显式给 DN + `-batch`，删除 `yes` 依赖 |
| 2 | CI worker CI-015（构建 #60185，2026-09-24 22:45） | 同型失败（67.5 s），排除单 worker 偶发 | 失败链条：`yes '' \| openssl req` → `yes: command not found`（stderr 被 `exec 2>>test.log` 吞入 scratch）→ `openssl req` DN 交互提示遇已关闭 stdin → `Error making certificate request` → `set -eu` 退出 1 | 同上，另加 `ERR` trap 回显 test.log 尾部到 stdout（失败从此可见）与 `wait_port` 60 s 超时（服务死时快速失败，不再挂满 14400 s CI 预算） |

**根因实证（A 机对照实验，2026-09-25）**：构造与 CI 同构的无 `yes` PATH（含
openssl/mktemp/curl/python3/bash，无 yes），复刻 `yes '' | openssl req -x509 ...`：
组 1（无 yes）rc=1，test.log 内 `yes: command not found` + `Country Name (2 letter
code) [AU]:Error making certificate request`，cert.pem 未生成；组 2（有 yes）rc=0，
cert.pem/key.pem 均生成。CI 判决特征（快速失败、唯一 stdout 为 scratch 目录名、
双 worker 同挂）与该链条完全吻合。

### 2.3 可用功能清单

```
✅ trojan 服务端/客户端（SOCKS5 代理 + TCP forward 两种 run_type）
✅ TLS 传输层（conan openssl/3.5.8.1，s_client 握手 Verify return code: 0）
✅ 配置校验入口 `trojan -t`（server/client/forward/fake-client 四种配置均过）
✅ 版本入口 `trojan -v`
✅ 纯 TLS 客户端拒绝（fake-client 负路径断言）
✅ 回环组网端到端（自签证书 → python3 http.server 假源站 → trojan → curl 取回 whoami）
```

### 2.4 已知限制

1. 冒烟脚本曾依赖 coreutils `yes`（上游原样），CI 镜像无此工具——已由 0002 补丁
   消除依赖，`-subj '/CN=trojan-test' -batch` 非交互出证。
2. 冒烟绑定回环端口 10080/10081/10443/11080/20081；配方串行执行两脚本并在各脚本
   末尾 `kill -KILL` 清理，若 CI worker 同刻跑同包构建仍可能端口冲突——`wait_port`
   已加 60 s 超时，冲突时快速失败而非挂起。
3. `N_consumer` 为补全测试（上游无消费者测试包），按 R34 真实依赖被测包：起包内
   server 并完成真实 TLS 握手。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 上游注册名 | 功能 | 结果 | 证据出处 |
|--------|-----------|------|------|---------|
| tests/LinuxSmokeTest/basic.sh | `LinuxSmokeTest-basic` | 自签证书 → 假源站(10081 true/10080 fake) → trojan server(10443)+client(11080)+forward(20081) → `curl --socks5` 经代理取回 whoami=true → `curl` 直连 20081 取回 whoami=true | ✅ PASS (exit 0) | `reports/conan-create.log` L205–208（2026-09-25 复验，scratch `trojan-smoke.VDGoSx`）；历史：`.ci_logs/conan_build_trojan_1.16.0.log` L186–187 |
| tests/LinuxSmokeTest/fake-client.sh | `LinuxSmokeTest-fake-client` | 同组网；断言纯 TLS 客户端直连 10443 取不到真源站内容、fake 路径(20081→fake)返回 fake | ✅ PASS (exit 0) | `reports/conan-create.log` L210–211（scratch `trojan-smoke.7G56AC`）；历史：同日志 L189–190 |
| test_package/test_tls.sh（消费者，补全） | —（上游无 test_package） | ① 二进制存在可执行 → ② 自签证书生成非空 → ③ `trojan -t server.json` 配置校验 → ④ 起包内 server → ⑤ `openssl s_client` 握手断言 `Verify return code: 0` | ✅ 5/5 检查点 | `reports/conan-create.log` 尾行 `trojan TLS wire behavior verified on 127.0.0.1:10443`（并 L205 `Built target trojan`） |

### 3.2 失败的测试

无（修复后复验，2026-09-25 `conan-verify` G1/G0/G2/G3 全 PASS，强制重建缓存后
`conan create` 全链 58.1 s，MEMCAP peak=576MB budget=2500MB rc=0）。

历史失败见 §2.2——两次 CI 失败均为冒烟脚本环境依赖问题（非被测功能缺陷），修复
后于 A 机以「CI 同构无-yes 环境」复验修复有效（harness：证书步通过，trap 在后续
人为失败点准确回显首错）。

### 3.3 跳过的测试

无。上游注册的全部测试（2/2）均已执行。

---

## 四、关键问题分析

### 问题1: CI 冒烟 `exit 1` 且无任何错误输出（本轮修复核心）

**现象**（PR #11779 两次 CI 判决，构建 #60109/#60185）：`[100%] Built target
trojan` 后冒烟仅打印 scratch 目录名（`trojan-smoke.cNfJpB` / `trojan-smoke.labIaH`）
即 `ConanException: Error 1 while executing`（conanfile.py line 82，即 `self.run`
basic.sh 处），fake-client.sh 未被执行；判决摘录无 smoke stdout，平台 logTail 空。

**根因分析**：basic.sh/fake-client.sh 起手 `exec 2>> test.log` 把后续全部 stderr
吞入 scratch 内的 test.log（CI 环境销毁后不可取）；上游证书生成写法
`yes '' | openssl req ...` 依赖 coreutils `yes`——CI worker 镜像没有该工具
（`/system/bin` 等系统目录为空布局 + 用户级 bin 稀疏，同判决 pre-download 9 次
`No such file or directory: 'curl'` 佐证）。`yes` 缺失后 openssl req 进入 DN 交互
提示并遇已关闭 stdin，`Error making certificate request` 退出 1，`set -eu` 终止
脚本。A 机对照实验完整复现该链条（见 §2.2）。

**解决方案**（patches/0002-tests-LinuxSmokeTest-smoke-nointeractive.patch）：
1. 证书生成改 `openssl req -x509 ... -subj "/CN=trojan-test" -batch` +
   `export OPENSSL_CONF=/dev/null`（与消费者测试 test_tls.sh 同款，顺带规避 conan
   openssl 制品内嵌悬空 OPENSSLDIR 问题，见 notes.md 问题 #3）；
2. 两脚本 `exec 2>> test.log` 后设 `trap 'dump_log $LINENO' ERR`，失败时
   `tail -n 40 test.log` 到 stdout——CI 判决自此可见首错；
3. `wait_port` 加 60 s 超时（600×0.1 s），服务死时 `return 1` 快速失败；
4. 断言失败的 else 分支加显式 stdout 提示行。

### 问题2: 上游冒烟在 OHOS 构建镜像的移植性（0001，前任完成）

`nc` 缺失（`wait_port` 改 bash `/dev/tcp`）、`mktemp -d` 落只读 /tmp（改构建目录内
`mktemp -d "$PWD/trojan-smoke.XXXXXX"`）、hnp bash HMDFS getcwd 失败致 `$PWD`
unbound（配方同 shell 先 `cd` 再显式种子 `PWD`）。详见 notes.md 问题 #1/#2。

---

## 五、测试环境

```
软件: trojan 1.16.0（GPL-3.0-or-later，上游 tarball sha256 86cdb268…）
构建系统: CMake（上游自带 CMakeLists.txt，C++11）
工具链: OHOS SDK 26.0.0.18 / clang 15.0.4 / conan 2.29.1（OHOS 适配版）
profile: ci/conan/profiles/ohos-aarch64（os=OHOS 6.0, arch=armv8）
依赖: boost/1.84.0（system+program_options）、openssl/3.5.8.1、zlib/1.3.1
验证命令: conan create archives/t/trojan/1.16.0 -pr:h=<profile> -pr:b=<profile> --build=missing --user=ohpcd --channel=stable
复验证据: ~/tmp/uc2/z31-trojan/verify7.log（2026-09-25 02:04，补丁集重构后强制重建 G1/G0/G2/G3 全 PASS）
```

---

## 六、证据文件索引

| 证据 | 路径 |
|------|------|
| CI 判决原文（两次失败全文） | PR #11779 评论 191624847 / 191627502（本地留档 `.temp/scratch/pr11779_comments.json`，A 机 `~/tmp/uc2/z31-trojan/ci-verdict-extract.log`） |
| 本地双冒烟通过日志（09-21） | `~/qzy/主理-31-trojan-1.16.0/.ci_logs/conan_build_trojan_1.16.0.log` L186–190 |
| 修复后强制重建全链（09-25） | `~/tmp/uc2/z31-trojan/verify7.log` + `reports/conan-create.log`（L205/207–211/尾行） |
| 无-yes 对照实验 | A 机 `~/tmp/uc2/z31-trojan/smoketest/`（组1 rc=1 复现 CI 首错；组2 rc=0 对照） |
| 修复版 harness（trap 回显验证） | A 机 `~/tmp/uc2/z31-trojan/smoketest/harness/`（scratch `trojan-smoke.2JKld0`：cert.pem 生成 + `=== trojan smoke FAILED at line 41 ===` 首错回显） |
| conan-verify 报告 | `reports/conan-verify-report.md`（2026-09-25 01:48 刷新） |

---

*报告生成: z31-trojan，2026-09-25（依据 A 机盘面日志，数字与日志同源）*
