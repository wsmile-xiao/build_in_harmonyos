# openldap-overlay-rwm 2.6.13 高难适配说明与复现证据

## 1. 文档用途与申请边界

本文是 `openldap-overlay-rwm/2.6.13` 的路径 C（高难度挑战）候选举证
材料，供 Issue `#2044` 与 PR `#5121` 引用。它只覆盖一个软件、一个
Issue、一个分支和一个 PR，不混入依赖库适配。

本材料申请评审委员会按路径 C 候选评估，不宣称已经取得高难度挑战认定、
最终分值或发布状态。最终路径分类、验收和分值以官方审核为准。

## 2. PR 信息与适配范围

- 三方库：OpenLDAP rewrite/remap overlay
- 上游版本：2.6.13
- 上游主页：`https://www.openldap.org/`
- 官方源码：`openldap-2.6.13.tgz`
- SHA-256：
  `d693b49517a42efb85a1a364a310aed16a53d428d1b46c0d31ef3fba78fcb656`
- 构建系统：Autotools
- 目标产物：`libexec/openldap/rwm.so*`
- 唯一 Conan 依赖：已发布的 `libtool/2.5.4`
- 目标环境：aarch64 HarmonyOS PC

该归档不是完整 OpenLDAP 产品包。最终包只交付 rwm 模块、其 ABI 匹配的
私有验证宿主、运行库和必要 schema；LDAP、relay、syncprov 仅为运行上游
测试而从同一源码树构建，测试完成后从包中移除。

## 3. 申请项总览

| 申请路径 | 适用性 | 本 PR 的实际工作与证据 |
|---|---|---|
| 路径 A：基础适配 | 适用 | Conan 配方、Autotools/OHOS 三元组、HMDFS 构建兼容、动态模块打包和消费者验证 |
| 路径 B：知识库扩展 | 适用 | E319 草稿沉淀 ABI 匹配私有宿主、同源测试夹具隔离、按 FIFO 能力选择临时存储 |
| 路径 C：高难度挑战 | 候选 | 在不扩张最终包边界的前提下，使 8 个多 daemon、网络、并发、超时类上游入口在目标端真实执行并达到 8/8 PASS |

路径 C 的申请依据不是代码行数、单线程编译耗时或普通平台宏补丁，而是：

1. 上游 rwm 覆盖依赖多个同源 backend/overlay 和真实 LDAP 网络进程；
2. 目标文件系统对脚本执行、权限继承和 FIFO 的能力不一致；
3. 测试依赖必须进入同一构建图，但不能污染窄范围 rwm 最终包；
4. 必须保留原上游协议流程和终止判定，在真机而非宿主上验证；
5. 最终还要证明包内私有宿主能实际加载 rwm 模块，且破坏包产物后测试会失败。

## 4. Path C 逐项举证

### 4.1 动态模块没有独立消费者 API

`rwm.so` 是由 `slapd` 动态加载的 overlay，不提供可供普通 Conan
consumer 直接编译调用的独立 C API。只检查文件存在、ELF 格式或导出符号，
不能证明以下契约：

- libltdl 能打开模块并解析其传递依赖；
- 模块 ABI 与 slapd 宿主一致；
- rwm 初始化和 overlay 注册完成；
- `overlay rwm` 与 `rwm-suffixmassage` 被真实解析。

本配方从同一源码树和依赖图保留最小私有 `slapd`，打包 `core.schema`，
由 `test_package` 生成绝对包路径配置并执行：

```sh
<package>/libexec/slapd -Tt -f <build>/slapd-rwm.conf
```

CI 的破坏性负向检查会移走包产物并要求同一 consumer 失败，避免出现不依赖
包内容的 false pass。私有宿主未加入公开 `bindirs`，不扩张消费者接口。

### 4.2 上游测试需要跨包边界的同源夹具

直接覆盖 rwm 的 8 个上游入口依赖 LDAP proxy、relay、syncprov、null/ldif、
slapd、LDAP clients、并发 helper、网络 listener 和可写 daemon 状态。若保持
最初的极简构建选项，这 8 个入口只能盘点，不能执行；PR 审查因此对 0/8
作出硬性不通过。

本次没有把依赖后端拆成额外公共包，也没有把完整 OpenLDAP 产品混入 rwm
归档，而是采用同源测试夹具：

1. configure 阶段临时启用 `--enable-ldap=mod`、`--enable-relay=mod` 和
   `--enable-syncprov=mod`；
2. 在安装前运行 8 个上游入口；
3. 安装后删除 `back_ldap.*`、`back_relay.*`、`syncprov.*`；
4. 检查最终 `libexec/openldap` 只有 `rwm.la`、`rwm.so` 及版本化普通文件。

