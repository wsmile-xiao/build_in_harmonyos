# E103 — OpenHarmony 平台 adjtime 函数缺失

## 错误特征

编译时报错：
```
error: 'adjtime' was not declared in this scope
undefined reference to `adjtime'
```

典型场景：编译时间同步软件（htpdate、ntpdate、chrony 等）时遇到。

## 触发条件
- 构建系统: 任意（Makefile、autotools、cmake）
- 阶段: compilation 或 linking
- 平台: OpenHarmony/HarmonyOS

## 根因分析

OpenHarmony 使用 `adjtimex` syscall 替代 POSIX 标准的 `adjtime` 函数。`adjtime` 函数在 OpenHarmony 的 libc 中不存在，导致编译失败。

`adjtime` 是 POSIX 标准函数，用于逐步调整系统时间。OpenHarmony 选择使用 Linux 的 `adjtimex` syscall，提供更精细的时间控制能力。

## 解决方案

### 推荐方案

添加 OpenHarmony 兼容性补丁，用 `adjtimex` 替换 `adjtime`：

```c
#ifdef __OHOS__
#define adjtime(tv, oldtv) adjtimex_compat(tv)
static inline int adjtimex_compat(const struct timeval *tv) {
    struct timex txc = {0};
    txc.modes = ADJ_OFFSET_SINGLESHOT;
    txc.offset = (long long)tv->tv_sec * 1000000LL + tv->tv_usec;
    return adjtimex(&txc);
}
#endif
```

补丁要点：
1. 使用 `#ifdef __OHOS__` 守卫，不影响其他平台
2. `ADJ_OFFSET_SINGLESHOT` 模式实现 adjtime 的逐步调整语义
3. 时间单位转换：秒+微秒 → 微秒

### 禁止做法
- ❌ 使用 `--build/--host/--target` 参数绕过平台检测（无法解决函数缺失问题）
- ❌ 直接删除 adjtime 相关代码（会破坏软件功能）

## 验证
```bash
# 编译验证
make CC=clang CFLAGS="-D__OHOS__"

# 功能验证
~/usr/local/sbin/htpdate -v
```

## 关联条目
- 相关: R8（源码四不准则）
- 受影响软件: htpdate, ntpdate, chrony, ntp
