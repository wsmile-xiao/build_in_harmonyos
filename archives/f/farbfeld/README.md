# farbfeld

## 简介
farbfeld 是一个简单的无损图像格式，使用 16 位 RGBA 像素数据。提供 `ff2pam`、`ff2ppm`、`2ff` 等转换工具。

## OHOS 适配
- 需要修补 `config.mk` 设置 OHOS 交叉编译工具链（CC、PREFIX 等）
- 构建系统为简单 Makefile，无需 configure
- 静态编译无特殊问题

## 依赖
- 无外部依赖（纯 C 实现）

## 功能验证
```bash
ff2pam --help
ff2ppm --help
```

## 参考
- 官网: https://tools.suckless.org/farbfeld/
