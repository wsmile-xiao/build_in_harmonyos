# OHOS 系统路径只读/缺失：命令行工具配置路径必须可被环境变量覆盖（草稿，通用）

> **Status**: Draft（待审核 promote）｜ **severity**: `2`（medium）｜ **category**: `platform|filesystem|portability|shell`
> **对应 kv**: `knowledge/drafts/chkboot-1.3-ohos-readonly-etc-config-path-override.kv`
> **来源实例**: chkboot 1.3（5 个脚本硬编码 `source /etc/default/chkboot.conf`）｜ **方案通用性**: 与软件名无关

---

## 一、问题（错误特征）

```
$ chkboot-check                          # 上游脚本原样运行
chkboot-check: line 10: /etc/default/chkboot.conf: No such file or directory
CHKBOOT ALERT!                           ← 假告警：实际没有任何变更
cat: /: Permission denied
$ mkdir -p /etc/default                  # 想按上游文档放配置
mkdir: '/etc/default': Read-only file system
$ ls -d /var/lib /etc/issue
ls: /var/lib: No such file or directory
ls: /etc/issue: No such file or directory
```

## 二、根因

1. **系统路径只读/缺省**：OHOS 的 `/etc` 是 Read-only file system，`/etc/default/*`、`/etc/issue` 不存在且不可创建；`/var/lib` 也不存在。
2. **失败方式隐蔽（关键）**：`source` 失败不终止脚本（无 `set -e`），变量保持未设置 → `${CHKBOOT_DATA}/${CHANGES_ALERT}` 塌缩为 `/` → `[[ -s / ]]`（目录）恒为真 → 工具**假告警**，`cat /` 报权限错，退出码与真实状态无关。排查时极易误判为“脚本逻辑坏了”。
3. 因此任何“安装期写 /etc”的修法在 OHOS 上都不可能成立。

## 三、使用说明（HOW-TO）

1. **定位**：`grep -rn "/etc/\|/var/lib\|/etc/issue" <上游脚本>` 找全部硬编码系统路径。
2. **最小补丁（每处一行）**：`source /etc/default/x.conf` → `source "${X_CONF:-/etc/default/x.conf}"`（**默认值保持上游原样**）。
3. **包内提供默认配置并注入**：配置装到 `res/default/x.conf`（不要装 `/etc`）；`package_info()` 里 `self.runenv_info.define("X_CONF", os.path.join(self.package_folder, "res", "default", "x.conf"))`。
4. **对写操作加守卫**：`if [ "$?" = 1 ] && [ -w /etc/issue ]; then … >> /etc/issue; fi`（只读即干净跳过）。
5. **三步验证**：① 设 `X_CONF` → rc/语义正确；② 不设 → 与设置时结果**不同**（证明覆盖是载荷性的）；③ 全部脚本 `bash -n` 通过。

## 四、适用范围

✅ **适用**：任何从系统路径读配置 / 写状态的 CLI、守护脚本、通知前端；打包为 Conan 包且需要可重定位运行；纯脚本包与含脚本的编译型包均适用。

❌ **不适用 / 需换做法**
- 上游已有 `--config <path>` 参数 → 直接用参数，不必加环境变量
- 需要“多用户共享 /etc 配置”的语义 → OHOS 上不可能，必须改为包内相对路径并在文档里写明
- 把路径改成平台私有绝对路径（`/data/service/hnp/...`）来“修好” → 换机即失效（**E049 禁令**）

## 五、输入 / 输出定义

| 项 | 定义 |
|---|---|
| **输入·平台事实** | 目标路径可写/存在性（`mkdir -p /etc/default` rc；`/etc/issue`、`/var/lib` 是否存在） |
| **输入·上游资产** | 脚本内硬编码路径清单（grep 结果）、配置文件默认内容 |
| **输入·recipe** | `package_folder`（承载 `res/default/x.conf`）、`runenv_info` |
| **输出** | ① 补丁 `source "${X_CONF:-<上游默认>}"`；② 包内默认配置 `res/default/x.conf`；③ 设置 `X_CONF` 时工具语义正确、未设置时与上游一致；④ 文档明确 OHOS 需经 `X_CONF` 指定配置 |
| **自动判据** | `X_CONF=<好配置> <tool>` → rc=0 且无假告警；`<有变更配置>` → rc=1 且输出含变更明细；未设置且系统路径不存在 → 结果与设置时不同 |
| **失败边界** | 默认值必须 = 上游值（不得改成平台私有路径）；写系统路径的代码必须带可写性守卫 |

## 六、示例

**示例 1 — 通用补丁**
```diff
-source /etc/default/mytool.conf
+source "${MYTOOL_CONF:-/etc/default/mytool.conf}"
```

**示例 2 — Conan 注入**
```python
def package_info(self):
    self.runenv_info.define("MYTOOL_CONF",
        os.path.join(self.package_folder, "res", "default", "mytool.conf"))
```

**示例 3 — 写 /etc/issue 的守卫**
```diff
-if [ "$?" = 1 ]; then echo "$OUT" >> /etc/issue; fi
+if [ "$?" = 1 ] && [ -w /etc/issue ]; then echo "$OUT" >> /etc/issue; fi
```

**示例 4 — 本次来源实例（chkboot 1.3）**
- 现象：`chkboot-check` 假告警（未定义变量把路径塌缩成 `/`，`[[ -s / ]]` 恒真）
- 处理：`CHKBOOT_CONF=<临时配置>` → 无变更 rc=0（空输出）；有变更 rc=1 且列出变更文件与 sha512
- 配套鸿蒙特有用例：`ohos-conf-from-package-env`（PASS）、`ohos-conf-override-required`（PASS）
- 证据：`chkboot-1.3-evidence/17-runtime-repro.log`、`18-runtime-fixed.log`、`50-conan-create.log`

## 七、禁止做法

- ❌ 把配置路径 sed 成平台私有绝对路径（E049）
- ❌ 安装/运行期 `mkdir -p /etc`、`cp … /etc/`、`>> /etc/issue`（只读必失败；若被 `|| true` 吞掉则变静默失效）
- ❌ 新增代码继续 `source /etc/...` 硬编码（把平台缺陷复制到下一个包）
