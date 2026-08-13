# E216 — OHOS musl libc 无 glibc MAX_INPUT 宏导致编译失败

## 错误特征
```
gdbus/object.c:138:11: error: use of undeclared identifier 'MAX_INPUT'
        char str[MAX_INPUT];
```

## 触发条件
- 构建系统: autotools (bluez 5.79 等)
- 阶段: compilation
- 平台: OHOS/musl libc

## 根因分析
`MAX_INPUT` 是 glibc 提供的宏（通常来自 limits.h），OHOS musl libc 不定义该宏，导致使用它的源文件编译失败。glibc 会自动包含相关头文件，但 musl 更严格。

## 解决方案

### 推荐方案
在源文件中使用 `_POSIX_MAX_INPUT` 兼容定义（与 musl 提供的 POSIX 常量一致）：
```c
#ifndef MAX_INPUT
#define MAX_INPUT _POSIX_MAX_INPUT
#endif
```
`_POSIX_MAX_INPUT` 在 limits.h 中定义为 255，glib.h 传递引入 limits.h 即可用。

### 禁止做法
- ❌ 硬编码魔数（如 4096）
- ❌ 删除使用 MAX_INPUT 的代码（功能缺失）

## 验证
```bash
grep -rn "MAX_INPUT" gdbus/object.c | head -1
make client/bluetoothctl   # 修复后应编译通过
```

## 关联条目
- 相关: E032（musl 头文件兼容类）
