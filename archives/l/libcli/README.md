# libcli

## 简介

libcli 是一个 C 语言共享库，用于为其他软件提供 Cisco 风格的命令行交互界面
（telnet CLI）：支持命令行编辑、历史记录、用户名/口令认证，以及基于回调的
用户可定义命令树（含管道、过滤器、optarg 参数与 buildmode 模式）。

## OHOS 适配（1.10.7）

- 上游为原生 Makefile 工程（无 configure），配方直接调用
  `make CC=<clang> AR=<llvm-ar> TESTS=0 LIBS= -j1`。
- `TESTS=0` 跳过 `clitest` 交互式 telnet 演示服务（监听端口 + `fork()`），与
  OpenWrt 打包行为一致；库本身无 fork 强依赖。
- Makefile 在非 Darwin 平台硬编码 `LIBS=-lcrypt`；OHOS 使用 musl libc（自带
  简化 `crypt()` 实现，设备上无独立 libcrypt），配方以 `LIBS=` 空值覆盖。
- 产物经 `-lcli` 链接（`cpp_info.libs=["cli"]`），头文件为 `libcli.h`。
- 上游无测试套件（Makefile 无 check/test 目标，上游 CI 仅 `make`），test_package
  提供 10 个 CHECK 的消费者冒烟测试（`test_libcli.c`，无 socket 实跑）。

## 依赖

无运行时依赖。

## 功能验证

```bash
# 消费者冒烟测试（test_package 自动执行）
./test_libcli   # 10/10 PASS（TAP 输出，失败即非零退出）
```

## 参考

- 官网: https://github.com/dparrish/libcli
- 源码: https://github.com/dparrish/libcli/archive/refs/tags/V1.10.7.tar.gz
