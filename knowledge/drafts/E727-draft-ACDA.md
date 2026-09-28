# E727: OHOS bionic 缺废弃 POSIX getwd()，替换为标准 getcwd()

## 错误特征

```
undefined symbol: getwd
undefined reference to getwd
implicit declaration of function 'getwd'
```

链接/编译阶段报 getwd 符号缺失或隐式声明。典型日志：

```
ld.lld: error: undefined symbol: getwd
clang-15: error: linker command failed with exit code 1
```

## 触发条件

- 遗留 C 源码（1990-2000 年代）在非 Windows 分支使用 `getwd()` 获取当前工作目录
- 典型写法：
  ```c
  #ifdef _WIN32
  #include <io.h>
  #include <direct.h>
  #define GETWD(x) getcwd(x,MAX_LINE)
  #else
  extern char *getwd();
  #define GETWD(x) getwd(x)
  #endif
  ```
- 在 OHOS（bionic libc）或 musl 环境下编译链接

## 根因

`getwd()` 是 POSIX 标记为废弃的旧 API（XPG/BSD 遗留），其缓冲区不携带长度参数，存在溢出风险。OHOS bionic libc 不实现此函数，导致链接期 `undefined symbol: getwd`。

与 E093（musl 缺 getpass GNU 扩展）同属"libc 缺失函数"类，但：
- getwd 是 POSIX 废弃 API（有标准替代 getcwd），getpass 是 GNU 扩展（无标准替代）
- getwd 直接替换为标准函数即可，getpass 需自实现或禁用功能
- 触发阶段：getwd 多为链接期 undefined symbol；getpass 多为编译期 implicit declaration

## 解决方案

替换为标准 `getcwd(x, size)`，并补充 `#include <unistd.h>`：

```c
/* 修改前 */
extern char *getwd();
#define GETWD(x) getwd(x)

/* 修改后 */
#include <unistd.h>
#define GETWD(x) getcwd(x,MAX_LINE)
```

此修改与 `#ifdef _WIN32` 分支的 `getcwd(x,MAX_LINE)` 写法保持一致，跨平台行为统一。

## 验证证据

postmark 1.53 适配（2026-09-26）：
- 修复前：`ld.lld: error: undefined symbol: getwd` → conan create G2 FAIL
- 修复后：`clang -O2 -g -Wall -c postmark-1.53.c` 通过（仅 deprecated 类警告），conan create G2 PASS，test_package 4 项断言全过
- 补丁：`archives/p/postmark/1.53/patches/0001-postmark-1.53.c.patch`

```bash
# 验证命令
grep -rn "getwd" src/ lib/ 2>/dev/null | head -5
clang -c postmark-1.53.c -o postmark.o   # 修改后编译通过
```

## 适用边界

- ✅ 适用于：使用 getwd() 的遗留 C 程序在 OHOS/musl/bionic 环境编译
- ✅ 适用于：源码中 GETWD 宏封装场景（一处宏修改全项目生效）
- ❌ 不适用于：代码对 getwd 返回的 char* 依赖特定语义（getcwd 语义一致，风险低）
- ❌ 不适用于：需要 getwd 的精确历史行为（无）

## 与既有条目关系

- similar_to: E093（musl 缺 getpass GNU 扩展）——同属 libc 缺失函数类，但 getwd 是 POSIX 废弃 API、方案为标准替换，getpass 是 GNU 扩展、方案为自实现/禁用
