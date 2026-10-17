# trousers

TCG Software Stack（TSS）1.2 的开源实现（上游 https://trousers.sourceforge.net/ ，版本 `0.3.15`）。
提供 `libtspi`（TSPI 客户端库）、`libtddl`（TCSD 设备驱动层）与 `tcsd` 守护进程。

## 功能概述

- TSS 1.2 TSPI API：上下文/对象管理、策略与口令、密钥与数据加解密、PCR、NV 存储、DAA 等
- `tcsd` 守护进程：面向 TPM 1.2 设备的本地服务，tspi 通过 TCS 层与其通信
- 内置自检入口（`tspi_selftest` 等）需要真实 TPM 才能运行

## OHOS 适配

- `autoreconf -fi` 生成构建脚本（release tarball 无 `configure`）；用工作机自带 autoconf，
  避免 registry perl 与系统 perl 的 XS 模块冲突
- 生成的 `configure` 在 HMDFS 下需要两处运行时修补：`pwd` 失败回退 `$PWD`、config.status 临时目录
  `umask 022`
- 两个 POSIX 化补丁：`rindex()`→`strrchr()`、`getutid()`→`getutent()` 扫描、`getpwent_r()`→`getpwent()`
  （musl/HarmonyOS 不导出这三个非 POSIX 入口，其中 `getpwent_r` 会导致消费者链接失败）
- 上游无测试套件，配方在 `build()` 内审计留证并补充消费者用例（6/6 通过）

## 依赖关系

- 编译依赖：`openssl/3.5.6.1`；构建期 `automake`、`libtool`、`pkg-config`
- 运行依赖：`openssl`（libcrypto）；`tcsd` 另需真实 TPM 设备与 `/etc/tcsd.conf`

## 参考资料

- 上游：https://trousers.sourceforge.net/
- TSS 规范：TCG TSS 1.2（LTC-TSS_LLD_08）
