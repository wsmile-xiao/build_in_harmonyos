# ent

## 简介
ent 是一个伪随机数序列测试程序，用于评估随机数生成器的质量。

## 功能概述
- 熵值计算
- χ²（卡方）统计检验
- 算术平均值计算
- Monte Carlo π 值计算
- 串行相关系数计算
- 支持多种字符编码（ASCII, EBCDIC, ISO 8859-1）

## OHOS 适配
- 使用 clang 替代 gcc 编译器
- 使用 bfd 链接器替代 lld（lld 在鸿蒙环境下缺少 libxml2 依赖）
- 无需额外依赖库，仅需标准数学库

## 排除与替代
无

## 依赖
- 无外部依赖
- 构建工具：clang, make

## 功能验证
```bash
ent --version  # 验证程序可用性
ent <文件名>    # 对文件进行随机性测试
```

## 参考
- 官网：https://www.fourmilab.ch/random/
- 源码：https://github.com/psm14/ent