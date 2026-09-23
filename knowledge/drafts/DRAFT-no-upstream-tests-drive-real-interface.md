# DRAFT-no-upstream-tests-drive-real-interface — 上游没有测试套件时：先取证"确实没有"，再驱动其真实对外接口

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-12
> **Severity**: 🟡 medium | **Category**: testing / conan / autotools / protocol / verification

## 相关既有条目（互补，非重复）

| 既有条目 | 关系 |
|---------|------|
| **E530** | 讲 X11 客户端库**无法**驱动真实接口（需 X server，CI 无 Xvfb）时，退化为「强类型活重定位 + ABI 布局固定」的消费者契约测试。本条讲**能**驱动真实接口时（协议 / IPC / CLI 型程序）应当真去驱动它 —— 两者是同一问题的**两个分支**：E530 = 驱动不了怎么办；本条 = 驱动得了怎么驱动。共同底线：**都禁止空 `test_package` 假装测过** |

> 查重（2026-09-12）：`Assuan` / `GETPIN` / `GETINFO` 在 `knowledge/` 命中 **0**；`上游.*无.*测试` 命中的 24 条中，仅 `graph/index.tsv`（索引）提到协议接口，**无任何条目**讲"改测真实协议接口"这一做法。

## Scope（何时用）

适配第三方库时，`make check` 看似成功、但你想确认**它到底测了什么** —— 尤其怀疑该库上游压根没有测试套件。

## 根因：`make check` 常常什么都不做

因为该库上游**根本没有测试套件**。此时两种错误做法很常见。

### 错误一：不实声明

把"没跑测试"说成「**上游测试需交互环境故未启用**」—— 这个说法**暗示测试套件存在**，属**不实**。

实测 pinentry 1.3.3：

```bash
$ tar tf pinentry-1.3.3.tar.bz2 | grep -i test     # → 0 条
$ grep -nA4 '^SUBDIRS' Makefile.am                # :114 → 不含 tests
$ grep -rn '^TESTS =\|check_PROGRAMS' .           # → 无任何匹配
```

→ 不是"未启用"，而是**上游没有**。1.3.2 同样如此。

### 错误二：空壳 test_package

只断言"文件存在 / `--version` 能跑"，不触碰任何功能路径 → R34 意义上的**假成功**。

### ⚠️ 关键认知

> **"上游有没有测试套件"本身必须先取证** —— 不能凭 `make check` 是否报错来推断。

因为 automake 的 `check` 目标在无 `TESTS=` 时**成功退出**（`Nothing to be done for 'check'`）—— 看起来"通过"。

## 方案：四步

### ① 取证"没有"

三种方式缺一不可：

```bash
tar tf <pkg>.tar.* | grep -iE "test|check"          # 条目数
grep -nA4 '^SUBDIRS' Makefile.am                    # 是否含 tests
grep -rn '^TESTS =\|check_PROGRAMS\|check-local' .  # 是否有目标
```

把**取证命令与输出**写进 `manifest` / `test_note` / PR 描述 —— 把"未启用"改成「**上游不存在（附证据）**」。这是诚实性问题（R34）。

> 另需区分：**tarball 剥离了 tests（仅 git 里有）** vs **上游就没有 tests** —— 两种都要先取证，处置不同。

### ② 找真实对外接口

读源码 / 文档确定接口形态，**接口就是被测面**：

| 形态 | 怎么找 |
|------|-------|
| **协议 / IPC** | 找命令表、消息定义（本例：pinentry 的 Assuan 命令表在 `pinentry/pinentry.c`）|
| **CLI** | stdin / stdout / 退出码 |
| **库 API** | dlopen + dlsym 后调用真实函数 |

```bash
grep -oE '"[A-Z_]{3,}"' <src>/**/*.c | sort -u     # 协议型：抽命令表
```

### ③ 构造功能测试：三类断言缺一即偏薄

- **正常路径**：真实输入 → 断言真实输出（**数据行**，不是 `"OK"`）
- **错误路径**：非法命令 / 非法参数 → 断言真实错误码 / 错误文本
- **状态 / 交互路径**：多步交互（需 pty 者见草稿B）

输出**机器可解析的汇总行**，供 `test_package` 断言，而不是让人肉读日志：

```
RESULT: passed=N failed=M skipped=K
```

### ④ 诚实区分 FAIL / SKIP

环境不具备（无终端、无设备）的用例标 **SKIP 并计数**，**绝不并入 passed**。`test_package` 侧：

- `failed > 0` → **报错**
- `passed == 0` → **报错**
- `skipped > 0` → **告警**（让"没测到"可见）

### 记录口径

把"上游无测试套件"的证据 + 替代测试的覆盖面一起写进 `test_note`，让后续维护者**一眼看懂测了什么、没测什么**。

## 备选（fallback）

当真实接口**确实无法驱动**时（典型：X11 客户端需 X server，CI 无 Xvfb / 无显示设备），退化为**消费者契约测试**：对每个导出符号做**强类型活重定位**（`__typeof__(&name)` + 取地址，链接期即校验签名与存在性），并用 `offsetof` / `sizeof` 钉死公开结构体布局与协议版本常量 —— 详见 **E530**（本条不重复其细节）。

> 注意：退化方案仍**禁止**空 `test_package`（只验证链接不算测过）。

## 禁止

- ❌ **"上游测试需交互环境，故未启用"** —— 该表述**暗示测试套件存在**。实测 pinentry tarball 内 test 条目 0 条、无 `TESTS=` 目标 —— 是**上游没有**，不是"未启用"；正确做法是附取证输出并说明替代测试
- ❌ **把 `make check` 成功当作"有测试/测试通过"** —— automake 在该包无 `TESTS=` 时 `check` 目标**静默成功**（`Nothing to be done for 'check'`），退出码 0 **不代表测过**
- ❌ **只断言"文件存在"/"`--version` 能跑"就算功能测试** —— 存在性断言不触碰任何功能路径，接口退化时无声（与 E530 所述"空 test_package 只验证链接"同源问题）

## 实证

- **pinentry/1.3.3（PR #9638）**：
  - 实测官方 tarball **不含 `tests/`**（tar 内 test 条目 0；`SUBDIRS`(Makefile.am:114) 无 tests；全树无 `TESTS=`/`check_PROGRAMS`）→ `make check` 为 **no-op**
  - 改为驱动其**真实对外接口** Assuan 协议，构造 **16 项**断言（`GETINFO version`/`pid`、未知命令 `ERR`、参数错误 `ERR`、`GETPIN` 返回所输 PIN、`CONFIRM`、`MESSAGE`）× 2 前端
  - 本地 **16/16 通过**；CI 无终端时 **3 项如实标 SKIP**（`RESULT: passed=13 failed=0 skipped=3`）
  - 此前 manifest/PR 把该情况写成"上游测试需交互环境故未启用"，属**不实**，已更正为附取证输出的"上游不存在"
