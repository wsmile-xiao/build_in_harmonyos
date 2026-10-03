# sysrqd 17 适配笔记

## 概述

- 软件: sysrqd — 通过网络（TCP 4094，密码认证）触发 Linux Magic SysRq 的小型守护进程
- 上游: https://github.com/jd/sysrqd（作者 Julien Danjou）
- 版本: 17（ChangeLog `Version 17 -- 8 Apr 2019`，最后一个上游版本）
- 许可: GPL-2.0-only（sysrqd.c 文件头许可声明）
- 构建系统: 普通 GNU Makefile（单个 sysrqd.c，无 configure，无 autotools）
- 产物: 单个可执行文件 `sysrqd`（上游安装到 /usr/sbin）
- 目标平台: OpenHarmony / HarmonyOS PC (aarch64-linux-ohos)

## 时间/状态

- 适配日期: 2026-09-29（真机 shadow CI 2026-10-01 r3 通过）
- 状态: **built**（本机前置 + 真机 conan create + test_package + L1e 全部通过）
- 分支: `feat/sysrqd-17-codex`，worktree `D:\harmonyos\worktrees\sysrqd`

## W0 依赖结论

```text
依赖数量：0（仅依赖 C 库，无第三方依赖）
已满足依赖：libc（crypt/daemon/mlockall/setpriority/syslog 均由 OHOS musl libc 导出）
缺失依赖：无
是否需要拆分依赖适配：否
阻塞点：无
下一步：本机前置验证 → CI/真机
```

`-lcrypt`：OHOS sysroot 无 libcrypt.so，但提供 libcrypt.a，且 libc.so 本身导出
`crypt` 符号（见下文 W4 验证），上游 LDFLAGS 原样可用，无需 libxcrypt/libcrypt
独立适配。制品仓 `sysrqd` 不存在（本仓 archives 与知识库检索均无记录），属首次
适配，Conan 包版本 = 上游版本 = `17`，无需 R37 递增。

## 源码归档选择

- URL: `https://deb.debian.org/debian/pool/main/s/sysrqd/sysrqd_17.orig.tar.gz`
- SHA256: `5b4b7f1b550001b330069c309ea70b69bd3875d8392ba8ea207dc74ee417e462`
- 格式: tar.gz（URL 以 `.tar.gz` 结尾，Conan 选 gzip 解压器，规避无扩展名
  codeload URL 的 `BadZipFile`，见知识条目 E392）
- 上游仓库无 tag/release 归档；Debian orig tarball 即上游 git 快照
  （解压根目录 `jd-sysrqd-9510edc`），是最接近官方的发行源码包。
- 归档内容：sysrqd.c(331 行) + Makefile + ChangeLog + README.md + INSTALL +
  AUTHORS + .gitignore，**无测试**、无 COPYING 文件（许可声明在 sysrqd.c 头部）。

## W1 源码与构建系统分析

| 观察点 | 结论 |
|---|---|
| 语言 | 纯 C（单文件 sysrqd.c） |
| 构建入口 | 手写 Makefile（无 configure） |
| 头文件依赖 | stdio/stdlib/fcntl/socket/netdb/syslog/crypt/mman 等标准头，sysroot 全部具备 |
| 关键 API | `crypt()`、`daemon()`、`mlockall()`、`setpriority()`、`syslog()` — 全部由 OHOS musl libc 导出（本机 llvm-nm 验证，见 W4） |
| socket | 仅 PF_INET/SO_REUSEADDR/inet_aton，musl 全有 |
| 运行时前提 | root、`/etc/sysrqd.secret`、TCP 4094、`/proc/sysrq-trigger`（编译期无涉及） |
| 测试 | **上游无任何测试**（无 tests/、无 check/test 目标、README 只给 telnet 演示） |
| VERSION 提取 | `grep '^Version' ChangeLog \| head \| cut \| tr` 管道 — 配方在 make 命令行钉 `VERSION=17` 绕开 |
| install 目标 | 调用 `install` 命令（OHOS 缺失，E098）— 配方不用 make install，package() 直接复制 |

### 潜在风险点（已排除/降级）

