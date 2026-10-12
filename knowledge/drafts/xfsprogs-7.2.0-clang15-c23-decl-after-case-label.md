# clang 15 拒绝「case 标签后声明」：声明上移 / case 加花括号

> Draft: `DRAFT-XFSPROGS-720-CLANG15-C23-DECL-AFTER-CASE-LABEL`
> Stem: `xfsprogs-7.2.0-clang15-c23-decl-after-case-label` — 与同名 `.kv` 配套
> 实例来源: xfsprogs 7.2.0 适配（补丁 `0008-io-healthmon.c.patch`）
> 关联知识: E027/E490（工具链/编译器版本差异类）

## 基本信息

- **ID**: DRAFT-XFSPROGS-720-CLANG15-C23-DECL-AFTER-CASE-LABEL
- **严重度**: 2
- **类别**: clang, compilation, portability, compat
- **触发工具**: clang
- **阶段**: compilation

## 使用说明（这份知识怎么用）

- **适用**：clang 15（OHOS SDK 固定版本）编译新式 C 代码报 `expected expression`，
  位置恰在 `case X:` 下一行是声明语句；同一 switch 的使用点报 `use of undeclared identifier`。
- **不适用**：clang≥16（已支持 C23）或使用 GCC 的项目（GCC 较新版本作为扩展支持）。
- **一次性定位**：用扫描命令找全仓命中点，不要逐个编译试错。

## 输入输出定义

- **输入**：报错定位到的声明语句 + 它所属的 case/分支。
- **输出**：声明位置调整后的源码补丁（两种等价形态：上移到函数/循环顶部，或 case 体加花括号）。
  - 约束：调整后**作用域与初始化时机语义不变**——若声明仅在单分支内使用，上移安全；
    若依赖"进入分支才初始化"（极少见），改用花括号保持原作用域。

## 错误特征（逐字实测）

```
io/healthmon.c:132:4: error: expected expression
            const size_t minsz =
            ^
io/healthmon.c:137:12: error: use of undeclared identifier 'minsz'
        if (c < minsz || errno) {
```

最小复现与模式验证（OHOS clang 15.0.4 实测）：

```
$ printf 'int g(int c){switch(c){case 1: const int x=4; return x; default: return 1;}}\n' > t.c
$ clang -c t.c             -> error: expected expression
$ clang -std=gnu11 -c t.c  -> error: expected expression
$ clang -std=gnu17 -c t.c  -> error: expected expression
$ clang -std=gnu23 -c t.c  -> error: invalid value 'gnu23'（clang15 未实现该模式）
```

即：**没有任何 -std 模式可绕过**，必须改源码。

## 根因

C23 语法允许标签后直接跟声明（declaration after label）。clang 15 的解析器仍按
"标签后必须是语句"处理，声明被当成非法表达式（`expected expression`），该声明
不进入符号表；后续使用点于是报 `use of undeclared identifier`。

上游代码在 clang≥16 开发/CI 上完全正常，属于**平台工具链版本差异**，
不是上游缺陷（不要因此给上游提 bug，除非项目声明支持 clang15）。

## 影响范围

- clang<16（含 OHOS SDK clang 15.0.4）上的所有新式 C 源码；
- 典型来源：2024+ 新增/重写的源码（内核工具、系统工具链项目）；
- 扫描命令可一次性列出候选（`case ...:` 下一行以声明关键字开头），
  避免"编译→修一处→再编译"的低效循环。

## 推荐方案

**方法**: `hoist-declaration-out-of-switch-or-brace-the-case-body`

**修法 1（首选，最小 diff）**：把声明移到函数/循环顶部：

```diff
 case 'b':
-    const size_t minsz = sizeof(struct xfs_health_monitor_event);
     errno = 0;
```

（实现里同时把 `const size_t minsz = sizeof(...);` 提到函数作用域，与其它局部变量并列。）

**修法 2（局部性强）**：给 case 体加花括号：

```diff
-case 'b':
-    const size_t minsz = sizeof(...);
-    ...
+case 'b': {
+    const size_t minsz = sizeof(...);
+    ...
+}
```

**禁止**：`-std=gnu2x`/换编译器绕过（工具链固定；且 gnu23 在 clang15 不存在）。

## 验证命令

```bash
# 最小复现（期望 expected expression）
printf 'int f(int c){switch(c){case 1: const int x=2; return x; default: return 0;}}\n' > t.c
clang -std=gnu11 -c t.c -o /dev/null

# 全仓扫描命中点
grep -rn -A1 "case [^:]*:$" --include=*.c . \
  | grep -E "^[^:]*-[[:space:]]*(const|size_t|int|struct|char|bool|unsigned|long)"
```

## 取证记录

- 包: xfsprogs 7.2.0（`archives/x/xfsprogs/7.2.0`，补丁 `0008-io-healthmon.c.patch`）
- 报错原文: 首次 `make` 日志（`io/healthmon.c:132/137`）
- 修复后: `make` RC=0；12 工具 `-V` rc=0；W3 `.ci-result.json` exit_code=0
