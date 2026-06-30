# E081: getpass() 函数缺失

## 问题描述
HarmonyOS musl libc 不提供 getpass() 函数，导致编译时链接失败。

## 错误示例
```
undefined symbol: getpass
```

## 根因分析
- HarmonyOS 使用 musl libc
- musl libc 不提供已废弃的 POSIX getpass() 函数
- 该函数在 POSIX.1-2008 中已标记为 obsolete

## 解决方案
创建 getpass_compat.c 兼容实现：

```c
#include <stdio.h>
#include <termios.h>
#include <unistd.h>

char *getpass(const char *prompt) {
    static char password[128];
    struct termios oldt, newt;
    
    // 禁用回显
    tcgetattr(STDIN_FILENO, &oldt);
    newt = oldt;
    newt.c_lflag &= ~(ECHO);
    tcsetattr(STDIN_FILENO, TCSANOW, &newt);
    
    // 读取密码
    if (prompt) fprintf(stderr, "%s", prompt);
    fgets(password, sizeof(password), stdin);
    
    // 恢回显
    tcsetattr(STDIN_FILENO, TCSANOW, &oldt);
    
    // 移除换行符
    char *nl = strchr(password, "
");
    if (nl) *nl = 0;
    
    return password;
}
```

## 适用场景
- 使用 getpass() 的密码工具（apg, passwd utilities）
- 需要安全密码输入的程序

## 平台限制
- 仅适用于 HarmonyOS musl libc 环境
- 不适用于 glibc 环境（glibc 提供 getpass）

## 相关软件
- apg (Automated Password Generator)
- passwd utilities
- 其他密码输入工具

## 状态
草稿，待主编审核合并
