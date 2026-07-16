# showkey 1.10 适配笔记

## 基本信息

- **软件**: showkey
- **版本**: 1.10
- **上游**: https://gitlab.com/esr/showkey
- **构建系统**: makefile（纯 Makefile，无 configure/autotools/cmake）
- **许可证**: MIT
- **状态**: built

## 软件说明

showkey 读取终端按键，以可打印形式回显其原始转义序列，是排查键盘映射/终端输入的轻量工具。上游为 Eric S. Raymond 维护的单文件 C 程序（showkey.c），仅依赖 POSIX termios 与 libc，无任何外部依赖。

## 编译步骤

1. 源码取自 GitLab 官方 tag 归档 `1.10`（`showkey-1.10.tar.gz`）。
2. 构建：`make CC=<Conan 配置的 clang> -j1`。Makefile 的 `all` 目标编译 `showkey.c` 生成 `showkey` 二进制。
3. 安装：Makefile 的 `install` 目标需 asciidoctor 生成 man 页 `showkey.1`（OHOS 无此工具），故 conanfile.py 的 `package()` 只拷贝 `showkey` 二进制到 `bin/`，不走 `make install`。
4. HarmonyOS 二进制需 ELF 签名：`package()` 中检测到 release worker 签名工具（`/data/service/hnp/bin/binary-sign-tool`）则签名；本地容器无该工具则跳过（musl rootfs 下未签名二进制可直接运行，不影响验证）。

## 遇到的问题与解决方案

无。showkey 仅使用标准 POSIX termios（tcgetattr/tcsetattr/sigaction/isatty/read），OHOS musl libc 完整支持，编译零警告零错误，无需任何补丁。

## 测试

showkey 是交互式 tty 工具，无 `--version`/`--help`，且无库 API（单二进制）。test_package 通过执行已安装的 `showkey` 二进制验证：非 tty stdin 下 showkey 确定性输出 `stdin is not a tty` 并以退出码 1 退出，据此证明二进制真实安装且可运行。

## 验证结果

- 编译：clang 15（`/data/service/hnp/bin/clang`），`make` 编译成功，无警告。
- 产物：`bin/showkey`（aarch64 LSB，动态链接 `/lib/ld-musl-aarch64.so.1`）。
- 运行：`showkey </dev/null` 输出 `stdin is not a tty`，退出码 1（符合预期）。
- 依赖：`readelf -d` 仅见 libc，无额外动态依赖。

## 依赖版本

无外部依赖（仅 libc）。
