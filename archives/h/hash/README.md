# hash

## 简介
clibs 组织提供的 C 哈希表实现，基于 khash（Attractive Chaos 的
khash.h 模板），提供字符串键 → void* 值的指针哈希表，包含
`hash_set` / `hash_get` / `hash_has` / `hash_del` / `hash_clear` /
`hash_size` 以及 `hash_each` / `hash_each_key` / `hash_each_val`
迭代宏。纯 C99，无外部依赖。

## OHOS 适配
- 上游 Makefile 仅含 `test` 目标（`-DTEST_HASH` 编译自测），无库构建/安装
  目标；配方直接以 clang 编译 `hash.c` 生成静态库并打包头文件
- 无平台相关代码，clang 15 直接编译通过（-std=c99 -fPIC -O2）
- 头文件：`hash.h`（含 khash.h）

## 依赖
- 无第三方依赖

## 参考
- 源码: https://github.com/clibs/hash