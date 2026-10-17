# radcli

## 简介
radcli 是轻量 RADIUS 客户端库（freeradius-client / radiusclient-ng 兼容），用于编写 RADIUS 认证/计费客户端，50 行 C 代码即可完成。

## OHOS 适配
- Autotools 构建，`--without-tls --without-nettle` 零外部依赖（内置 MD5/HMAC）
- 上游 `make check` 的 11 个 shell 集成测试需本地 RADIUS 服务器，无服务器时按 SKIP 处理
- test_package 离线覆盖字典加载与 AVPair 编解码核心 API

## 依赖
- 无

## 功能验证
```bash
pkg-config --modversion radcli  # 期望输出: 1.2.11
```

## 参考
- 官网: https://radcli.github.io/radcli/
- 源码: https://github.com/radcli/radcli
