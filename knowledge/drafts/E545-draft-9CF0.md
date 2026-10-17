# E545: OHOS 不支持 GNU error.h

## 问题描述
OHOS 平台不提供 GNU 扩展库中的 `error.h` 和 `error()` 函数，导致依赖它们的软件编译失败。

## 错误特征
```
fatal error: error.h: No such file or directory
implicit declaration of function 'error'
undefined reference to `error'
```

## 根本原因
`error.h` 是 GNU C Library (glibc) 的扩展，不属于 POSIX 标准。OHOS 使用的 C 库不包含此扩展。

## 解决方案

### 方法：替换为标准库函数

1. **移除 error.h**
```c
// 删除
#include <error.h>

// 添加标准头文件
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
```

2. **替换 error() 调用**

原函数签名：`void error(int status, int errnum, const char *format, ...)`
- `status`: 非零时调用 exit(status)
- `errnum`: 非零时打印 strerror(errnum)
- `format`: printf 风格格式字符串

替换规则：
```c
// 情况 1: 只打印消息，不退出
error(0, 0, "message");
// →
fprintf(stderr, "message\n");

// 情况 2: 打印消息并退出
error(1, 0, "message");
// →
do { fprintf(stderr, "message\n"); exit(1); } while(0);

// 情况 3: 打印消息 + errno + 退出
error(1, errno, "Cannot open file");
// →
do { fprintf(stderr, "Cannot open file: %s\n", strerror(errno)); exit(1); } while(0);
```

## 实际案例

**ltrace 0.7.3** - 7 个文件需要替换：
- read_config_file.c
- expr.c
- zero.c
- 等

## 验证
```bash
# 检查是否还有 error.h 引用
grep -r "error\.h" .
grep -r "error(" . | grep -v "stderr"
```

## 相关知识
- E123: 其他 GNU 扩展兼容性问题
