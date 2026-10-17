# twopaco 1.0.0

**TwoPaCo — 从多份完整基因组快速构建压缩 de Bruijn 图（1.0.0，TBB 版本）**

## 程序

```bash
twopaco -f 20 -k 11 example.fa -o example.dbg
graphdump -f seq example.dbg -k 11 > example.seq
graphdump -f gfa1 -k 11 example.dbg -s example.fa > example.gfa
twopaco --test   # 上游内部测试（10 组随机对照）
```

## 依赖

- tbb/2023.0.0（TCLAP 已随源码 vendored）

## OHOS 适配

- 补 `<cmath>`（`log2` 未声明，clang 失败）
- TBB 路径由配方从依赖包喂入（`TBB_INCLUDE_DIR`/`TBB_LIB_DIR`）
- 双二进制重签；上游 `--test` 逐行解析（退出码恒 0 不可信）

## 状态

adapting —— 待真机预检。
