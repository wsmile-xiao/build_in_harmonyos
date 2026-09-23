# pipemeter

管道进度计（pipemeter），由 Clint Byrum 编写，读取 stdin 并写 stdout，同时在
stderr 上报告吞吐速率、已传输字节数、块大小与预计完成时间。典型用法：

```sh
tar cf - mydir | pipemeter | nc other-host 9999
dd if=disk.img of=/dev/sdX bs=4M 2>&1 | pipemeter
```

上游版本 1.1.5（2021-01-09，Launchpad），License: GPL-2.0-or-later。

## 特性
- 单文件 C 实现（`pipemeter.c`，904 行），零第三方依赖
- 自适应块大小（`-b` 初值、`-m` 上限，`-a` 关闭自适应）
- 已知总量时显示进度条与百分比（`-s SIZE`），支持 `k/M/G` 后缀
- 可多路输入：`-f FILE` 可重复、`-F LISTFILE` 读文件清单
- 日志模式 `-l`、纯数字报告模式 `-r`、自定义刷新间隔 `-i`

## OHOS 适配要点
1. **构建**：`autoconf` 生成的 `configure`（无 automake、无 `config.guess`/`config.sub`、
   无 `AC_CANONICAL_HOST`）+ 手写 `Makefile.in`。上游只需 libc/libm，OHOS musl sysroot
   即可满足，无 Conan 依赖。`Makefile.in` 不支持 VPATH，配方强制 in-tree 构建。
2. **补丁 `patches/0002-configure.patch`**（知识 E114）：HMDFS 忽略 `umask`/`chmod`，
   `(umask 077 && mktemp -d ./confXXXXXX)` 产出的 `drwx--S---` 目录连属主都写不进去，
   `config.status` 会崩在 `could not setup config files machinery`；改为普通 `mkdir -p`。
3. **补丁 `patches/0001-Makefile.in.patch`**：OHOS 无可用 `install`（`/bin` 不在 PATH，
   toybox install 不支持 GNU `-D`/`-t`），安装规则改用源码包自带的 autoconf `install-sh`。
4. 两个补丁均不含 `__OHOS__` 平台宏。

## 测试
上游唯一测试入口是 `testscript.sh`（0 断言的 200M 性能采样脚本，需人工回寄结果）；
它依赖 GNU `time` 的 `-a`/`-o`，OHOS toybox `time` 只支持 `-p`/`-v`，原样执行会静默丢采样。
已在 OHOS aarch64 真机上按语义等价方式逐步实跑，11 步全通过、pipemeter 计量精确为 200.00M。
适配层 `test_package/` 为标准结构（`conanfile.py` + `CMakeLists.txt` + `pump.c` 测试源码
+ `smoke.sh`），其中 `pump.c` 编译成管道数据生产者、`smoke.sh` 提供 8 条针对包内二进制
的真实断言（版本、字节计量、
数据面透传、多文件累加、块大小、两类错误退出码）。详见 `1.1.5/notes.md` 与
`1.1.5/reports/test-report.md`。

## 参考
- 上游：https://launchpad.net/pipemeter （发布页 https://launchpad.net/pipemeter/trunk/1.1.5）
- 手册页：`man/man1/pipemeter.1`（随包安装）
