# trojan 1.16.0 适配笔记

## 编译环境
- 构建系统: cmake（上游自带 CMakeLists，C++11）
- 编译日期: 2026-09-21
- 编译器: clang/clang++（OHOS aarch64 工具链, conan profile ohos-aarch64）
- 状态: built（W3 通过后更新）

## 编译步骤

1. conandata.yml 源 = GitHub 官方 tag archive（trojan 无 submodule，archive 即完整源码）。
2. build(): 应用补丁（上游冒烟脚本可移植化）→ CMake configure
   （`ENABLE_MYSQL=OFF`——上游默认 ON 且 find_package REQUIRED；
   `SYSTEMD_SERVICE=OFF`——OHOS 无 systemd）→ `cmake.build()` →
   运行上游端到端冒烟套件 `tests/LinuxSmokeTest/basic.sh` 与 `fake-client.sh`（见下）。
3. test_package: 消费者测试 `test_tls.sh` —— `trojan -t` 校验配置 →
   起包内 trojan server → `openssl s_client` 完成 TLS 握手并断言
   `Verify return code: 0`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游冒烟 basic.sh 在 OHOS 上不可直接运行 | 依赖 `nc`（镜像内无）且 `mktemp -d` 落只读 /tmp（E002/E052 家族） | 补丁 common.sh：wait_port 改 bash `/dev/tcp` 探测；TMPDIR 改 `mktemp -d "$PWD/trojan-smoke.XXXXXX"`（构建目录内，可写） |
| 2 | 上游冒烟脚本启动即失败：`shell-init: error retrieving current directory: getcwd: cannot access parent directories: Not supported` → `common.sh: line 26: PWD: unbound variable` | hnp bash 在 HMDFS 构建目录下 `getcwd()` 失败（E386 家族），bash 起手的内建 `PWD` 因此未赋值，而 common.sh 用 `$PWD` 拼临时目录 | 在配方里同 shell 先 `cd` 再显式种子 `PWD`：`self.run(f'cd "{scratch}" && PWD="{scratch}" bash "{smoke}" ...')`（命中既有草稿 DRAFT-hnp-bash-pwd-unbound-set-u-scripts，判 hit 不另计 B） |
| 4 | CI 两次校验失败（PR #11779 构建 #60109/#60185，双 worker 同挂）：编译绿但 `build()` line 82 smoke `exit 1`，stdout 仅 scratch 目录名，无首错 | CI worker 镜像无 coreutils `yes`，上游 `yes '' \| openssl req` 的 yes 缺失 → openssl req DN 交互遇 EOF → `Error making certificate request` exit 1；stderr 全被 `exec 2>>test.log` 吞入 scratch（CI 环境销毁不可取）。A 机无-yes 对照实验复现（组1 rc=1 同首错 / 组2 rc=0） | 0002 补丁：`-subj/-batch` 显式 DN 删 yes 依赖 + `OPENSSL_CONF=/dev/null`；`trap ERR` 回显 test.log 尾部到 stdout（失败自此可见）；`wait_port` 60s 超时快速失败 |
| 3 | 消费者测试 `openssl req` 报 `Can't open ".../.cache/conan2/p/b/opensf4d50a3c869ab/p/ssl/openssl.cnf" for reading` 退出码 1，而 build() 里同一条命令正常 | 已发布 openssl 制品把 `--openssldir` 编译成**构建期 conan 包目录绝对路径**（`openssl version -d` 实测指向不存在的 `~/.cache/conan2/...`，包内也不附带 cnf）；build() 走 VirtualBuildEnv 命中设备自带 openssl，test() 走 conanrun 命中包内那份，故只有消费者侧失败 | 消费者脚本顶部 `export OPENSSL_CONF=/dev/null`，证书字段全部由 `-subj/-batch` 显式给出（本包新增路径 B 草稿 DRAFT-trojan-1.16.0-openssl-cli-stale-openssldir） |

## 源码修改

