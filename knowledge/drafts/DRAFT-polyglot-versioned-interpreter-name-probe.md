# DRAFT-polyglot-versioned-interpreter-name-probe：sh/Tcl polyglot 脚本版本化解释器探测（tclsh8.5）在仅发 tclsh8.6 的平台全入口退出

> Contributor: combat-0.8.1 适配 | Status: Draft | Updated: 2026-09-11
> Source: archives/c/combat/0.8.1

## 现象

`./dotest`（以及 bin/idl2tcl、bin/iordump、各 test/*/server.tcl）在上游
pristine 树上不进任何业务逻辑即退出：

```
This software requires Tcl 8.5 to run.
Make sure that "tclsh8.5" or "tclsh85" is in your $PATH
（exit 1）
```

平台消费环境只有 `tclsh8.6`（tcl 包 bin/ 不提供 8.5 名），24 个入口脚本
全部失效。

## 根因分析

Tcl 生态经典 sh/Tcl 双语包装结构：

```sh
#! /bin/sh
# the next line restarts using tclsh8.5 on unix \
if type tclsh8.5 > /dev/null 2>&1 ; then exec tclsh8.5 "$0" ${1+"$@"} ; fi
```

- **sh 侧**：注释不吸收行尾反斜杠，`if` 行是可执行语句（探测 8.5，失败
  则继续往下探测，最终 `exit 1`）。
- **tclsh 侧**：行尾反斜杠把 `if` 行吸收进注释块——探测行同时充当注释块
  终结符（其后才能出现可执行 Tcl 代码）。

上游 combat 0.8.1 的 24 个入口（bin/{idl2tcl,iordump} +
test/{1..11}/{dotest,server.tcl}）只探测版本化旧名 `tclsh8.5`/`tclsh85`。
归类：平台解释器命名约定差异（平台探测），非库内私有 quirk；复发面由
平台本身保证（tcl 包只发 8.6 名）。

## 解决方案

**主案**：按上游 polyglot 结构插入同构探测对（放在 8.5 探测行之后、
cygwin 分支之前，保留上游全部分支与提示文本）：

```sh
# the next line restarts using tclsh8.6 on unix \
if type tclsh8.6 > /dev/null 2>&1 ; then exec tclsh8.6 "$0" ${1+"$@"} ; fi
```

要点：

- 插入必须保持"行尾 `\` 的注释行 + 无 `\` 的 if 行"同构对——否则 sh 侧
  可执行、tclsh 重启解析时会把探测行当可执行 Tcl 语句报语法错误。
- `sh -n <dotest>` 报"语法错误"是上游 polyglot 尾部 Tcl 代码固有（sh
  会全文件解析、执行停在 exec），不是补丁引入（pristine L22 与补丁后
  L24 同一错误，行号偏移恰等于插入行数）。
- combat patch 0001 实测：24 文件每文件恰 +2 行；打补丁后 187 项上游
  用例全执行（ci-run1.log / upstream-logs）。

**fallback（退路）**：shebang 改 `#!/usr/bin/env tclsh`。诚实权衡：丢失
Windows/cygwin 分支与版本保证（env tclsh 可能解析到不兼容版本），仅作
上游结构无法保持时的退路。

## 禁止

- 禁止把上游 `tclsh8.5` 字样全文改写为 `tclsh8.6`（或 `sed
  s/tclsh8.5/tclsh8.6/g`）——丢失 8.5/85 环境回退语义与上游提示文本；
  改写属语义级修改而非能力探测扩展，环境回退不可逆、补丁不可向上游提交。

## 验证证据

前置条件：**PATH 必须先前置 tcl 包 bin（等价 conan runenv PATH）。裸
shell 无任何 tclsh（8.5/8.6/85/tclsh 均 not found），`type tclsh8.6` 亦
不命中，无法区分故障面。**（tcl 包 conan 缓存路径随设备 cache 状态变化，
可用 conan install 物化后替换。）

pristine 入口必须从 **pinned 归档**现解包（设备上任何已解压的工作副本都
可能已被补丁污染，不可作为 pristine 依据）；临时目录用后自清理：

```sh
export PATH=/storage/Users/currentUser/.conan2/p/tcla4d5206af411b/p/bin:$PATH
type tclsh8.5 || echo "tclsh8.5 MISSING（平台仅发 8.6）"
# => tclsh8.5 not found
type tclsh8.6 || echo "tclsh8.6 MISSING"    # 命中

T="${TMPDIR:-/storage/Users/currentUser/tmp}/oh-device-porting-v2/combat-0.8.1/polyglot-probe.$$.$(date +%s)"
mkdir -p "$T"
curl -sL --max-time 300 -o "$T/combat.tar.gz" \
  https://deb.debian.org/debian/pool/main/c/combat/combat_0.8.1.orig.tar.gz
echo "1923fa19f55a03f720f0444d6edffe7dad246c2c4be82453b8d2c5b4922d99a8  $T/combat.tar.gz" | sha256sum -c -
# => combat.tar.gz: OK
tar xzf "$T/combat.tar.gz" -C "$T"
cd "$T/combat-0.8.1/test/1" && ./dotest ; echo "rc=$?"
# => This software requires Tcl 8.5 to run.
#    Make sure that "tclsh8.5" or "tclsh85" is in your $PATH
#    rc=1
cd / && rm -rf "$T"   # 临时目录自清理（设备实测无残留）
```

补丁有效性反证（同设备 CI 证据）：打补丁后 24 个入口全部真实执行，187 项
上游用例运行（ci-run1.log / upstream-logs）。

## 与既有条目的增量

- E037：shebang 行 `/usr/bin/env` 缺失/不可移植——问题面限 shebang 首行。
- E049：shebang 硬编码解释器绝对路径——同限首行。
- 本条：脚本**体内** exec 重启探测行的**版本化名称**维度 + 注释续行结构
  对补丁插入点的约束；上游 shebang（`#! /bin/sh`）工作正常，故障在探测段。
  shebang 家族条目均未覆盖。
