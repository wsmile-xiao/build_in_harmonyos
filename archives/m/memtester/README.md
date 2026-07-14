# memtester

> 用户态内存子系统压力测试工具

## 简介

memtester 是一个用户态内存测试工具，通过多种写入/读取模式对内存子系统进行压力测试，
用于定位间歇性、非确定性的内存故障。原始作者 Simon Kirby，自版本 2 起由
Charles Cazabon 维护，官方站点为 https://pyropus.ca/software/memtester/ 。

## OHOS 适配要点

- **构建系统**：上游使用 djb 风格 Makefile（`conf-cc`/`conf-ld` 配置编译/链接命令，
  运行期生成带 `#!/bin/sh` 的脚本驱动编译）。OHOS 没有 `/bin/sh`(R5)，这些脚本无法执行，
  因此配方改为用与 `conf-cc`/`conf-ld` 完全等价的 CFLAGS 直接编译 `memtester.c` 与
  `tests.c` 并链接，产物行为与上游 `make` 构建一致。
- **依赖**：仅依赖 libc（`mmap`/`mlock`/`malloc`），无任何外部依赖。
- **mlock 行为**：OHOS 上进程默认无 `CAP_IPC_LOCK`，`mlock` 返回 `EPERM`，memtester 会
  自动降级为 unlocked 测试并正常退出，不影响功能与测试结论。
- **源码可下载性**：官方 `pyropus.ca` 的 SSL 证书存在主机名不匹配，conan `get()` 严格校验
  会失败；`conandata.yml` 以官方 URL 为首，并附 Debian pristine `orig.tar.gz` 镜像作为
  fallback，两者字节一致（sha256 相同）。

## 依赖

无外部依赖。

## 功能验证

```bash
memtester 1M 1     # 对 1MiB 内存跑一轮全部测试，健康内存退出码 0
```

## 参考

- [memtester 官方站点](https://pyropus.ca/software/memtester/)
