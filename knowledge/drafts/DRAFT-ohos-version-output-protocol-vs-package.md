# DRAFT-ohos-version-output-protocol-vs-package — CLI `--version` 输出协议版本≠包版本

> Contributor: 7B6E / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-version-output-protocol-vs-package`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `E530` | 图谱 | 消费者契约测试里"钉死协议版本常量与公开结构体 offsetof/sizeof" | 那是**主动核对**协议版本以保 ABI 兼容；本条是 **CLI `--version` 输出语义**的断言陷阱——按包版本断言会误判失败 |
| `E251` | 图谱 | NLP 词典/分词数据包适配模式 | 数据包内容层面，无关版本断言 |

**全库查证**：对 `协议版本.*包版本` / `--version.*(协议|不是包版本)` /
`版本.*不是包版本` 等关键词 grep —— 仅 `E530` 命中"协议版本常量"（语境不同，
见上），**无一条讲"`--version` 输出协议版本 vs 包版本的断言陷阱"**。

## Scope（何时用）

在 test_package 里对 CLI 工具做 `--version` 断言，且上游存在"版本漂移"——
`--version` 输出的不是发布版本。

**实例**（eudev 3.2.14 实测）：

```console
$ udevadm --version
251
```

`251` 是 **udev 协议版本**（对应 systemd 251），而 conan **包版本**是 **3.2.14**
（eudev 自身的发布版本）。两者不同。

## Symptom

```console
[test_package] FAILED: udevadm --version 不包含 "3.2.14"
[test_package] FAILED: 版本断言失败（期望 3.2.14，实际 251）
```

工具本身完全正常，只是 `--version` 输出的是另一个版本号。

## Root Cause

很多系统工具/库的 `--version` 输出"上游协议版本 / 内部接口版本"，与被打包
进 conan 的"包版本"不是一回事。符号"版本"的语义随上游而异，不能想当然等于
包版本。

## Recommended Solution

### 主方案（priority 1）— observe-then-assert-semantics

1. **先实测** `--version` 的真实输出，判断其语义；
2. 断言内容改为"**成功退出 + 输出非空**"，或"输出含**经实测确认**的版本标记"
   （如 eudev 断言 `251` 而非 `3.2.14`）；
3. 把该版本的语义写进 test_package 注释，防后人误改回包版本断言。

### 回退方案（priority 2）— assert-exit-code-and-nonempty

无法确证输出语义时，退化为最弱但稳的断言：exit 0 + 输出非空。

### 禁止做法

- ❌ 未实测就按包版本断言 `--version` —— 一旦版本漂移即误判失败；
- ❌ 为让断言通过而改包版本 / 伪造输出 —— 把测试缺陷转嫁到产物上。

## 实测证据（2026-09-16，eudev 3.2.14）

| 项 | 结果 |
|---|---|
| `udevadm --version` | 输出 `251`（udev 协议版本，对应 systemd 251）|
| conan 包版本 | `3.2.14`（eudev 发布版本）|
| test_package 处置 | 断言"成功退出 + 输出 251"，并在 conanfile/test 注释写明 251 的协议语义 |
| 结果 | 4 项消费者断言全过，`udevadm --version` / `--help` 均真实运行 |

## 测试覆盖边界

本条只处理 "CLI `--version` 输出语义的断言陷阱"。区分相邻情形：

- 消费者契约里的协议版本核对 → `E530`；
- 数据包内容适配 → `E251`。

## 关联条目

- 相似：`E530`（协议版本常量）、`E251`（数据包模式）
- 差异：见上方差异化定位表
