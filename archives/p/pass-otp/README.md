# pass-otp

pass-otp 是一个 pass 密码管理器的扩展，用于管理一次性密码（OTP）令牌。

## 基本信息

- **软件名称**: pass-otp
- **项目地址**: https://github.com/tadfisher/pass-otp
- **描述**: pass 扩展，支持 TOTP 和 HOTP 令牌管理
- **类别**: Security / Password Manager Extension
- **许可证**: GPL-3.0

## 功能

- 生成 OTP 代码
- 插入新的 OTP 密钥 URI
- 显示 QR 码
- URI 格式验证

## 运行时依赖

pass-otp 是纯 shell 脚本扩展，无需编译，但需要以下运行时组件：

**必需依赖**：
- `pass` >= 1.7.0（密码管理器）
- `oathtool`（来自 oath-toolkit）

**可选依赖**：
- `qrencode`（用于显示 QR 码）

## 已编译版本

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 1.2.0 | built | 2026-06-02 | 最新稳定版本 |

## 安装方法

安装预编译包后，需要自行安装运行时依赖：

1. 安装 pass 密码管理器
2. 安装 oath-toolkit（提供 oathtool）
3. （可选）安装 qrencode

## 使用示例

```bash
# 插入 OTP 令牌
pass otp insert totp-secret

# 生成 OTP 代码
pass otp code totp-secret

# 显示 QR 码
pass otp uri --qrcode totp-secret
```

---
**维护者**: OpenHarmony PC Developer
