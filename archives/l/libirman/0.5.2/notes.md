# libirman 0.5.2 — HarmonyOS PC 适配说明

## 概况

libirman 是 Irman 红外接收器（及模拟 Irman 协议的硬件，如 irtoy）的用户态支持库：
通过串口完成 `IR` 握手、接收 6 字节 IR 伪码，并按 rc 文件把伪码绑定到名字/命令。

- 上游：https://sourceforge.net/projects/libirman/
- 源码：Debian orig tarball `libirman_0.5.2.orig.tar.gz`（sha256 `3608506e…`）
- 构建：autotools（**tarball 自带 `configure`（autoconf 2.69）与 `Makefile.in`**）
- 依赖：无外部依赖（仅 configure 需要 pkg-config；LIRC 插件默认关闭）

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | **不需要 autoreconf** | 上游 tarball 已带 `configure`/`Makefile.in`/`m4/`，直接 `./configure && make`，因此完全避开 automake 包 perl shebang 指向 CI 镜像路径 `/data/service/hnp/bin/perl` 的坑（对比 archives/l/libhbaapi） |
| 2 | **E011：configure 的 umask 077** | 预生成的 configure 同样含 `umask 077 && mktemp -d`；HMDFS 为 setgid 挂载，config.status 建的 0700 目录不可用 → `config.status: error: could not setup config files machinery`。`build()` 就地放开为 `umask 022`（icoutils 先例） |
| 3 | **E007：config.guess** | 1999 年的 config.guess 既不能在 HMDFS 建临时文件也不认识 HarmonyOS → 显式 `--build/--host=aarch64-unknown-linux-ohos`，configure 不做猜测 |
| 4 | **LIRC 插件** | `PKG_CHECK_MODULES(lirc-driver > 0.9.3)` 缺失时会自动关闭，但仍显式 `--with-plugin=no` 保证确定性 |
| 5 | **没有 IR 硬件** | configure 用 `--enable-swtest`：上游把底层串口 I/O 换成 stdin 软件后端（`irfunc.c` 的 `#ifdef IR_SOFTWARE_TEST`，提示 `please enter 12 hex digits`）→ 在无硬件机器上也能端到端验证「rc 文件 → 哈希表 → 解码」链路 |
| 6 | **安装布局** | `make install`（DESTDIR 暂存）后删除 libtool `.la`；`libirman.pc` 的前缀由 `/` 改写为包目录（Conan 用 `--prefix=/` 安装） |

## 测试

### 上游测试（build() 内执行，真机）

`--enable-swtest` 额外构建 `libirman_sw` 与 `test_name_sw`/`test_func_sw`。配方在
`build()` 中生成一个最小 rc 文件（`bind POWER 010203040506`、`bind PLAY aabbccddeeff`、
`alias ON POWER`），并把 `010203040506` 从 stdin 喂给两个程序：

```
test_name_sw  -> ok / rx `POWER'      （名字绑定 + 别名解析）
test_func_sw  -> ok / rx `010203040506'（6 字节码 -> 文本）
```

两者退出码为 0，输出与期望字符串完全匹配，否则 `build()` 直接失败——是确定性证据，
不依赖任何 IR 硬件。

### 消费者测试（test_package，CMake）

`test_package/test_irman.c` 针对**安装后**的头文件与库做 24 条断言：

- `ir_strerror()` 对 `IR_ENOKEY`/`IR_EBADCMD`/`IR_EDUPKEY` 的映射
- `ir_valid_code()`：12 位十六进制通过；11 位、含非十六进制字符拒绝
- `ir_text_to_code()`/`ir_code_to_text()` 往返一致
- `ir_get_code()`/`ir_finish()` 未初始化时返回 `IR_EDISABLED`
- `ir_init_commands()` 加载 rc（bind/alias/port），且不可重入（`IR_EENABLED`）
- `ir_name_to_text()`/`ir_text_to_name()`/`ir_code_to_name()` 绑定与别名解析
- `ir_default_portname()` 取 rc 的 `port` 行
- `ir_register_command()`（成功/重复 `IR_EDUPKEY`/非法命令号 `IR_EBADCMD`）、`ir_remove_command()`（成功/未知 `IR_ENOKEY`）
- `ir_free_commands()` 后可重新初始化

## 已知限制

- 串口握手（`ir_init()` 打开真实设备、收发 `IR`/`OK`）无法在无接收器的环境中执行；
  上游软件后端覆盖的是其上层逻辑。硬件路径沿用上游原样，未做修改。
- LIRC 插件（`--with-plugin`）未启用：仓库内无 `lirc-driver`。
- 随包安装的交互式工具（`irman.test_*`）与原 `workmanir` 需要真实设备，未在 CI 中运行。
