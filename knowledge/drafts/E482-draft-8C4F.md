# E482 — OHOS libc 不传递包含 sys/types.h，uint 未定义编译失败

## 错误特征
- `unknown type name 'uint'`
- `tools.h: ... 'uint' ... not declared`
- `error: unknown type name 'uint'`

## 触发条件
- 构建系统: autotools
- 阶段: compilation

## 根因分析
上游代码在非 WIN32 分支依赖系统头文件传递提供 typedef uint（glibc 由 stdio/dirent 等传递包含 sys/types.h）。OHOS musl-libc 类实现不传递包含 sys/types.h，uint 未定义即报 unknown type name。lbreakouthd tools.h 仅在 `#ifdef WIN32` 下 `typedef uint32_t uint`。

## 解决方案

### 推荐方案
在依赖 uint 的头文件中显式 `#include <sys/types.h>`（OHOS libc 定义 `typedef unsigned u_int, uint;`），或将 uint 替换为 uint32_t/stdint 类型。

### 禁止做法
- （草稿，待主编合入时补充）

## 验证
```bash
```

## 关联条目
- 相关: （无）
