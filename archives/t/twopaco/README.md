# twopaco

**TwoPaCo — 从多份完整基因组快速构建压缩 de Bruijn 图**

实现论文 "TwoPaCo: An efficient algorithm to build the compacted de Bruijn
graph from many complete genomes" (Bioinformatics, 2016) 的算法。

## 程序

| 程序 | 说明 |
|------|------|
| `twopaco` | 从多份 FASTA 直接构建压缩图（二进制输出） |
| `graphdump` | 把二进制输出转成文本（seq / group / dot / gfa1 / gfa2 / fasta） |

## 用法

```bash
twopaco -f 20 -k 11 example.fa -o example.dbg
graphdump -f seq example.dbg -k 11 > example.seq
graphdump -f gfa1 -k 11 example.dbg -s example.fa > example.gfa
twopaco --test   # 上游内部测试（10 组随机对照）
```

## 构建

- 构建系统：CMake（`src/CMakeLists.txt`，C++14）
- 依赖：Intel TBB（1.0.0 版本需要；1.1.0 起已去 TBB）
- 许可证：Custom OSS（见 LICENSE.txt）
- 源码：https://github.com/medvedevgroup/TwoPaCo

## 已适配版本

- 1.0.0 (adapting)
