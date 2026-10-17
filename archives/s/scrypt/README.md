# scrypt 1.3.2 for HarmonyOS

## 概述

scrypt 是 Colin Percival 编写、Tarsnap 维护的文件加密命令行工具，
使用 scrypt 密钥派生函数（RFC 7914）加解密文件，输出格式自带
HMAC-SHA256 完整性校验。本归档为 HarmonyOS PC (aarch64) 平台的适配记录。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | scrypt |
| 版本 | 1.3.2 |
| 上游仓库 | https://github.com/Tarsnap/scrypt |
| 官方发布 | https://www.tarsnap.com/scrypt/scrypt-1.3.2.tgz |
| 许可证 | BSD-2-Clause |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.12.0 |
| 架构 | aarch64 |
| 编译器 | clang 15 (LLVM) |
| 构建系统 | autotools (configure + make) |
| 依赖 | openssl/3.5.8.1（configure 硬性要求 AES_encrypt 与 openssl/aes.h） |

## 适配要点

1. **E007 config.guess/config.sub 补丁**：上游 2018 版 config.guess 不识别
   HarmonyOS（uname -s 返回 HarmonyOS），configure 报 `cannot guess build type`。
   打补丁后输出三元组 `aarch64-unknown-linux-ohos`（config.sub 增加 ohos-linux
   分支、ohos* OS 列表与 linux-ohos 内核列表）。
2. **openssl 依赖注入**：configure 硬性检查 `AES_encrypt`（`AC_SEARCH_LIBS`）
   与 `openssl/aes.h`，配方通过 `AutotoolsDeps` 将依赖 include/lib 目录注入
   CPPFLAGS/LDFLAGS。
3. **CLI 工具**：安装产物为 `bin/scrypt` 命令行工具，软件级声明
   `commands.json`（R38）。

## 编译步骤

```bash
tar -xzf scrypt-1.3.2.tgz && cd scrypt-1.3.2
# 应用 config.aux/config.guess + config.sub 补丁后：
./configure --prefix=/usr/local && make -j1 && make install
```

## 测试

- 上游测试：`make test` 运行 tests/test_scrypt.sh 的 9 个场景脚本
  （01-09），另有 verify-strings C 程序（4 组已知向量，输出与
  test_scrypt.good 一致）。
- 鸿蒙专项测试：`tests/ohos_roundtrip_test.sh` 在 OHOS 平台实际执行
  `scrypt --version`、文件加解密往返与错误口令必败校验。

## 消费者验证

test_package 直接调用已安装的 `bin/scrypt`：版本核验 + enc/dec 往返 +
错误口令解密失败（HMAC 校验生效）。