1. **crypt 依赖**：OHOS 无 libcrypt.so。实测 sysroot 有 libcrypt.a 且 libc.so
   导出 `crypt` → `-lcrypt` 链接成功（W4 实证）。与 E014（musl 未导出符号族）
   不同：sysrqd 所需 5 个关键符号全部导出，零补丁。
2. **/proc/sysrq-trigger**（E031 /proc SELinux 限制、E051 未实现 syscall）：
   仅影响真机完整守护行为，不影响编译打包与 test_package 拒绝路径断言。
3. **setpriority(-19) / mlockall / write /var/run/sysrqd.pid**：需要 root 权限，
   属运行时行为，真机完整功能验证超出本轮边界，notes 如实记录。

## W2 配方设计

`conanfile.py` 要点：

- `package_type = "application"`，`settings = os/compiler/build_type/arch`。
- `source()`：`get(self, **self.conan_data["sources"], strip_root=True)`。
- `build()`：R33 编译器取自 `tools.build:compiler_executables`；单条命令
  `make CC="<target-clang>" VERSION="17" -j1 sysrqd`（钉 VERSION 绕 toybox
  管道；不用 make install）。
- `package()`：bin/sysrqd（chmod 0755；用 Conan 标准 bin/ 使 CI L5/L1e
  门禁可识别产物，上游原生安装到 /usr/sbin）、share/sysrqd/doc/{README.md,ChangeLog}、
  licenses/AUTHORS（归档无 COPYING，许可声明在源文件头，已在配方注释说明）。
- `package_info()`：`cpp_info.bindirs = ["bin"]`。
- 补丁：**无**（conandata patches 为空列表）。

## W3 test_package

- `test_package/conanfile.py`：`test_type="explicit"`、`generators="VirtualRunEnv"`，
  经 `bash test.sh` 调用已安装二进制（OHOS 的 /system/bin sh 不能执行 ELF）。
- `test_package/test.sh`：**6 项**确定性断言 —
  A1 二进制存在可执行、A2 ELF magic、A3 AArch64 e_machine(0xB7)、
  A4 无参数启动 exit 1（daemonize 前拒绝）、A5 非 root stderr 拒绝消息
  （root 环境自动 SKIP）、A6 未解析参数 `--version` 同样 exit 1。
  全部以 `timeout 10` 防护，避免任何环境下守护进程挂起测试。
- 设计依据：`int main(void)` 不解析参数；非 root → `Only root can run this
  program.` + exit 1；root 且无 /etc/sysrqd.secret → syslog + exit 1；两条路径
  都在 daemon() 之前退出，root/非 root 环境断言均成立。
- 完整守护行为（root + secret + 端口 4094 + /proc/sysrq-trigger）超出
  test_package 边界：需要改写 /etc、绑定特权行为，且 OHOS /proc 受 SELinux
  限制（E031），在 notes 与 MANIFEST 中如实申报为环境限制而非静默跳过。
- `test_package/MANIFEST.yml`：如实申报「上游测试 = 0」。

## W4 本机前置验证

| 检查 | 结果 |
|---|---|
| YAML/JSON 结构（conandata/manifest/MANIFEST/commands.json） | 通过 |
| Python 语法（conanfile.py、test_package/conanfile.py） | 通过（py_compile） |
| Shell 语法（test.sh） | 通过（bash -n） |
| 源码 SHA256 复核 | 通过（= 5b4b7f1b…，下载时复算） |
| musl 符号核验 | 通过：`llvm-nm -D libc.so` 导出 `crypt`/`daemon`/`mlockall`/`setpriority`/`syslog`；sysroot 有 libcrypt.a（无 libcrypt.so） |
| **OHOS 交叉编译（真实）** | **通过**：DevEco OHOS clang 15.0.4，`-target aarch64-linux-ohos --sysroot=…`，上游全套警告 CFLAGS + `-DSYSRQD_VERSION="\"17\""` 编译 0 error 0 warning |
| 链接（含 -lcrypt） | **通过**：aarch64 ELF（DYN），NEEDED 仅 libc.so，无 UND 残留符号 |
| `conan create` | **未执行**（本机无 Conan） |
| 目标二进制运行 | **未执行**（本机无 OHOS 运行时；Windows 无法运行 aarch64-ohos ELF） |

