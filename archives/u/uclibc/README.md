# uclibc (uClibc-ng)

## 简介

uClibc-ng 是一个面向嵌入式 Linux 系统的小型 C 标准库（LGPL-2.1），可作为
glibc/musl 的替代品，专为资源受限环境设计。

## OHOS 适配

### 适配要点
- 构建系统为 Kconfig + GNU make（类似 Linux 内核），非 autotools/CMake
- 上游不提供 `make check` 测试套件，官方测试在独立仓库 uClibc-ng-test
- aarch64 无预置 defconfig，需 `KCONFIG_ALLCONFIG` 片段 + `allnoconfig` 生成 `.config`
- `Rules.mak` 硬编码 `CC=$(CROSS_COMPILE)gcc`，需命令行覆盖为 LLVM 工具链
- 无补丁需求（官方 1.0.54 源码）

### 已知问题
- 作为 libc 本体，与 OHOS musl sysroot 冲突，消费者需以 `-nostdinc`/`-nostdlib` 方式使用
- 本机前置适配未执行真机构建（无 OHOS 交叉工具链），状态为 prepared

## 依赖

### 编译依赖
- 无外部依赖（自包含 C 标准库）；需目标内核头文件（OHOS SDK sysroot）与交叉编译器

### 运行依赖
- 无运行依赖（libc 本体）

## 功能验证

```bash
# 编译产物验证（真机 shadow CI 后）
ls <pkg>/lib/libc.so         # 共享库
ls <pkg>/usr/lib/libc.a      # 静态库
ls <pkg>/usr/lib/crt1.o      # 启动文件
ls <pkg>/usr/include/*.h     # C 标准头文件
```

## 参考

- 官网: https://uclibc-ng.org/
- 源码: https://downloads.uclibc-ng.org/releases/（镜像: toolchains.bootlin.com）
- 文档: https://uclibc-ng.org/docs/
