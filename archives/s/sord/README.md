# Sord

## 简介
Sord 是一个 SPARQL 库，用于存储和查询 RDF 数据，是 LV2 生态的重要组成部分。

## 功能概述
- RDF 数据存储
- SPARQL 查询支持
- 提供 sordi 命令行工具
- C++ API (sordmm.hpp)

## OHOS 适配
- 构建系统: meson 1.11.1
- 依赖 serd-0 和 zix-0
- ELF 签名必需
- 测试全部通过（3/3）

## 依赖
- serd >= 0.30.10 (RDF 序列化库)
- zix >= 0.6.0 (基础工具库)

## 功能验证
```bash
export LD_LIBRARY_PATH=$HOME/usr/local/lib
sordi -v  # 输出: sordi 0.16.22
```

## 参考
- 官网: https://drobilla.net/software/sord
- 源码: https://gitlab.com/drobilla/sord