- patches/0001-tests-LinuxSmokeTest-common.sh.patch（+4/-3）：仅改测试脚本
  common.sh，不触生产代码；type=portability。
- patches/0002-tests-LinuxSmokeTest-smoke-nointeractive.patch（+39/-2）：仅改
  测试脚本（basic.sh/fake-client.sh/common.sh），不触生产代码；type=portability。
  openssl 证书生成去 yes 依赖（-subj/-batch + OPENSSL_CONF=/dev/null）、ERR trap
  回显 test.log 首错到 stdout、wait_port 60s 超时。

## 依赖版本

- boost/1.84.0（ohpcd 定制配方，含 system + program_options 组件，
  trojan `find_package(Boost 1.66 COMPONENTS system program_options REQUIRED)`）
- openssl/3.5.8.1（`find_package(OpenSSL 1.1.0 REQUIRED)`）

## 验证结果

```bash
# 设备实测（2026-09-21，CONAN_HOME=~/tmp/ch/home-DS16，conan 2.29.1 / profile ohos-aarch64）
python3 scripts/ohc-run.py conan-verify trojan 1.16.0     # -> PASS
#   G1 配方完整性 PASS / G0 预构建风险评估 PASS / G2 conan create 干净构建 PASS
#   G3 系统同名库隔离(R26) PASS / G4 产物完整性 + L2 平台功能矩阵 + L4 checksec + L5 基线对比 PASS
#   上游冒烟在 build() 内真实执行并通过：basic.sh（SOCKS5+forward 双路径 whoami 断言）、
#   fake-client.sh（纯 TLS 客户端直连必须被拒 + fake 路径断言），两者退出码均为 0
#   test_package 消费者测试 test_tls.sh 通过：trojan -t 校验 -> 起包内 server -> openssl s_client
#   断言 "Verify return code: 0"
# 资源封顶证据（AGENTS §14.1④ 父进程监管，整进程组 0.5s 采样）：
#   MEMCAP[run] peak=592MB budget=3500MB rc=0 用时60.6s
#
# CI 失败修复后强制重建复验（2026-09-25，conan remove trojan/* 后全链）：
#   verify6: G1/G0/G2/G3 全 PASS，MEMCAP peak=575MB budget=2500MB rc=0 用时70.8s
#   reports/conan-create.log：L219 Built target trojan / L221-225 双冒烟实跑
#   （scratch trojan-smoke.5lG0ZU / .gdf1BB）/ L304 消费者 TLS verified
```

## 测试账本（五维，AGENTS §10.1）

| 维度 | 数 | 口径 |
|---|---|---|
| `N_static` | 2 | 上游 CMakeLists.txt（L124-128，非 Windows 分支）`enable_testing()` + `add_test` 注册 `LinuxSmokeTest-basic`、`LinuxSmokeTest-fake-client` 两条，COMMAND 为 `bash <脚本> <构建目录>/trojan`；配方 `build()` 的 `self.run` 直跑与该 COMMAND 同形等价 |
| `N_registered` | 2 | 两个脚本均在配方 `build()` 内以 `self.run` 真实执行 |
| `N_executed` | 2 | 全部执行，退出码均 0（任一失败 conan create 即中止） |
| 未执行/跳过 | 0 | 无平台受限项 |
| `N_consumer` | 1 | `test_package/test_tls.sh`：真实启动包内 trojan 服务端并完成 TLS 握手，断言 `Verify return code: 0`；检查链 5 个检查点：二进制可执行/证书生成非空/`-t` 校验通过/服务存活/握手 Verify=0 |

## 注意事项

- 上游测试注册为 CMake `add_test` ×2（同 tests/LinuxSmokeTest 两个端到端脚本）；
  `basic.sh`（自签证书 → python3 http.server 假源站 → trojan server+client 回环组网 →
  curl socks5/forward 双路径取回 whoami 断言）与 `fake-client.sh`（额外断言纯 TLS 客户端
  直连必须拿不到真源站内容、fake 路径返回 fake），N_static=2，两者均已集成进 build() 真实执行。
