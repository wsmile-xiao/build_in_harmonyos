# Sratom

## 简介
Sratom 是一个 Atom 序列化库，用于将 LV2 Atom 数据序列化为 RDF 格式。

## 功能概述
- LV2 Atom 序列化
- RDF 格式转换
- 连接 LV2 和 RDF 生态

## OHOS 适配
- 构建系统: meson 1.11.1
- 纯库项目，无可执行文件
- ELF 签名对共享库必需
- 测试全部通过（3/3）

## 依赖
- lv2 >= 1.18.4 (LV2 规范)
- serd >= 0.30.10 (RDF 序列化)
- sord >= 0.16.16 (SPARQL 库)

## 功能验证
```bash
pkg-config --modversion sratom-0  # 输出: 0.6.22
```

## 参考
- 官网: https://drobilla.net/software/sratom
- 源码: https://gitlab.com/lv2/sratom