# fcrackzip

## 简介
fcrackzip 是 ZIP 文件密码破解工具，支持暴力破解（Brute force）和字典攻击（Dictionary）模式，支持标准 ZIP 和 AES 加密。

## OHOS 适配
- 需要修补 `crack.h`、`getopt.c`、`getopt1.c` 以适配 OHOS 环境
- 使用 autotools 构建系统
- 支持多线程模式

## 排除与替代
无

## 依赖
- 编译工具: clang, make
- 无额外库依赖

## 功能验证
```bash
# 暴力破解
fcrackzip -b -c 1 -l 4-4 protected.zip

# 字典攻击
fcrackzip -D -p passwords.txt protected.zip

fcrackzip --help
```

## 参考
- GitHub: https://github.com/hyc/fcrackzip
