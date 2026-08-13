# gf2x 1.3.0 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
gf2x 是 GF(2)[x] 上的**快速多项式乘法**库（Karatsuba / Toom-Cook / Cantor FFT）。
是 NTL 与 SageMath / passagemath 计算代数栈的可选加速后端。

## 关键适配
无补丁。configure 直接可用。删除 `lib/*.la`（其中烤死 libdir 绝对路径，
会把下游 libtool 引到 `//lib/` 死路）。

源码地址取自 **SageMath 自己的 `build/pkgs/gf2x/checksums.ini`**，非猜测：
`https://gitlab.inria.fr/gf2x/gf2x/uploads/c46b1047ba841c20d1225ae73ad6e4cd/gf2x-1.3.0.tar.gz`
（sha256 已本地核对一致）。

## 真机验证（2026-08-13，HarmonyOS PC MateBook）
用 **CI 的 profile、且保留环境 LDFLAGS** 跑 `conan create`，
test_package 4 条**真实计算断言**全绿：

```
gf2x: (x+1)^2=x^2+1、(x^2+x+1)(x+1)=x^3+1、x^3·x^4=x^7、p·1=p 全部通过
```

多项式按位表示（bit i = x^i 的系数），结果纯手算可核对——
GF(2) 上系数模 2，交叉项两两抵消：

- `(x+1)²= x²+2x+1 = x²+1` → `0b11 · 0b11 = 0b101`
- `(x²+x+1)(x+1) = x³+x²+x+x²+x+1 = x³+1` → `0b111 · 0b11 = 0b1001`
- `x³·x⁴ = x⁷` → `0b1000 · 0b10000 = 0b10000000`
- `p·1 = p`（乘法单位元）

走的是 `gf2x_mul` 真实导出函数（`gf2x.h:76`），并校验其返回码为 0。
