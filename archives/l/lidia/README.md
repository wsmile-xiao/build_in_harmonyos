# LiDIA

## 简介

LiDIA 是一个 C++ 计算数论库，提供多精度整数、有限域、线性代数、格（lattice）、
代数数域、椭圆曲线及类群计算等算法组件。原由 TU Darmstadt 开发（1994–2004），
上游已下线；现由 LattE integrale 项目维护 latte-patches 版本，SageMath 的
optional spkg `lidia` 亦从此取源。

## OHOS 适配

- 上游代码为 C++98 时代产物（1994–2004），`register` 关键字 1142 处、`auto_ptr` 21 处
  → 配方统一以 `-std=gnu++98` 编译，零源码改动规避 C++17 已移除语法
- 归档 `config.sub`（2008-01-16）不识别 `aarch64` 与 `-linux-ohos*`
  → 补丁 `patches/0001-config.sub-ohos.patch` 补 3 处锚点，并以
  `--build/--host=aarch64-unknown-linux-gnu` 绕开 `config.guess` 探测（HarmonyOS 下必然失败）
- 安装目录为小写 `include/lidia`，而公共头内部使用大写 `#include "LiDIA/..."`
  → 配方在包内补齐大写 `include/LiDIA`（大小写敏感 FS 上实体复制，兼容 CI）
- 公共头直接 `#include <gmp.h>`，故 gmp 以 `transitive_headers/transitive_libs` 暴露给下游
- 构建仅支持静态库（上游 `configure.ac` 含 `AC_DISABLE_SHARED`）

## 依赖

- 运行时: `gmp/6.3.0`（多精度整数运算后端，上游硬下限 GMP >= 3.1）
- 构建: 无额外工具依赖（归档自带预生成 `configure` / `Makefile.in` / `ltmain.sh`，无需 autoreconf）

## 功能验证

```bash
# 消费者视角：包含头文件、链接静态库、真实调用数论运算
conan create archives/l/lidia/2.3.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# test_package 输出: consumer checks=10 failures=0 / RESULT: PASSED

# 上游测试资产实跑（EXTRA_DIST，输入 test_roots.1，比对 test_roots.1.cmp）
clang++ -std=gnu++98 -o test_roots_appl test_roots_appl.cc \
  -I<install>/include -I<gmp>/include -L<install>/lib -lLiDIA -L<gmp>/lib -lgmp
./test_roots_appl < test_roots.1
# 8 个多项式求根用例：8/8 通过（顺序无关 + 相对容差 1e-18 口径）
```

## 参考

- 上游（现行）: https://github.com/passagemath/upstream-LiDIA
- 发行归档: https://www.math.ucdavis.edu/~latte/software/packages/lidia/current/
