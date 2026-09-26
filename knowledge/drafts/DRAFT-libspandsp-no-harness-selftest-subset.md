# E6406：无测试 harness 的自编译自跑验证+E074 并行 install 竞态

## 错误特征

```
automake: TESTS not defined          # 无官方测试口径
make install: Directory not empty   # HMDFS 并行竞态
HMDFS jobserver fifo EPERM          # E074
```

## 解法

1. **纯算法子集法**（0.0.6 先例系统化）：挑无硬件依赖的编解码核心，配方内编消费者探针真跑往返断言
2. make -j1 + install -j1 串行化
3. N=0 如实+子集探针作消费者验证申报

## 实证

PR #12309 libspandsp 3.1.1 CI passed。
