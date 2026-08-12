# givaro 4.2.1 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
C++ 计算代数库，提供有限域 / 环 / 多项式等代数结构，产出 `libgivaro.so`。
是 fflas-ffpack、linbox、SageMath / passagemath 计算代数栈的核心依赖。

## 关键适配

### 必须用开了 `--enable-cxx` 的 GMP
首轮直接 `configure: error: ERROR: GMP not found/usable!` —— givaro 探测的是 GMP 的
**C++ 接口**（`gmpxx.h` / `libgmpxx`），而仓里原有的 `gmp/6.3.0` 是纯静态、未开
`--enable-cxx` 的包，根本不产这两样。故本包依赖 `gmp/6.3.0.1`（同一份上游 tarball
＋ `--enable-cxx`），见该版本的 notes。

其余：删除 `lib/*.la`（其中烤死 libdir 绝对路径，会把下游 libtool 引到 `//lib/` 死路）。

## 消费方必看：`Modular` 的特化按头文件分散提供

givaro 的 `Modular<T>` **不是对所有 T 都有定义**，特化分散在各个头文件里：

```cpp
#include <givaro/modular.h>          // 总入口，含 modular-floating 的 Modular<double> 特化
Givaro::Modular<double> F(7);        // ✓
```

写成 `Modular<int64_t>` 而只 include 总入口会撞：

```
error: implicit instantiation of undefined template 'Givaro::Modular<long>'
```

首轮 test_package 就是这么挂的——**编译期就报**，比运行期崩要友好，但错误信息
指向"未定义模板"而非"你该换个头文件"，容易误判成库没装好。

## 真机验证（2026-08-12，HarmonyOS PC MateBook）
`conan create -pr ohos-native` 通过，test_package 4 条**真实计算断言**全绿：

```
givaro: GF(7) 加/乘/逆 通过；GMP 大整数乘法 通过
```

- GF(7)：`5+4 ≡ 2`、`5×4 ≡ 6`、`inv(5) = 3`（均可手算核对）
- `Givaro::Integer` 30 位大整数乘法比对（顺带证明 gmpxx 真的链上了）
