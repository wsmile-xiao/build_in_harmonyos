# E601 — glibc 专属头文件（如 ieee754.h）在 OHOS musl 系 libc 缺失

## 错误特征

上游测试/工具源码包含 glibc 专属头时，OHOS（musl 系 libc）编译直接失败：

```
test.cpp:14:10: fatal error: 'ieee754.h' file not found
```

`find` 全盘检索确认 OHOS sysroot（`aarch64-linux-ohos/usr/include`）不提供该头。

## 触发条件

- 构建系统: 任意（Makefile/CMake/autotools），编译期 include glibc 专属头
- 阶段: compilation
- 环境: OHOS（musl 系 libc）；glibc Linux 本机编译不报错

## 根因分析

部分上游代码直接使用 glibc 提供的 `ieee754_float` 位域联合（`union { float f; struct { unsigned mantissa:23, exponent:8, negative:1; } ieee; }`）操作 IEEE-754 位布局。OHOS libc 不提供 `<ieee754.h>`。正确修复不是换 libc 或伪造头，而是把用到的位域布局内联为可移植定义，保持字段名与位宽一致，改动面最小。

## 解决方案

### 推荐方案

移除 glibc 专属 include，在源码内内联等价位域 union（字段名与 glibc 相同，调用方逻辑零改动）：

```cpp
#include <math.h>
/* 替换 #include <ieee754.h> */
union ieee754_float {
  float f;
  struct {
    unsigned int mantissa:23;
    unsigned int exponent:8;
    unsigned int negative:1;
  } ieee;
};
```

symfpu 0.0-git.40bdec00 实测通过：24 项上游测试全部运行，仅 max/min ±0 平局 6 处失配（属上游 SMT-LIB vs C fmaxf 语义差异，非本修复问题）。

### 禁止做法

- ❌ 在 sysroot 手写/注入 glibc 专属头（污染共享环境，违反基线纪律）
- ❌ 只注释掉使用位域的逻辑（破坏测试能力）

## 验证

```bash
make -C symfpu CXX=clang++ -j1                 # 构建通过
./test --allTests --specialValues              # 测试运行，无编译期头缺失
```