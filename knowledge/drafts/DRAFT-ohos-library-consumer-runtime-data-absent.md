# DRAFT-ohos-library-consumer-runtime-data-absent — 库消费者需运行期数据，制品只交付头与库

> Contributor: 3D6F / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-library-consumer-runtime-data-absent`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `E251` | 图谱 | OHOS 上 **NLP/分词数据包的构建**（mecab-dict-index 索引生成、固定版本 hash、UTF-8 编码校验） | E251 是"**构建**某个词典制品"（构建期问题）；**本条是"库的消费者需要词典数据才能行使功能"**（运行期问题，且发生在**依赖库内部**）。本条的产物是*库*（pwquality），数据缺口在*依赖*（cracklib） |
| — | — | — | 全库对 `运行期数据文件` / `dictionary data` / `data files.*not shipped` 的**专项**条目命中 0（仅 1 处顺带提及）|

**全库查证**：对 `运行期数据`、`词典.*未`、`pw_dict`、`dictionary data`、
`data files.*not shipped` 等关键词 grep —— 除本条外无专讲此机制的条目。

## Scope（何时用）

一切"**库本身可用，但部分功能依赖外部运行期数据资产**"的适配与测试场景。

同类数据资产（均不随库交付，属运维期安装）：

| 领域 | 库 | 数据资产 |
|---|---|---|
| 密码强度 | cracklib | `pw_dict.pwd` / `pw_dict.pwi` |
| 拼写检查 | hunspell | 词典 `.dic` / `.aff` |
| 时区 | tzdata | 时区数据库 |
| 证书 | OpenSSL / ca-certificates | CA 证书包 |
| MIME | shared-mime-info | MIME 数据库 |

**在消费者测试里最突出**：测试跑在构建机/CI 上，这些数据通常未安装 →
**功能测试会假失败**。

## Symptom

库**编译链接全部正常**，直到**运行期**调用到相关路径才失败（示例为 pwquality）：

```console
FAIL: strong password rejected: score=-22 msg=The password fails the dictionary check
FAIL: pwquality_generate rc=-24
/__pkg_prefix__/share/cracklib/pw_dict.pwd: No such file or directory
```

错误码映射（pwquality）：

| 码 | 含义 | 与数据缺口的关系 |
|---|---|---|
| **-22** `PWQ_ERROR_CRACKLIB_CHECK` | 词典检查失败 | **直接**因词典缺失 |
| **-24** `PWQ_ERROR_GENERATION_FAILED` | 生成失败 | **级联**：候选密码过不了词典检查 |

> ⚠️ 两处误导点：
> ① 症状出现在**运行期**且发生在**依赖库内部**，容易误判为"本适配的库坏了/打包错了"；
> ② 报错路径里的 `__pkg_prefix__` 是**构建期占位符**未替换（实测该串来自
>    **pwquality 自身**的库，cracklib 库内无此串），会让报错看起来更"像 bug"。

## Root Cause

cracklib 的 `FascistCheck` 需要**已编译的词典**才能在运行期做词典检查。
而制品仓的 cracklib 包是常规 C 库交付形态——**只含头与库**（实测
`find <pkg> -name 'pw_dict*'` 无结果）。词典属**独立的数据包/运行期资产**。

于是：库**在**、头**在**、链接**正常**，失败源于**数据**而非符号。

## Recommended Solution

### 主方案（priority 1）— 探测 + 隔离 + 如实申报（三步）

1. **探测并固化**：以默认设置调用该功能，断言必须得到**预期错误码**
   （本例 `-22`），把"环境无词典"这一事实写进断言，而非任其造成泛化失败：

   ```c
   int rc = pwquality_check(pwq, "Str0ng!Password#2024", NULL, "alice", &aux);
   assert(rc == PWQ_ERROR_CRACKLIB_CHECK);   /* 固化数据缺口 */
   ```

2. **关闭该功能后验证其余能力**：

   ```c
   pwquality_set_int_value(pwq, PWQ_SETTING_DICT_CHECK, 0);
   rc = pwquality_check(...);   /* 实测 score=100，须通过 */
   ```

3. **如实申报**：在 `notes.md` / `manifest.yaml` 写明该功能在当前环境不可达及原因，
   并说明**安装词典后即完整可用**——**不得**据此判定适配失败或删除断言。

**命令行工具同理**——优先选用**不依赖该数据**的真实代码路径：
`pwscore` 的长度检查**先于**词典检查（可用过短密码验证真实路径）；
`pwmake` 的**用法路径**不碰词典（无参 → rc=3、非数字 → rc=4）。
对确实需要数据的路径，则断言其**预期失败**。

### 回退方案（priority 2）— 在测试环境真正提供数据资产

若测试**必须**覆盖完整路径（要验证词典检查本身确实工作），须在测试环境真正提供
数据（安装词典包，或由另一制品条目交付并引为测试依赖）。
代价是测试环境依赖变重、且数据资产本身也需适配与发布。

### 禁止做法

- ❌ 因词典/数据缺失就判定"适配失败/打包错误/库有 bug"并去改库代码或打包
  ——库、头、链接均正常，改代码造不出词典；
- ❌ 静默跳过该测试——会使"数据缺失"与"功能正常"在记录上无差别（违反 R51）。

## 实测证据（2026-09-16，pwquality 1.4.5 适配）

| 项 | 结果 |
|---|---|
| 默认设置（`dict_check=1`）| `-22`（`PWQ_ERROR_CRACKLIB_CHECK`）|
| `pwquality_generate` | `-24`（级联：`PWQ_ERROR_GENERATION_FAILED`）|
| cracklib 包内词典 | **无**（`find` 无 `pw_dict*`）|
| 系统词典 | **无**（无 `/usr/share/cracklib/`）|
| 关闭 `dict_check` 后 | 强密码 **score=100**；生成密码长度 14 且回灌校验 **score=43** |
| CLI | `pwscore` 长度检查触发；`pwmake` 用法路径 rc=3 / rc=4 |
| 处置 | 断言固化 -22 + 关闭 dict_check 验证其余 + notes/manifest 如实申报 |

## 测试覆盖边界

本条处理"**库消费者需运行期数据**"。区分相邻情形：

- **构建**某个词典/数据包制品 → `E251`；
- 依赖**符号**未实现（库为空壳）→ `DRAFT-ohos-dependency-library-missing-own-symbols`；
- 依赖库整体缺失 → `E241` / `E305` 族。

## 关联条目

- 相似：`E251`（构建词典制品）
- 差异：见上方差异化定位表
