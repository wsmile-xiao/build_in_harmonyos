# DRAFT-hnp-bash-pwd-unbound-set-u-scripts — OHOS hnp bash 执行上下文 PWD 不可假设：set -u 脚本引用 ${PWD} 必现 "unbound variable"

> **Contributor**: sea_crab | **Status**: DRAFT | **Updated**: 2026-09-09
> **Severity**: blocking (2) | **Category**: shell / ohos / runtime / environment / conan
> **Audience**: 所有在 OHOS 上以 hnp bash 执行脚本类应用（纯 bash 包）的配方维护者、conan test_package 作者、CI harness/直跑冒烟脚本作者

## 触发（trigger）

- 以 **hnp bash**（`/data/service/hnp/bin/bash`，bash 5.3）执行脚本；
- 派生上下文环境里**没有 PWD**：ssh 远程命令、`env -i`/`subprocess(env=…)` 清洁 env、部分 CI 派生链；
- 被执行脚本启用 `set -u`（或 `set -euo pipefail`）且引用 `${PWD}`（或在子上下文调用 `pwd` 内建）。
- 典型案例（本条 source_event）：dehydrated 0.7.2，脚本第 9 行 `set -u`，第 348 行 load_config 配置搜索路径含 `"${PWD}"`——启动即崩，与业务参数无关。

## 症状（symptom）

```text
shell-init: error retrieving current directory: getcwd: cannot access parent directories: Operation not permitted
/data/service/hnp/bin/bash: line 1: PWD: unbound variable
```

脚本无任何业务输出即退出；`pwd` 内建同报 `pwd: error retrieving current directory`。
间歇性形态：同一脚本经 conan 聚合 shell / mksh 间接执行时正常（父进程导出了 PWD），直跑/ssh/清洁 env 必崩。

## 机制（root cause）

1. **bash 启动 PWD 初始化**：hnp bash 启动时若环境未带 PWD，用 getcwd(2) 探测当前目录来初始化内置 PWD。
2. **OHOS hnp 域 getcwd() 跨目录受限**（设备实测，2026-09-09）：

| 上下文（ssh 远程命令） | 结果 |
|---|---|
| 默认（home 目录） | getcwd: Operation not permitted → PWD 未定义 |
| `cd /tmp && env -u PWD bash -c …` | getcwd: Permission denied → PWD 未定义（**cd 不救**） |
| `cd /data/service/hnp/bin && env -u PWD …` | getcwd: Permission denied → PWD 未定义 |
| 深层 storage 路径（.local/state/…） | getcwd: Not a tty / Not supported → PWD 未定义 |
| `PWD=/tmp bash -c …`（显式传入） | 正常执行，仅余 getcwd 诊断噪音 |

   注意失败横跨本地目录（/tmp、/data）与 storage 路径——**不是 HMDFS 独有、也不要求"过期 PWD"**，比姊妹现象（autoconf 2.69 configure 的 getcwd 失败，见 DRAFT-autoconf269-config-shell-unset-not-empty）的记录面更宽。
3. **失败点**：脚本首次 `${PWD}` 展开（或 `pwd` 内建），`set -u` 将未定义变量升级为致命错误，退出码非 0。
4. **归类**：OHOS hnp 域执行上下文语义（getcwd 受限 × bash PWD 回退缺失），非库缺陷；调用方一侧修复。

## 验证（verification，自包含、只读）

```bash
# 复现（任意新 shell）:
ssh <ohos-host> '/data/service/hnp/bin/bash -c "set -u; echo [\$PWD]"'
# 修复面:
ssh <ohos-host> 'PWD=/tmp /data/service/hnp/bin/bash -c "set -u; echo [\$PWD]"'   # → [/tmp]
# 反面（证明 cd 不是退路）:
ssh <ohos-host> 'cd /tmp && env -u PWD /data/service/hnp/bin/bash -c "set -u; echo [\$PWD]"'   # 仍崩
```

## 修复（rec：调用方显式传 PWD）

- conan 配方（build()/test_package 一致）：

```python
self.run('cd "%s" && PWD="%s" "%s" dehydrated --version' % (src, src, bash))
# test_package: env = dict(os.environ); env["PWD"] = script_dir; subprocess.run([bash, script, ...], env=env, cwd=script_dir)
```

- CI/直跑：执行前 `export PWD=$PWD`。
- 不改被测脚本、不预置答案（态度审计 2 通过）；案例已在 dehydrated 0.7.2 候选（`archives/d/dehydrated/0.7.2/conanfile.py` build() 与 `test_package/test_dehydrated.py`）落地，权威 CI PASS。

### fallback（诚实权衡）

经会导出 PWD 的父 shell（conan 聚合 shell、mksh）间接执行。**掩盖而非修复**：父 shell 是否导出 PWD 是实现细节（zsh/ssh 命令上下文实测不导出），换执行器即复发；仅作退路。

### 反模式（forbid）

1. `cd <dir> && bash script`（不配 `PWD=`）——cd 只作用父进程域，bash 启动仍自己 getcwd()；本机探索通过、CI/ssh 必崩，是最难排查的间歇性形态。
2. `env -i bash …` / `subprocess(env={})` 派生脚本不回填 PWD——getcwd 失败率最高，set -u 脚本启动即死，易误判为脚本自身缺陷而开始改上游源码。

## 证据与关联

- 案例 run：dehydrated 0.7.2（候选 b53a3cc4f7，权威 CI PASS：`Total=1 Success=1`，含 L1 6 断言 + L1e 破坏性反向验证 + L2 冒烟）。
- 探针复核：Curator 2026-09-09 设备实测（上表全部行）。
- 相近条目与差异：
  - **DRAFT-autoconf269-config-shell-unset-not-empty**：同根（hnp bash 启动 getcwd 失败），但失败面是 autoconf 2.69 configure 的 re-exec 中止（"working directory cannot be determined"），修复轨道围绕 CONFIG_SHELL；本条失败面是任意 `set -u` 脚本的启动崩溃（"PWD: unbound variable"），波及脚本类应用与测试直跑，且实证 cd 不可作为退路。两案互补，建议交叉引用；编号合并与否由主编定。
  - **E386**（noexec 树上能力测试 shell + 选择性派发）：共享"getcwd 诊断 ≠ 能力可用"的教训，但 E386 面向 Automake 测试派发与 shell 选型，不覆盖 PWD 未定义崩溃，其修复（CONFIG_SHELL/SHELL 钉定）对本条无效。
  - **DRAFT-empty-login-identity-empty-success**：同族"OHOS 会话环境语义不可假设"（LOGNAME 空成功 vs PWD 未定义），诊断词汇不同。
- 原则挂钩：P014（环境变量与工具语义的非显性冲突——消费方须显式管理环境而非依赖继承）。
