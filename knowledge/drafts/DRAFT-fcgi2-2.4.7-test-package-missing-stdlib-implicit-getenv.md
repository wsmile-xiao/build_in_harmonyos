# DRAFT-fcgi2-2.4.7-test-package-missing-stdlib-implicit-getenv — conan-init 模板 test_package 消费者测试源缺 stdlib.h 致 getenv 隐式声明被 ISO C99 判错

- 触发事件：fcgi2 2.4.7 适配，conan-verify G2 首跑 test_package 即败
- 路径：Path B（知识库扩展）
- 编号：DRAFT-fcgi2-2.4.7-test-package-missing-stdlib-implicit-getenv

## 现象

conan-init 生成的 test_package/test.c 模板默认只包含 stdio.h；消费者测试
使用 `getenv()` 时，clang（OHOS 交叉工具链，ISO C99 模式）报：

```
test.c:17:24: warning: call to undeclared function 'getenv'; ISO C99 and later do not
                 support implicit function declarations [-Wimplicit-function-declaration]
test.c:17:15: error: incompatible integer to pointer conversion initializing 'char *' with
                 an expression of type 'int' [-Wint-conversion]
```

`conan create` 的 test_package test() 阶段失败，conan-verify G2 门禁红。

## 根因

C 标准中 `getenv()` 声明于 `<stdlib.h>`。模板 test.c 头文件包含集过窄（仅
stdio.h），导致 getenv 隐式声明；clang 在 ISO C99 模式把隐式函数声明视为
错误——隐式声明返回 int，与 `char *method = getenv(...)` 的指针初始化不兼容。

## 修复

按"实际调用即包含"原则补全消费者测试源的标准头：

```c
#include <stdlib.h>   /* getenv/strtol/malloc/free */
#include <string.h>   /* strcmp/strlen/memset     */
#include <unistd.h>   /* getpid 等 unistd 函数     */
```

## 验证（fcgi2 2.4.7 实测）

- 补头前：G2 FAIL（上述编译错误，conan-create.log 留档）。
- 补头后：conan-verify G2 PASS（G0-G4 + L2/L4/L5 全过）；
- 消费者用例（clang 编译 + 链接 libfcgi + CGI 回退模式运行）通过，
  输出 `OHOS_FCGI_TEST_OK` / `fcgi-ok` 断言，退出码 0。

## 与既有条目的区分（查重结论）

| 条目 | 层面 | 根因 | 与本条差异 |
|---|---|---|---|
| E308 | 门禁发现 | 模板 .c.in/.cpp.in 后缀不被 CI L0c find 识别 | 本条目=头文件缺失致编译错，非后缀识别 |
| E081/E093 | libc 符号 | musl 缺 secure_getenv/getpass（源码调用不存在函数） | 本条目=标准 C 函数缺头文件声明，符号本身存在 |
| DRAFT-7316-quirc | 测试策略 | 无测试素材时自研编码器构造输入 | 本条目=消费者测试源自身标准头完整性 |

七轴：exact_duplicate=否；causal_duplicate=否；trigger_overlap=部分（同属
conan test_package 阶段）；solution_overlap=否；combination_novelty=是；
boundary_novelty=是（消费者测试源必须完整包含其实际调用的标准库头）；
test_migration_novelty=否。

## 适用范围与反例

- 适用：所有以 C 语言编写 test_package 消费者测试的 Conan 配方；模板仅含
  stdio.h 且测试使用 getenv/strtol/malloc 等函数的场景。
- 反例：纯 C++ 测试源；模板已含所需头；编译器未启用严格隐式声明检查
  （隐式声明仅为 warning 时不阻断）。

## 关系字段

- similar_to: E308；DRAFT-7316-quirc
- caused_by: conan-init 模板 test.c 头部包含集过窄
- prerequisite_of: 无
- conflicts_with: 无

## 来源

- 库：fcgi2 2.4.7（task fcgi2-2.4.7-r01-pc2-22-20260921T071217Z）
- 归档：archives/f/fcgi2/2.4.7/（conanfile.py/test_package）
- 证据：archives/f/fcgi2/2.4.7/reports/conan-create.log（G2 首跑错误）、
  conan-verify-report.md（补头后全过）