> 交叉编译命令与 rotix 案例一致，未走 Makefile 而是直接调 clang（本机无 Conan
> 环境下隔离验证源码/头文件/链接兼容性）；Makefile 路径本身仅是薄封装，配方
> build() 的 `make CC= VERSION=` 已在 W2 逐项对齐。

## W5 真机 shadow CI 结果

### r1（2026-10-01 20:55，失败于 KC 门禁——环境问题，非包问题）

| 项 | r1 |
|---|---|
| job 名 | sysrqd-17-20261001 |
| exit code | 1 |
| 失败门禁 | KC：`build_and_test.sh:980: permission denied: bash` |
| 根因 | runner 环境 PATH 无 bash：`/bin/bash`、`/usr/bin/bash` 不存在，bash 实际在 `/data/service/hnp/bin/bash`；同批 reniced r2 同样挂 KC（malint/trickle 各死于自身 no_test_sources/registry_unreachable） |
| 解法 | 修补 job 私有 `env.sh` 追加 `export PATH=/data/service/hnp/bin:$PATH`（不动 git 基础设施），重跑 |

传输：scp + 设备端 sha256 校验（`8ca7d3dc…` 一致），find 清点 9 文件齐全。

### r2（2026-10-01 20:57，pass）

| 项 | r2 |
|---|---|
| exit code | 0（Build Summary 100.0%，1/1 成功） |
| 排队 | wait_seconds=0（锁空闲即得） |
| L0 / KC / JC / G0 / G0e | 全 pass（R37 首次发布无碰撞、R38 commands.json valid、R39 目录结构 valid） |
| conan create | 成功：源码从 deb.debian.org 直接下载成功（无需镜像 fallback）、`make CC=<hnp clang> VERSION=17` 零警告编译、`-lcrypt` 链接成功、打包 AUTHORS/README.md/ChangeLog/sysrqd 4 文件 |
| test_package | **6/6 assertions PASS（0 skipped）**：真机非 root，A5 拒绝消息断言也实跑通过 |
| L1 | pass（L1a/L1b 测试执行证据确认） |
| L2 | skip: no bin/ dir（当时产物在 sbin/） |
| L4 | pass（no patches） |
| L5 | **warn: no artifacts found**（CI 只识别 bin/lib，产物在 sbin/） |
| L1e | **skip: No standard artifact dirs found to sabotage**（同因，未真正执行破坏性验证） |

### r3（改进：sbin → bin）

r2 暴露两个改进点：L5 warn 与 L1e skip 均因产物目录不在 CI 识别的 `bin/`。
r3 把 package 目录从 `sbin/` 改为 Conan 标准 `bin/`（上游原生安装 /usr/sbin，
此改动仅为 CI 门禁识别与消费者习惯，已在配方注释说明），期望 L5=pass、
L1e 真正执行破坏性验证（破坏 bin/sysrqd 后 test.sh A1/A4 必 FAIL）。
已知代价：L2 冒烟将执行 `--version/--help`，而 sysrqd 无 CLI 参数解析
（main(void)），预期 L2 non-blocking skip/fail（同 rotix/E503 案例处理）。

### r3（2026-10-01 21:00，pass，全绿）

| 项 | r3 |
|---|---|
| run 目录 | ohos-test-runs/codex-17-sysrqd-17-20261001-conan-20261001-210013-17320 |
| exit code | 0（Build Summary 100.0%，1/1 成功） |
| 排队 | wait_seconds=0 |
| L0 / L1 / L4 | pass / pass / pass（no patches） |
| **L1e** | **pass：`[sabotage] bin/ moved away` → `Negative test confirmed — test genuinely depends on sysrqd`**（真实破坏性反向验证） |
| **L5** | **pass: bin/ has content** |
| L2 | skip: sysrqd version/help failed（non-blocking）——sysrqd `int main(void)` 不解析任何参数，`--version` 走非 root 拒绝路径 exit 1；与 rotix/E503 同族，属上游 CLI 惯例缺失而非平台适配缺口，真机 A6 断言已实测该行为 |
| KC / JC / G0 / G0e | pass / pass: empty / pass / pass |
| test_package | **6/6 assertions PASS（0 skipped）** |
| 上游测试 | 0/0（上游确无测试，MANIFEST.yml 已附清点证据） |