- 两个脚本共用回环端口（10080/10081/10443/11080，basic.sh 另用 20081），配方按顺序串行执行
  并在各自结束时 kill -KILL 清理，不并发占用。
- trojan 为 application 包，软件级 commands.json 已声明（R38）。
## 对话记录（续，z31-trojan，2026-09-25）

- **CI 失败定位与修复**：PR #11779 两次 CI 校验失败（#60109 CI-008 / #60185 CI-015），
  编译全绿但 `build()` smoke `exit 1` 且无首错输出。判决原文取证（GitCode API 只读）
  + A 机对照实验实证根因为 CI 镜像无 coreutils `yes`（见问题 #4）。修复走
  0002 新补丁（不动 0001、不 amend 已推送提交）。强制重建复验 verify6 全绿。
  五维账本同步修正 `N_static` 归因（上游实有 `add_test` 注册，实测 CMakeLists L124-128）。
  证据：`~/tmp/uc2/z31-trojan/{verify6.log, ci-verdict-extract.log, smoketest/}`；
  测试明细见 `reports/test-report.md`。

## 对话记录

- **接手（QOD-BE7，2026-09-21 19:56）**：本行由 DS-16 交接包接手（`~/tmp/uc2/handoff/trojan-1.16.0/`），
  配方与冒烟集成已在分支 `a7700228f2`；接手时 `claimer` 已核对为 `wanderlust_0823`（任务 11298）。
- **首跑 conan-verify → G2 失败**：上游冒烟 `basic.sh` 启动即 `shell-init: error retrieving current
  directory: getcwd: cannot access parent directories: Not supported`，随后
  `common.sh: line 26: PWD: unbound variable`。判为 E386 家族（hnp bash getcwd 失败 → 内建 `PWD`
  未赋值），按既有草稿 `DRAFT-hnp-bash-pwd-unbound-set-u-scripts` 的修法在配方里同 shell 先 `cd`
  再显式种子 `PWD`。**判重结论：hit，不另计 B。**
- **二跑 → 进入 test_package 后失败**：消费者测试 `openssl req` 报
  `Can't open ".../.cache/conan2/p/b/opensf4d50a3c869ab/p/ssl/openssl.cnf" for reading`。
  设备侧实测取证：`conanrun` 环境下 `command -v openssl` 命中包内二进制，其 `openssl version -d`
  的 OPENSSLDIR 指向不存在的构建期路径，`find` 确认包内不附带 cnf；`OPENSSL_CONF=/dev/null` 后
  同命令退出码 0 并产出证书。另对照确认 `build()` 内同一条命令走 VirtualBuildEnv 命中设备自带
  openssl 而一直正常。查重 `knowledge/graph/index.tsv` 与 `knowledge/drafts/` 无命中（最相近的
  E006 是 ARM64 RSA-PSS 汇编 bug、E235 是随机源 seeding、DRAFT-openssl-4.0-major-migration 是 4.0
  版本迁移断言），`draft-review` 实测 TOP3 相似度 ≤0.03，**判 create 并新增本草稿**。
- **覆盖面修正**：原实现只跑 `basic.sh`（`N_static=1`）。核对上游 `tests/LinuxSmokeTest/README.md`
  的 Usage 节后确认注册入口为 `basic.sh` 与 `fake-client.sh` 两条，遂把两者都接入 `build()` 真实
  执行（负路径断言：纯 TLS 客户端直连不得取到真源站内容），`N_static` 修正为 2。
- **门禁**：`conan-verify` → `✅ 配方验证通过`（G1/G0/G2/G3 PASS + G4/L2/L4/L5）；`finish built`
  → `✅ W3 本地 CI 模拟通过`；`preflight_check.sh trojan/1.16.0` 在 `CONAN_HOME` 正确指向含 ohpcd
  remote 的任务 home 后 PASS（首次误用默认 home 时曾把"远端未配置"误诊为 boost/openssl 未发布，
  属已记录的判别陷阱）。
---

**编译结束**: 2026-09-25 02:06
**最终状态**: built
