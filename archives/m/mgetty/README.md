# mgetty

mgetty+sendfax：Unix 下的智能 getty（拨入串口登录管理）与 class-2 传真套件。
包含 `mgetty`（getty 替代）、`sendfax`/`faxspool`/`faxrunq`/`faxrunqd`（传真发送与队列），
以及 G3 传真图像工具 `pbm2g3`/`g32pbm`/`g3cat`/`sff2g3`。项目由 Gert Doering 维护，
GPL-2.0-or-later。

## 功能概述

- `mgetty`：拨入串口智能 getty（自动识别调制解调器、呼叫方 ID、传真/数据切换）
- `sendfax` + `faxspool`/`faxrunq`/`faxrunqd`/`faxq`/`faxrm`：传真发送、队列与状态管理
- `pbm2g3`/`g32pbm`/`g3cat`/`sff2g3`：G3 传真图像编解码与拼接（pbm/sff ↔ g3）
- `newslock`：UUCP 兼容锁文件工具

## OHOS 适配

- 上游是**纯 Makefile 工程**（无 configure）：按 README.1st 复制 `policy.h-dist` →
  `policy.h` 后 `make`；配方用 Conan `AutotoolsToolchain` 提供 CC/CFLAGS/LDFLAGS（R33），
  并以命令行变量覆盖 Makefile 内的硬编码值。
- 平台移植点：
  - 追加 `-DPTR_IS_LONG`——`config.h` 借此在 LP64 目标上把指针大小的整数定为 `long`
    （否则 `conf_mg.c` 的静态初始化不是常量表达式，编译失败）；
  - 补丁 `0001-logfile.c.patch`：`logfile.c` 引用 musl 不存在的 `sys_nerr`/`sys_errlist`，
    改用标准 `strerror()`（无平台宏，glibc 2.32+ 同样适用）；
  - `LIBS=`：上游默认 `-lutil` 为 Linux 专有库，OHOS/musl 无（openpty/logwtmp 在 libc）。
- 打包：13 个可执行文件（`bin/`）＋ 默认配置（`etc/mgetty+sendfax/`）＋
  字模/数据（`lib/mgetty+sendfax/`）。faxspool/faxrunq/faxq/faxrm/faxrunqd 由 `./sedscript`
  从 `*.in` 生成，构建树内不可执行，打包时统一 `chmod 755`。
- 上游有测试：`make test` 跑 `g3/`（G3 图像工具字节级断言）与 `t/`（2 个 C 程序 +
  3 个 shell 脚本）；配方在 `build()` 内实际执行（20/20 通过）。test_package 另做
  消费者验证（25 条）与鸿蒙平台验证（16 条）。

## 依赖关系

- 无第三方编译依赖（仅 libc / POSIX）。
- 运行期可选：`perl`（`faxrunqd` 前端）、`awk`/`sed`（脚本与测试）。

## 参考资料

- 上游主页：<http://mgetty.greenie.net/>
- 源码：<http://mgetty.greenie.net/source/1.2/mgetty-1.2.1.tar.gz>（官方仅 HTTP/FTP）
