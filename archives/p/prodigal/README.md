# Prodigal

## 简介
Prodigal (PROkaryotic DynamIc Programming Genefinding ALgorithm) 是一个用于微生物（细菌和古菌）基因预测的快速高精度软件。

## OHOS 适配
- 纯 Makefile 项目，无 configure 脚本
- 需通过 make 变量传递编译参数（CC=clang, LDFLAGS 等）
- 必须使用 GNU ld 替代 lld（-fuse-ld=/data/service/hnp/bin/ld.bfd）
- Makefile 不支持 DESTDIR，需修改 INSTALLDIR 实现 staging 安装
- 版本信息使用 `-v` 而非 `--version`

## 依赖
无外部库依赖，仅需数学库（-lm）。

## 功能验证
```bash
prodigal -v  # 显示版本: Prodigal V2.6.3: February, 2016
```

## 参考
- 官网: https://github.com/hyattpd/Prodigal
- 源码: https://github.com/hyattpd/Prodigal/archive/refs/tags/v2.6.3.tar.gz