# DRAFT: precomp CLI 脚本化陷阱：-o 无空格 + -r 交互式覆盖询问

- **严重度**: 2
- **类别**: test, cli, compression
- **软件**: precomp 0.4.7（schnaader/precomp-cpp）
- **阶段**: test_package
- **状态**: UNMATCHED 草稿，待人工/AI 审核晋升

## 错误特征
```
error 10                       # "-o 文件名" 写成了带空格的形式
Overwrite? (y/n)               # -r 还原遇到同名输出文件时交互询问
```

## 根因分析
1. `-o` 与输出文件名之间**不能有空格**（上游参数解析硬约定），写
   `-o out.pcf` 会被当作两个独立参数，报 error 10。
2. `precomp -r file.pcf` 还原时，默认输出名取自 **PCF 头内记录的原始
   文件名**（不是输入 .pcf 的名字）。若该名字的文件已存在于 CWD（比如
   原文件就在旁边——round-trip 测试的常见布局），会触发交互式
   Overwrite 询问；非 tty 环境（subprocess/CI）下行为不可靠。

## 推荐方案
test_package / 自动化脚本统一使用：

```bash
precomp -o<输出.pcf> <输入>            # -o 紧贴文件名
precomp -r -o<还原输出> <输入.pcf>     # 还原也显式 -o
```

退出码语义：0=成功、1=各类错误、2=无流可解（批量场景可用来区分）。

## 验证
precomp 0.4.7 OHOS aarch64 实测：`-r -oX` 组合 rc=0 且 sha256 与原文件
一致；带空格 `-o X` 报 error 10。

## 关键词
precomp, -o, -r, error 10, Overwrite, round-trip, script, headless
