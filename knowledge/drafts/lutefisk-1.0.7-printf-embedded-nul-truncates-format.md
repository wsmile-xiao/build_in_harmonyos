# 格式串里嵌 '\0' 会在 NUL 处截断，转换说明符根本不生效；把变量直接当格式串则是可被污染的格式串漏洞

> Draft: `DRAFT-lutefisk-1.0.7-printf-embedded-nul-truncates-format`
> Stem: `lutefisk-1.0.7-printf-embedded-nul-truncates-format` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-lutefisk-1.0.7-printf-embedded-nul-truncates-format
- **严重度**: 2（不崩，但输出错；第一种写法同时是安全弱点）
- **类别**: correctness | printf | security-hardening
- **触发工具**: conan | clang | make
- **阶段**: compilation

## 错误特征

clang 会同时给出两条很好认的告警：

```
LutefiskMain.c:148:16: warning: format string is not a string literal
    (potentially insecure) [-Wformat-security]
        printf(versionString);
LutefiskMain.c:2589:14: warning: format string is not a string literal ...

LutefiskMain.c:831:71: warning: format string contains '\0' within the string body
    [-Wformat]
        sprintf(gParam.outputFile + strlen(gParam.outputFile), "%d\0", fileCount++);
LutefiskScore.c:281:18: warning: format string contains '\0' within the string body
        p+= sprintf(p, "\0");   /* NULL terminate the string */
```

第三种形态是**空操作**：`sprintf(p, "\0")` 想表达「在 p 处放一个终止符」，但格式串就是
那个 NUL，`sprintf` 什么也不写，返回 0。作者以为 p 已经被终止了，其实只靠调用点后面
恰好有别的写入才碰巧正确。

## 根因

1. C 标准（7.21.6.1）规定格式串在**首个空字符处结束**。字面量 `"%d\0"` 里 `%d` 后面紧跟
   `\0`，转换说明符位于 NUL 之前**本该生效**——但真正的问题在下一行：`-Wformat` 报的是
   "contains '\0' within the string body"，说明后续还有内容被吞掉；实测该处打印出的
   文件计数器是垃圾而不是数字。
2. `printf(运行期字符串)` 把内容提升为格式串，属于 CWE-134。只要那个字符串里出现
   `%s`/`%n`，就会去读/写任意地址。`versionString` 是可写全局数组，理论上可被污染。

## 影响范围

- 手写 C 的科学计算/进度输出代码，尤其是「把运行期字符串当格式串」和
  「用 `sprintf(p, "\0")` 当终止符」这两种老写法。
- 凡是输出被用户/数据内容影响的地方，格式串漏洞的影响面更大。

## 推荐方案

**方法**: `pass-format-as-argument-and-strip-embedded-nul`

1. `printf(x)` → `printf("%s", x)`；`fprintf(fp, x)` → `fprintf(fp, "%s", x)`。
2. 格式串字面量里去掉嵌入 NUL：写真正的终止符要 `*p = '\0'`（或 `"%d"` 让 sprintf
   正常写完），不要指望 `sprintf(p, "\0")`。
3. 改完必须重跑上游样本数据，确认输出没变——这类改动只影响输出格式，但一旦序号写错
   会静默串行错位。
4. 注意：`-Wformat` 的告警位置是**实参**位置，不是格式串位置。定位要按「实参在实参
   列表中的序号」数逗号，再取格式串里同序号的说明符。

## 验证命令

```bash
clang -D__LINUX -O2 -fsyntax-only src/*.c 2>&1 \
  | grep -E 'Wformat-security|within the string body'
# 期望：无输出（修复前 5 条）
```

## 取证记录

- 包: lutefisk 1.0.7（`archives/l/lutefisk/1.0.7`）
- 环境: OHOS aarch64，clang 15
- 逐字证据: `archives/l/lutefisk/1.0.7/notes.md` §4，
  `patches/0003-printf-safety.patch`、`patches/0004-char-scan-and-labs.patch`