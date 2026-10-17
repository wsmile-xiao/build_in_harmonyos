# OHOS libc 缺失 glibc 遗留函数 gcvt() 的可移植替换

> 草稿出处：jsonparse-cpp 1.00（上游 liufeigit/jsonParse v1.00）适配 R01，2026-09-26
> 对应 .kv：`DRAFT-jsonparse-cpp-1.00-ohos-libc-gcvt-missing-snprintf-float-string.kv`

## 问题

上游 `object.c` 的 `__toFloatString()` 用 `gcvt(d, 30, str)` 做 double→字符串。
`gcvt()` 是 glibc 遗留扩展（SVID/XPG，非 C 标准），OHOS musl libc 不声明也不导出该符号：

```
object.c:650:2: warning: call to undeclared function 'gcvt' [-Wimplicit-function-declaration]
ld.lld: error: undefined symbol: gcvt
>>> referenced by object.c:(object_toString)
```

## 根因

gcvt() 属于 glibc 兼容层中的遗留函数，musl 项目明确选择不实现非 POSIX 扩展
（与 E534 的 gethostid/strverscmp/sigisemptyset、E093 的 getpass 同根因类）。

## 方案

用 C99 标准函数无条件替换，不引入平台条件编译（符合 R8：补丁默认禁止 `__OHOS__` 宏）：

```c
snprintf(str, 30, "%.17g", d);
```

- `%.17g` 是 IEEE-754 double 往返保真（round-trip）的标准最短可靠格式，任何 libc 通用；
- 若上游原本依赖 gcvt 的 30 位有效数字语义，可改用 `snprintf(str, 30, "%.*g", 17, d)`
  或按需放大缓冲区，但 `%.17g` 已满足双精度无损往返；
- 相比"补实现"（弱符号/平台守卫），替换为可移植标准函数更小、无语义平台差异。

## 验证

- 静态库 `clang -O2 -fPIC -c parse.c object.c`：无警告；
- 上游测试 `test/testStr.c`（解析 citm_catalog.json）：exit=0，status=1727204；
- conan-verify G1/G2/G3/G4 全 PASS；test_package 消费者 round-trip 断言通过；
- W3 本地 CI（build_and_test.sh）：1/1 (100%) 通过。

## 适用边界

- 适用：任何在 OHOS / musl 环境调用 gcvt、ecvt、fcvt 等 glibc 遗留浮点转换函数的 C/C++ 库；
- 反例：目标平台仍为 glibc 且必须保持 gcvt 兼容语义时，应保留 gcvt 走条件编译而非本替换；
- 同类触发但函数不同：gethostid/strverscmp/sigisemptyset（E534，弱符号补实现）、getpass（E093）。

## 查重差异

- 正式知识/图谱、草稿均无 gcvt 条目 → 非 exact/causal 重复；
- 与 E534/E093 共享根因类（musl 缺 GNU 扩展），但函数与本方案（标准函数替换，非补实现）均未被覆盖。