这使测试依赖和被测 rwm 使用完全一致的源码版本、编译选项和 ABI，同时保持
最终包合同不变。

### 4.3 HMDFS 可写不等于具备 daemon 测试能力

目标端诊断证明，普通文件 create/write/remove 成功不能推导 `mkfifo` 成功：

```text
FIFO_OK   /data/storage/el2/base/cache
FIFO_FAIL /storage/Users/currentUser/tmp
```

HMDFS-backed user storage 拒绝 OpenLDAP proxy timeout harness 所需的命名管道。
若只探测“目录可写”，`test079-proxy-timeout` 会在运行中因
`mkfifo: Operation not permitted` 失败。

配方现在为每次构建创建独立候选目录，依次探测普通文件 I/O 和 FIFO 创建；
两者都成功后才把该目录用作 `USER_TESTDIR` 根。OHOS 优先探测
`/data/storage/el2/base/cache`，其他平台回退到 configure 临时根。探测失败会
关闭构建，不会跳过测试或把失败计为通过。

### 4.4 脚本执行与权限映射的组合问题

HMDFS 上复制后的 shell 脚本、libtool wrapper 和目标 helper 不能统一依赖直接
执行。测试目录使用上游 `umask 077` 时，又会因设备 UID/GID 映射导致后续
目标进程无法遍历目录。

适配只修改测试启动层，不改变测试输入、LDAP 操作序列或断言：

- `tests/run` 通过 `CONFIG_SHELL` 启动选定测试脚本；
- slapd、LDAP clients、monitor helper、librewrite 和测试 helper 通过同一
  shell wrapper 启动；
- 测试状态使用组内私有的 `umask 007`，不放宽到 world-writable；
- 并发测试把 `.libs` 中真实目标 ELF 目录传给 `slapd-tester`；
- 每个测试使用独立状态目录和唯一 `SLAPD_BASEPORT` 端口块。

每项测试除进程退出码为零外，还必须出现上游终止标记
`>>>>> Test succeeded`。`test030-relay` 额外要求同时出现
`Using relay backend` 与 `Using ldap backend`，防止任一路径未执行却计为
成功。

## 5. 失败演进、根因与修复闭环

| 阶段 | 实际结果 | 根因 | 修复与边界 |
|---|---|---|---|
| 初始审查 | 上游 8 个入口识别、0 个执行 | 极简包未构建 LDAP/relay/syncprov 测试依赖 | 构建同源测试夹具，打包前移除 |
| r16f fresh build | `test028`、`test030` PASS；`test039` 启动失败 | `monitor_data.sh` 在 HMDFS 不能直接执行 | monitor helper 经 `CONFIG_SHELL` 启动 |
| r16g 同构建诊断 | `test039`、`test047` PASS；`test079` 失败 | HMDFS user storage 不支持 FIFO | 增加 FIFO 能力探测并选择原生 cache |
| r16h 定向复核 | `test079`、`test087`、`test088`、`its9468` PASS | FIFO 根与 wrapper 修复有效 | 保留原上游终止判定，不替换测试 |
| r16i fresh Shadow CI | 8/8 上游 PASS，随后 `test_package` PASS | 完整修复闭环 | 同一干净 Conan home 全量重建验证 |
| AtomGit CI #21811 | L0、L1、Conan test_package、build、cleanup 全部 PASS | 正式 Worker 验证最新提交 | 构建测试耗时 42 分 15 秒，退出成功 |
| AtomGit CI #22131 | configure 首个编译器探针失败 | Conan 子进程把外层原生 `TMPDIR` 改写为 HMDFS user storage | OHOS configure 显式优先原生 cache，再回退到注入值和 build-local |
| AtomGit CI #22141 | build、上游测试、`test_package`、L0/L1、cleanup PASS | 证明申请材料未触发门禁问题 | 22:06 启动早于 22:25 推送的 temp-root 修复，不宣称覆盖 `ce8ab75827` |

诊断轮次用于定位问题，最终通过率只绑定同一次 fresh r16i 全量运行，不把多轮
零散结果拼接成正式 8/8。

## 6. 上游测试入口与真实结果

| 上游入口 | 覆盖重点 | r16i 结果 |
|---|---|---|
| `test028-idassert` | LDAP proxy identity assertion 与 suffix rewriting | PASS |
| `test030-relay` | relay 和 LDAP 两条 backend mapping 路径 | PASS |
| `test039-glue-ldap-concurrency` | 20-child 并发、glue/LDAP rewriting | PASS |
| `test047-ldap` | 查询、修改、timeout、limit、password 流程 | PASS |
| `test079-proxy-timeout` | connection/activity timeout 与 FIFO harness | PASS |
| `test087-librewrite` | librewrite 回归 | PASS |
| `test088-syncprov-glue-rwm` | syncprov/glue/rwm refreshAndPersist 与变更 | PASS |
| `its9468` | 断连、重绑和 proxy timeout 回归 | PASS |

