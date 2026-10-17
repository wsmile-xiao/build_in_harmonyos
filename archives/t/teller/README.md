# teller

面向开发者的多云密钥管理器（multi-provider secret manager），用 Rust 编写。

- 上游仓库：<https://github.com/tellerops/teller>
- 许可证：Apache-2.0
- 语言 / 构建系统：Rust / cargo（Cargo workspace）

## 已适配版本

| 版本 | 状态 | 构建方式 | 备注 |
|---|---|---|---|
| 2.0.7 | built | cargo workspace → `bin/teller`（aarch64-unknown-linux-ohos，OHOS 自签名） | 工具链 `rust-toolchain/1.97.1`（tool_requires）；依赖 `openssl/3.5.8.1`（静态链接）；`protobuf/3.17.3` 提供 protoc |

## 支持的 provider（上游默认特性）

`hashicorp_vault`、`dotenv`、`ssm`、`aws_secretsmanager`、`google_secretmanager`、`hashicorp_consul`、`etcd`（默认全部启用）。

## 使用

```bash
teller --version
teller --help
# 需要配置文件（.teller.yml 或 -c/--config 指定）
teller export json
teller scan
```

详见各版本目录下的 `notes.md`（适配笔记）与 `reports/`（构建/测试报告）。
