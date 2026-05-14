# mecab — 日语分词引擎

## 软件简介
MeCab 是一款开源的日语文本分词引擎，基于条件概率场（CRF）模型。它可生成高质量的日语形态分析结果，广泛应用于自然语言处理、文本分析等领域。

## 可用版本

| 版本 | 状态 | 补丁数 | 发布日期 |
|------|------|--------|----------|
| 0.996 | partial | 3 | 2026-04-29 |

## 快速安装

```bash
# 下载预编译包
cd ~/usr/local
tar xzf mecab-0.996-ohos-aarch64.tar.gz

# 运行安装脚本
sh install-mecab-0.996.sh

# 验证
mecab --version
# 输出: mecab of 0.996
```

## 注意事项
- 需安装日语字典包（如 mecab-ipadic）才能使用分词功能
- 本包专为 HarmonyOS aarch64 平台编译

## 相关资源
- 官网: https://taku910.github.io/mecab/
- 源码: https://deb.debian.org/debian/pool/main/m/mecab/
- 字典: mecab-ipadic, mecab-jumandic

---
*OpenHarmony 预编译包维护*