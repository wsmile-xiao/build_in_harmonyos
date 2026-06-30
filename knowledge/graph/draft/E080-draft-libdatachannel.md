# E080: OHOS BSD类型缺失

## 问题描述
OpenHarmony系统头文件不含BSD风格类型定义：`u_int`, `u_long`, `u_char`, `caddr_t`。
这些类型在BSD系统（FreeBSD/NetBSD/OpenBSD）中由 `<sys/types.h>` 提供，但POSIX标准不要求。

## 影响范围
任何内嵌BSD代码的C库（usrsctp、libevent、ncurses等）在OHOS上编译时会报 `unknown type name` 错误。

## 解决方案
1. 创建 `ohos_compat.h` 头文件，定义缺失的BSD类型和宏（IFNAMSIZ/timercmp/timeradd/timersub）
2. cmake项目：`CMAKE_C_FLAGS=-include ohos_compat.h` 注入
3. autotools项目：`CFLAGS=-include ohos_compat.h` 注入
4. **⚠️ 关键陷阱**：compat类型定义不能放在 `#if defined(__APPLE__)` 块内！OHOS不定义 `__APPLE__`，整个块被跳过

## 典型错误
```
deps/usrsctp/usrsctplib/user_socketvar.h:47:5: error: unknown type name 'u_int'
deps/usrsctp/usrsctplib/user_socketvar.h:48:5: error: unknown type name 'u_long'
```

## 参考
- libdatachannel 0.24.0 编译记录