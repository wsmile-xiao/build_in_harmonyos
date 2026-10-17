# draft-rdma-core-61.0-rindex-strrchr

## 症状

链接阶段（clang/ld.lld）报：

```
ld.lld: error: undefined symbol: rindex
>>> referenced by srp_daemon.c
>>>               CMakeFiles/srp_daemon.dir/srp_daemon.c.obj:(set_conf_dev_and_port)
>>> did you mean: index
```

## 根因

`rindex()` 与 `index()` 是 BSD 废弃字符串函数，glibc 兼容导出；OHOS musl libc
**不导出 rindex**（`nm -D libc.so | grep rindex` 为空，仅 `index`/`strrchr` 可用）。
源码在 srp_daemon/srp_daemon.c:745 用 `rindex(umad_dev, '/')` 取最后一个 `/`，
链接时符号缺失。

> 勘误提示：`knowledge/musl-glibc-full-comparison-iso-posix.md` 将 rindex 列为
> "已废弃但可用"，与 OHOS 实测矛盾（该表以 glibc 视角编制，OHOS musl 不适用）。

## 最小修复方案

源码替换为 POSIX 等价函数（语义完全相同：返回最后一次出现 c 的指针，无 c 时 NULL）：

```c
umad_dev_name = strrchr(umad_dev, '/');   /* 原: rindex(umad_dev, '/') */
```

不引入兼容实现、不加平台宏，补丁最小化，可向上游提交（P005）。

## 验证

- rdma-core/61.0 srp_daemon：替换后 `make` 全目标构建通过（60 个 bin 产物，100%）；
- conan-verify G2 通过；patch 0006 干净可反向应用；
- 语义等价由 test_ohos_specific [3] 断言（strrchr 返回最后 '/' 位置）。

## 适用范围 / 边界

- 适用：任何使用 rindex/index 等 BSD 废弃字符串函数的 C 项目适配 OHOS；
- 边界：若源码依赖 rindex 作为弱符号占位或 ABI 符号，需改用 E534 类 weak 兼容实现；
- 与 E534 关系：E534 覆盖"musl 缺 GNU/BSD 扩展函数"类别但方案为 weak 符号；
  本条提供最小源码替换方案，二者方案轴不同，可互补。