计数口径：8 个脚本入口各计 1 个逻辑测试；内部循环、LDAP 操作、并发 child、
四个 ITS 子场景和重复诊断均不拆分为额外测试。

最终结果：

```text
upstream identified: 8
upstream executed:   8
upstream passed:     8
upstream failed:     0
upstream skipped:    0
upstream pass rate:  100%
consumer executed:   1
consumer passed:     1
```

## 7. 真机与正式 CI 证据

### 7.1 Fresh-build Shadow CI

```text
runner: codex-openldap-overlay-rwm-issue-2044-r16i-final-upstream-tests-20260812-190906-919
target: aarch64 HarmonyOS PC
Conan home: fresh isolated conan-home-r16i-final-upstream-tests
L0: pass
L1: pass
L2: skip (package intentionally has no public bin/)
L4: pass
L5: pass
package summary: 1 success, 0 failed
runner rc: 0
```

该运行从官方源码 tarball 的已验证本地缓存开始，完整执行 configure、
`make depend -j1`、`make -j1`、8 个上游入口、package 和 `test_package`。

### 7.2 AtomGit PR CI

```text
PR: #5121
build: #21811
worker: OpenHarmonyPCDeveloper-CI-033
Conan test_package: pass
L0: pass
L1: pass
conan-build-test: pass (42m 15s)
cleanup: pass
```

正式 CI 证明最新分支可以从镜像 URL 下载与校验官方内容一致的源码，并在社区
Worker 上完成相同配方和消费者验证。

## 8. 生产包与测试边界

- 最终公开模块：`rwm.so*`。
- 私有验证宿主：`libexec/slapd`，不在 `bindirs`。
- 必要配置数据：`etc/openldap/schema/core.schema`。
- 测试夹具模块：`back_ldap`、`back_relay`、`syncprov`，最终包中均不存在。
- 可选依赖保持关闭：Cyrus SASL、TLS、libevent、argon2、LMDB、systemd。
- 未修改 OpenLDAP rwm 生产源文件和公共 ABI。
- 未把目标端失败解释为 host PASS，未把 SKIP 计为 PASS。

## 9. 可复用知识

本 PR 同时提交 E319 草稿，提炼三项可复用模式：

1. 无独立 consumer API 的动态模块使用同一构建图中的 ABI 匹配私有宿主，
   运行配置验证模式并配对破坏性负向测试；
2. 上游测试需要包外组件时，只在测试阶段构建最小同源夹具，执行真实上游
   入口后从最终包移除；
3. daemon 测试临时目录按实际能力选择，除普通文件 I/O 外还应探测 FIFO、
   socket、lock 等 harness 依赖的操作。

## 10. 复现命令

在已配置的 aarch64 HarmonyOS 隔离任务中：

```sh
. "$HOME/ohos-users/codex/openldap-overlay-rwm-2.6.13-2044-20260811/env.sh"
export CONAN_HOME="$OHOS_JOB_BASE/conan-home-path-c-fresh"
cd "$CI_REPO_ROOT"
zsh ci/conan/setup.sh
zsh ci/conan/build_and_test.sh "$CI_PACKAGES"
```

共享设备上应由 `$HOME/bin/ohos-test-runner.sh` 以 heavy 模式排队，保持全局
单包锁。验收要求：8 个上游入口各出现唯一成功终态，`test_package` 成功，
最终模块目录不含三项测试夹具，runner 退出码为零。

## 11. 请评审确认

请评审委员会确认以下组合工作是否满足路径 C 高难度挑战候选材料要求：

1. 在目标端复现并区分 HMDFS 脚本执行、权限映射和 FIFO 能力差异；
2. 为多 daemon 上游集成测试建立同源夹具但保持最终窄包边界；
3. 不改变上游协议流程和断言，使原 0/8 的相关测试达到 fresh 8/8；
4. 使用 ABI 匹配私有宿主和破坏性负向测试验证动态模块；
5. 完成 Shadow CI 和 AtomGit 正式 CI 双重闭环。

路径 C 分类和分值最终以官方审核为准。

## 12. Issue 与 PR 引用

```text
路径 C 详细举证：archives/o/openldap-overlay-rwm/2.6.13/reports/high-difficulty-evidence.md
```

- Issue：`#2044`
- PR：`#5121`
- 实现证据提交：`1340d5a5986caeb2935599c5ee738c0b7b27eb93`
