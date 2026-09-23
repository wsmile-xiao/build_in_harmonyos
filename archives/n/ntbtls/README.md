# ntbtls

## 简介
Not Too Bad TLS library（ntbtls）是 GnuPG 项目自带的 TLS 底层库（TLS 1.2 客户端实现），
以 libgcrypt 为密码学后端、libksba 解析 X.509 证书、libgpg-error 提供错误码与 estream I/O 抽象。

## OHOS 适配
- 构建系统: autotools（交叉编译 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`）
- 依赖全部走 Conan 显式路径（`AutotoolsDeps` 注入 `-I/-L`，`GPGRT_CONFIG` 指向 libgpg-error 的 gpgrt-config），不写共享 `/usr/local`
- 补丁: `0001-build-aux-config.guess.patch`、`0002-build-aux-config.sub.patch`（config.guess/config.sub 增加 HarmonyOS 三元组识别）
- 详见各版本 notes.md 获取适配详情

## 依赖
- libgpg-error/1.55
- libgcrypt/1.12.2
- libksba/1.6.7.1
- zlib/1.3.2（上游标称可选，实为硬依赖：`src/context.h` 无条件 `#include <zlib.h>`）

## 功能验证
- 消费者冒烟测试（`test_package/test.c`）：版本查询与版本比较语义、客户端上下文生命周期、
  无效构造标志拒绝、hostname/SNI 往返、空 transport 拒绝、无对端握手失败路径（返回错误码不崩溃）、
  release 安全性 —— 11/11 通过
- 上游 0.3.2 无测试套件（tarball 无 `tests/`、无 `TESTS`/`check_PROGRAMS` 目标），详见
  `0.3.2/test_package/MANIFEST.yml` 与 `0.3.2/notes.md`

## 参考
- https://gnupg.org/software/ntbtls/
