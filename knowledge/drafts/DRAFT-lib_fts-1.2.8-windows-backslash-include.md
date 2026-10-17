# E-DRAFT: 上游测试源 Windows 反斜杠 include 路径在 POSIX 无法编译

- **触发实例**：lib_fts 1.2.8 适配（2026-09-27，任务 pc2-36，分支 feat/lib_fts-1.2.8）
- **错误签名**：`fatal error: '..\..\code\fts_fuzzy_match.h' file not found`
- **类别**：platform, compat, portability, build-system
- **严重度**：2（编译阶段确定性失败，修复模式固定）

## 症状

```text
tests/fuzzy_match/fts_fuzzy_match_test.cpp:12:10: fatal error:
  '..\..\code\fts_fuzzy_match.h' file not found
#include "..\..\code\fts_fuzzy_match.h"
         ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
```

## 根因

Windows 优先开发的上游项目测试源用反斜杠写相对 include
（`..\..\code\...`）。POSIX 文件系统把 `\` 当普通字符，路径无法解析。
这是源码字面路径的平台可移植缺陷，不是平台宏问题。

## 修复

最小补丁：两处 include 改为正斜杠，其余不动。

```diff
-#include "..\..\code\fts_fuzzy_match.h"
-#include "..\..\code\util\fts_timer.h"
+#include "../../code/fts_fuzzy_match.h"
+#include "../../code/util/fts_timer.h"
```

补丁用 `a/` `b/` 前缀、`patch -p1` 在干净 .orig 上验证可应用。

## 验证

```bash
clang++ -std=c++17 -O2 -I code tests/fuzzy_match/fts_fuzzy_match_test.cpp -o fts_test
# exit 0；词表运行 exit 0
conan create archives/l/lib_fts/1.2.8 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 适用边界 / 反例

- ✅ 适用：上游测试/样例源确实含反斜杠 include 或反斜杠文件路径的 POSIX 移植。
- ❌ 反例：纯 POSIX 项目无此问题；不要为不含反斜杠路径的库硬造补丁；
  不要用 `#ifdef __OHOS__` 之类平台宏绕道（R8 默认禁平台宏）。