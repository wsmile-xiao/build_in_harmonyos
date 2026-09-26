# E600 — 上游 Makefile flags 硬编码 x86 专属编译选项在 aarch64/OHOS 被 clang 拒绝

## 错误特征

上游 `flags`/`CFLAGS` 文件写死 x86 专属编译选项时，aarch64 clang 直接失败：

```
clang++ ... -msse2 -mfpmath=sse ... -mfma -mno-fma4 ...
error: unknown FP unit 'sse'
make: *** [Makefile:10: test.o] Error 1
```

`-msse2`、`-mfma`、`-mno-fma4` 仅为 unused-argument 警告，但 `-mfpmath=sse` 是硬错误。

## 触发条件

- 构建系统: 裸 Makefile（`flags` 文件 + 子目录 `make -C`），无 configure/cmake
- 阶段: make（compilation）
- 环境: aarch64（OHOS armv8 等）clang 交叉编译；x86 本机编译不报错

## 根因分析

上游 Makefile 项目为 x86 开发机优化而把 `-msse2 -mfpmath=sse -mfma -mno-fma4` 写死在 flags 文件。aarch64 后端没有 SSE 浮点单元概念，clang 对 `-mfpmath=sse` 报 `unknown FP unit`。此类项目无 configure 阶段，无法通过标准选项流程剔除。

## 解决方案

### 推荐方案

patch flags 文件，移除 x86 专属项、保留可移植项：

```
-CXXFLAGS+=-std=gnu++11 -Wall -W -frounding-math -fsignaling-nans -ffp-contract=off -msse2 -mfpmath=sse -pedantic -mfma -mno-fma4
+CXXFLAGS+=-std=gnu++11 -Wall -W -frounding-math -fsignaling-nans -ffp-contract=off -pedantic
```

并在 conan 配方 build() 中以 Conan conf 取编译器（R33），`-j1` 串行调用（避免顶层隐式规则与子目录并行竞争）。symfpu 0.0-git.40bdec00 实测通过，`conan-verify` G2-G5 全绿。

### 禁止做法

- ❌ 不 patch、只靠环境 CXXFLAGS 覆盖（Makefile `+=` 仍会追加上游 x86 选项）
- ❌ 把 `-mfpmath=sse` 改写为 `-mfpmath=neon` 等臆测替换（语义不同，且非本库目标）

## 验证

```bash
make -C symfpu CXX=clang++ AR=llvm-ar RANLIB=llvm-ranlib -j1   # 构建通过
conan create archives/s/symfpu/0.0-git.40bdec00 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```