### r3 后状态更新

版本级/软件级 manifest 状态由 pending → **built**（真机 conan create +
test_package + L1e 破坏性验证全部通过）。`commands.json` 的 `binary` 保持
false（制品仓发布在 PR 合并后的 release 流水线，届时改 true）。

## 遗留与阻塞点

- ~~本机无 Conan：`conan create` / test_package 待真机 shadow CI 执行。~~（r3 已补齐）
- ~~无 OHOS 运行时，未运行目标二进制~~（真机已验证，见 W5 r3 记录）
- 真机完整守护功能（root + secret + 4094 端口 + /proc/sysrq-trigger）预期受
  SELinux/权限限制，不在验证目标内；以启动拒绝路径断言为验收主体。
- issue 编号待补（任务下发时未提供，仓库内亦无 sysrqd 相关 issue 记录）。

## 下一步（W5/W6）

```bash
# 真机隔离 job（拿到空闲窗口后）
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex \
  --job sysrqd-17-<日期> \
  --package archives/s/sysrqd/17 \
  --repo-source <existing-repo>
sh "$HOME/ohos-users/codex/sysrqd-17-<日期>/run-conan-heavy.sh"

# 本机具备 OHOS conan 时的等价命令
conan create archives/s/sysrqd/17 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 提交前终检后一键提交（内含门禁 + 审计 + push + PR + CI 监控）
python3 scripts/ohc-run.py submit sysrqd 17
```

## 交付物

| 文件 | 说明 |
|---|---|
| conanfile.py | application 型配方（纯 make，钉 CC/VERSION，零补丁） |
| conandata.yml | Debian orig URL + SHA-256，patches 为空 |
| test_package/ | conanfile.py + test.sh（6 断言，root 自适应）+ MANIFEST.yml |
| commands.json | CLI 工具声明（R38，软件级） |
| manifest.yaml | 软件级元数据（ohos_adaptation.key_points + versions） |
| notes.md | 本文件 |

## 知识草稿沉淀

本轮产出 3 条知识草稿（`knowledge/drafts/`，.md + .kv 成对）：

1. **DRAFT-sysrqd-17-ohos-musl-libc-exports-crypt-daemon-no-patch**：OHOS musl
   libc 直接导出 crypt/daemon/syslog/mlockall/setpriority 且有 libcrypt.a——
   libxcrypt 类用户零补丁，勿因无 libcrypt.so 误判依赖缺失（W0 实证）。
2. **DRAFT-shadow-ci-kc-gate-permission-denied-bash-hnp-path**：隔离 job runner
   PATH 缺 hnp bin 使 KC 门禁 bash 调用被拒（L0 全过后挂 KC）；job 私有
   env.sh 追加 PATH 修复（r1 → r2 实证）。
3. **DRAFT-ci-l5-l1e-standard-bindir-sbin-packages**：上游装 /usr/sbin 的
   application 包必须打包到 Conan 标准 bin/，否则 L5 永远 warn、L1e 被
   静默跳过（r2 → r3 实证）。

查重结论（其余发现已有归属，不重复立条）：

| 本轮发现 | 既有条目 | 处置 |
|---|---|---|
| 隔离 job PATH 缺 hnp bin（build 层 cmake Error 127 表现） | opencsg-1.8.2-shadow-ci-isolated-job-hnp-toolchain-path | 草稿②标 similar_to（失败面 KC 层不同，独立检索词） |
| L1e 空壳测试判定 | E560 | 草稿③标 similar_to（本条是 L1e 被跳过的前置条件） |
| L2 冒烟 × 无参数 CLI | E503（jshon）/ rotix | 引用，不立条 |
| /proc SELinux 限制（完整守护行为） | E031/E051 | 引用，不立条 |
| install 命令缺失 | E098 | 引用，不立条 |
| musl 未导出符号（运行期 syscall） | E014 | 草稿①标 similar_to（链接期/运行期分层） |

## issue 说明

本轮任务提示中「issue」要求先在项目内/会话上下文中确认；仓库内（archives、
knowledge、git grep）**未找到 sysrqd 相关 issue 编号**。按任务兜底要求，
本包已继续完成本机前置适配，**issue 编号待补**（见交付报告）。
