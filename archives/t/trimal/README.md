# trimAl

trimAl 是一套用于系统发育分析的多序列比对（MSA）自动化修剪工具，提供三个命令行程序：

- `trimal`：核心修剪工具（自动策略 gappyout/strict/strictplus/automated1、手动阈值、格式转换）
- `readal`：比对文件读取、信息与格式转换
- `statal`：比对统计（列缺口分布、相似性、一致性等）

## HarmonyOS 适配

配方直接使用上游 Makefile 构建（make 变量覆盖编译器，零源码补丁），产出
aarch64-linux-ohos 可执行文件；构建阶段集成上游 dataset 回归套件（504 用例：
84 个数据集比对 × 6 种修剪模式，逐一与上游参考输出 diff），另有 10 项
消费者断言在 test_package 中执行。无第三方依赖。

## 使用示例

```bash
trimal -in input.fasta -out trimmed.fasta -automated1
readal -in input.fasta -info
statal -in input.fasta -sgc
```

## 参考资料

- [trimAl GitHub 仓库](https://github.com/inab/trimal)
- [trimAl 文档](https://trimal.readthedocs.io)
