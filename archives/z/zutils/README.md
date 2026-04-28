# Zutils

## 简介
透明处理 gzip、bzip2、lzip、xz 压缩文件的工具集，包含 zcat、zcmp、zdiff、zgrep、ztest、zupdate 等命令。

## OHOS 适配
- 自定义 configure 脚本，兼容 autotools 模式
- 1.15 有 FIFO 创建限制（鸿蒙不支持 mkfifo）
- 运行依赖 gzip, bzip2, lzip, xz

## 依赖
- gzip
- bzip2
- lzip
- xz

## 功能验证
```bash
zcat --version
zgrep --version
```

## 参考
- 官网: https://savannah.gnu.org/projects/zutils/
