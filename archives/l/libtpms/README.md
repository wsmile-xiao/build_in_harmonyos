# libtpms

libtpms 提供可嵌入应用程序的 TPM 1.2 与 TPM 2.0 软件实现。

## 版本

| 版本 | 状态 | 构建系统 | 本地验证 |
|------|------|----------|----------|
| 0.10.2 | built | Autotools | 上游测试 10/10，Conan 消费者测试通过 |

## OHOS 适配

- 使用 Conan 2 配方为 HarmonyOS PC arm64 构建静态库 `libtpms.a`
- 使用 OpenSSL 3.5.6，并配置 OHOS build/host triplet
- 从上游标签源码生成 Autotools 构建快照
- 兼容 HarmonyOS 测试环境中的 GNU `stat -c%s` 行为
- 保留并执行实际配置启用的全部 10 项上游测试
- 消费者测试真实调用 `TPMLIB_GetVersion()` 验证公共 API

## 上游

- 仓库：https://github.com/stefanberger/libtpms
- 版本：0.10.2
- 许可证：BSD-3-Clause
