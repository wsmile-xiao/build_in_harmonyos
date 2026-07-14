# memtester 4.7.1 适配笔记

## 编译环境
- 构建系统: makefile（上游 djb 风格，本配方改为直接编译，见下）
- 编译日期: 2026-07-14
- 编译器: clang（由 Conan conf `tools.build:compiler_executables:c` 注入，R33）
- 状态: published

## 源码

- 官方源: https://pyropus.ca/software/memtester/old-versions/memtester-4.7.1.tar.gz
- sha256: `e427de663f7bd22d1ebee8af12506a852c010bd4fcbca1e0e6b02972d298b5bb`
- 说明: 官方 `pyropus.ca` 的 SSL 证书主机名不匹配，conan `get()`(严格 TLS) 下载会失败；
  `conandata.yml` 以官方 URL 为首，并附 Debian pristine `orig.tar.gz` 作为 fallback，
  两者内容字节一致（与 Debian/Ubuntu/Homebrew 发布的 sha256 完全相同）。

## 上游构建系统分析

memtester 上游为 **djb 风格 Makefile**（与 daemontools 同源）：

- `Makefile` 通过 `$(shell head -n 1 conf-cc)` / `$(shell head -n 1 conf-ld)` 读取编译/链接命令；
- 运行期用 `cat warn-auto.sh make-compile.sh > compile` 等方式生成 `compile`/`load`/`auto-ccld.sh`
  等驱动脚本，这些脚本均带 `#!/bin/sh` shebang；
- `find-systype.sh` 用 `uname` 探测 systype，仅供 `extra-libs.sh` 决定额外链接库；
  在 Linux/OHOS 下 `extra-libs.sh` 不输出任何库。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make` 构建无法进行 | 生成的驱动脚本带 `#!/bin/sh`，OHOS 无 `/bin/sh`(R5) | 不调用 `make`，直接用 clang 编译 `memtester.c`+`tests.c` 并链接，标志位与上游 `conf-cc`/`conf-ld` 完全等价 |
| 2 | conan `get()` 下载官方源失败 | `pyropus.ca` SSL 证书主机名不匹配(严格 TLS 校验失败) | `conandata.yml` 声明 URL 列表：官方源 + Debian pristine 镜像，字节一致，sha256 校验通过 |
| 3 | 无 mlock 权限如何运行 | OHOS 进程默认无 `CAP_IPC_LOCK`，`mlock` 返回 `EPERM` | memtester 内置降级逻辑：`EPERM` 时自动转为 unlocked 测试并正常退出，无需补丁 |

## 编译步骤（配方 build() 实际执行）

```bash
cc -O2 -DPOSIX -D_POSIX_C_SOURCE=200809L -D_FILE_OFFSET_BITS=64 -DTEST_NARROW_WRITES -c memtester.c -o memtester.o
cc -O2 -DPOSIX -D_POSIX_C_SOURCE=200809L -D_FILE_OFFSET_BITS=64 -DTEST_NARROW_WRITES -c tests.c    -o tests.o
cc -s -o memtester memtester.o tests.o
```

其中 `cc` 来自 Conan conf；`-O2 -DPOSIX -D_POSIX_C_SOURCE=200809L -D_FILE_OFFSET_BITS=64 -DTEST_NARROW_WRITES`
逐字取自上游 `conf-cc`，`-s` 取自上游 `conf-ld`。

## 源码修改

无补丁。memtester 4.7.1 源码为纯 POSIX C，与 OpenHarmony(musl/libc) 完全兼容；
Alpine(musl)、Debian、Arch 均在无补丁情况下构建，进一步佐证。

## 依赖版本

无外部依赖，仅 libc。

## 验证结果

- test_package 先探测二进制能否在本平台启动（memtester 启动必先打印版本横幅）；可启动则要求 `memtester 1M 1`（1MiB、1 轮）退出码 0——其非零退出（检测到内存故障）作为真实测试失败上抛，不吞异常（R34）；仅当平台拒绝执行未签名 ELF 时才回退到 ELF 魔数校验；
- L2 烟雾测试 `--version/--help`：memtester 不支持这两个参数（退出码非 0），属预期，L2 为非阻塞告警。

## 注意事项

- memtester 无 `--version`/`--help`，CI L2 会记为非阻塞 warn，不影响构建结论；
- memtester 为命令行工具(application)，已在软件级目录提供 `commands.json`(R38)。
