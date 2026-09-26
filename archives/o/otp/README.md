# otp

> John Walker 的**一次性密码本 / 密码列表生成器**（fourmilab）：生成随机字母、
> 数字或按英语二元组频率生成的“易记”口令，并可输出每个口令的 MD5 签名文件。

## 简介

`otp` 生成用于校验和安全用途的口令列表：口令长度任意，可由大写/小写字母、
数字组成；字母口令既可是完全随机的（最安全），也可遵循英语文本的二元组统计
（便于抄录、但安全性略低）。对计算机应用，`otp` 还能写出每个口令的 MD5 签名
文件，使应用无需保存明文口令即可校验用户输入。

## OHOS 适配要点

- 纯 C 三个源文件（`otp.c`、`md5.c`、`random.c`），无三方依赖。
- 上游 `Makefile` 硬编码 `CC = gcc`：配方在 make 命令行覆盖为 OHOS 工具链的 clang。
- 上游自带确定性回归套件：固定 `-r` 种子后输出可完全复现，`build()` 中执行
  `sh test.sh` 并与金标准 `test.mas` 逐字节 `diff`。
- 产物是 CLI 工具，安装 `bin/otp` + `share/man/man1/otp.1`，并提供软件级
  `commands.json`。

## 依赖

无。

## 使用

```sh
# 生成 4 组 8 位小写字母口令（固定种子，可复现）
otp -rTEST -n4

# 生成 7 组 4 位数字口令，并写出 MD5 签名文件
otp -rTEST -n7 -d4 -m sig.md5

# 查看用法
otp -U
```

## 参考

- [上游 fourmilab OTP](https://www.fourmilab.ch/onetime/otpgen.html)
