# multisort

## 是什么

multisort 把多个 Common Log Format（CLF，httpd 访问日志）文件按请求时间合并成一份日志，输出到 stdout：

```
multisort LOGFILE1 LOGFILE2 [LOGFILEn ...]
```

典型场景：同一站点经轮询 DNS 分布在多台主机上，把各主机的访问日志合并后统一分析。

## 行为（multisort.c）

| 输入 | 行为 |
|------|------|
| 少于两个文件 | usage 打印到 stderr，退出码 1 |
| 两个及以上文件 | 每轮输出各文件缓冲行中时间戳最小的一行（`[dd/Mon/yyyy:hh:mm:ss` 部分；时区被忽略），全部读完后退出码 0 |
| 文件打不开 | `multisort: <文件>: <strerror>`，退出码 1 |
| 空文件 | `multisort: empty input file ...`，退出码 1 |
| 无法解析时间的行 | 时间记为 0，优先输出 |

## OHOS 适配

- 上游 Makefile 写死 `CC = gcc`：配方把 `AutotoolsToolchain` 给出的编译器与标志放在 make 命令行上覆盖（R33）。
- `patches/0001-multisort.c.patch`：
  - 行缓冲由 libc 的 `BUFSIZ` 改为固定 8192 字节——OHOS musl 的 `BUFSIZ` 为 1024（glibc 为 8192），
    `fgets()` 会把 1024 字节以上的日志行切段，续段被当作新行参与排序，输出被截断/串行；
  - gperf 生成的 `in_word_set()` 加 `static`——非 static 的 `__inline` 函数在 C99 inline 语义下
    不产生外部定义，不内联时（`-O0` / Debug）链接报 `undefined symbol: in_word_set`；
  - 排序哨兵 `900000000` 改为 `LONG_MAX`——**上游缺陷修复，非平台相关**：1999 年的哨兵自
    2018 年 12 月起小于所有时间戳，合并不再按时间进行，并会对已关闭的 `FILE` 再次读取。
- 上游无 install 目标，配方 `package()` 直接把二进制复制到 `bin/`。
- 上游无测试套件；test_package 补全 A1-A3 产物检查 + F1-F7 功能检查（共 10 项）。

## 依赖关系

- 编译依赖：无（仅 libc；`months.gperf` 的生成结果已内嵌在 multisort.c 中，构建不需要 gperf）
- 运行依赖：无

## 参考资料

- 上游主页：https://www.xach.com/multisort/
- 源码包：`multisort-1.1.tar.gz`（SHA256 `50cc0e84...5bc17d`）
