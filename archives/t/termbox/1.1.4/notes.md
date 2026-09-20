# termbox 1.1.4 适配笔记

## 编译环境

- 构建系统：GNU Make 4.4.1
- 编译日期：2026-09-18
- 编译器：OHOS Clang 15.0.4，目标 `aarch64-unknown-linux-ohos`
- Conan：2.29.1 OHOS 适配版
- 状态：built（本地 Conan、仓库门禁与 HarmonyOS PC 真机测试通过，未发布）

## 上游测试清点

- 上游源码包共 10 个普通文件，包含 `demo/` 下 3 个交互示例。
- 不存在 `test/`、`tests/` 或测试框架配置。
- `make -n check` 返回 `No rule to make target 'check'`。
- 因此上游自动化测试总数为 0；示例程序不计为自动化测试。

## 编译步骤

```bash
make CC=<OHOS clang> AR=<llvm-ar> -j1 libtermbox.a
conan create archives/t/termbox/1.1.4 \
  -pr:h=ohos-aarch64-linux-cross -pr:b=linux-x86_64 --build=termbox/*
```

配方直接复制 `termbox.h` 和库文件，不执行上游 `make install`。这既保持
源码零修改，也避开其共享库安装规则中的 `ln -sf` HMDFS 风险。
共享库配置在打包后使用 HarmonyOS `binary-sign-tool` 自签，再将相同签名
内容复制为 SONAME 和链接名对应的普通文件；静态和共享配置均在真机通过。

## 依赖版本

无第三方依赖，仅依赖 HarmonyOS libc/POSIX 接口。

## 测试补全与验证

上游无自动化测试，本适配新增 2 个消费者测试程序，共 33 个断言：

1. `test_api.c`：16 个断言，覆盖初始化前状态、UTF-8 长度、UTF-8 与
   Unicode 双向转换及公开常量。
2. `test_ohos_pty.c`：17 个断言，要求 `__OHOS__`，在真机创建 PTY，
   验证 `tb_init_fd`、termios、窗口尺寸、输入/输出模式、缓冲区写入、
   `tb_present`、`SIGWINCH` resize 事件和 `tb_shutdown`。

验证命令与完整结果见 `reports/test-report.md`。适配后测试数 2，严格多于
上游实测的 0，且包含 1 个 HarmonyOS 特有测试。

## 源码修改

无源码修改、无补丁。

## 交付物

- `include/termbox.h`
- `lib/libtermbox.a`（默认）
- `lib/libtermbox.so*`（`shared=True` 时，使用普通文件别名而非软链接）
---

**编译结束**: 2026-09-18 09:33
**最终状态**: built
