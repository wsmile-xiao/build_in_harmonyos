# DRAFT-theora-ogg-uint64-type-gap

## 新版 Xiph 库使用 ogg_uint64_t 而 ogg/1.1.1 老包线缺失该 typedef

### 错误特征（可机器匹配）

```
lib/state.c:391:11: error: unknown type name 'ogg_uint64_t'; did you mean 'ogg_int64_t'?
note: 'ogg_int64_t' declared here (ogg/config_types.h:9)
```

### 根因

- ogg/1.1.1（2004 老 ogg 包线）的 Linux 路径 `config_types.h` 只定义六个类型
  （ogg_int16/uint16/int32/uint32/int64_t），**无 ogg_uint64_t**
- ogg_uint64_t 是 libogg 1.3.x 才加入（1.3 的 config_types.h 与 os_types.h 的
  MinGW 分支）
- theora 1.2.0（2025-03 发布）在 lib/state.c 的 border-mask 计算用了它——
  这正是其 configure.ac `ogg >= 1.3.4` 版本闸的真实根因之一

### 解法

静态补丁替换为 C99 `uint64_t` + 显式 `#include <stdint.h>`（全库仅两行受影响，
移位转换一并改无符号避免有符号溢出 UB）。**先决核对**：用 llvm-nm -D 逐符号核对
theora 用到的全部 ogg 符号在 ogg 1.1.1 符号表存在（全部存在——类型缺口是
编译期唯一断点，勿误判为依赖缺失走 dependency_missing 止损）。

### 降级方案

若 ogg_uint64_t 泄漏进公共头（无法局部替换）：改依赖 libogg/1.3.x 新包线，
或为 ogg/1.1.1 追加 typedef（侵入公共头，不推荐）。

### 红线

- 禁止因"上游要 ogg>=1.3.4"直接判 dependency_missing 止损——实际符号面兼容，
  仅一个 typedef 缺口，两行补丁可修
- 禁止用 --host 绕过 configure 版本闸（E007 系铁律）——走 XIPH_PATH_OGG
  fallback（--with-ogg + --disable-oggtest）是上游文档化的正规路径

### 复用面

Xiph 生态配老 ogg 包线的场景：theora（本例）/ speex / opus-file /
vorbis-tools 等任何引用 ogg_uint64_t 的新版 Xiph 库。同类模式：
"新版库配老版本同名依赖包线"的类型断层（非 Xiph 特有的抽象模式）。

### 验证

- CI 构建 #50742（PR #10978）：L0/L1 门禁 + Conan test_package 全过
- 本地 conan create：make check 9/9 + 消费者往返 smoke 通过
