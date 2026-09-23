# plfit

plfit 是 Tamas Nepusz 用 C 语言实现的幂律分布拟合库，依据 Clauset、Shalizi
与 Newman 的方法（SIAM Review 51, 661-703, 2009）对经验数据（离散或连续）
做最大似然幂律拟合：估计幂指数 alpha 与下界 xmin、计算 KS 统计量与 p 值。
随库提供两个命令行工具：

- `plfit`：对输入数据文件做幂律拟合（支持 `-b` 简洁输出、`-M` 矩统计等）
- `plgen`：按给定指数生成幂律分布样本（可加指数截断、可选连续/离散）

## OHOS 适配

- **构建系统**: CMake（原生构建，build = target = OHOS/aarch64，clang 15/16，C99）
- **依赖链**: 无第三方依赖（数学函数由 OHOS libc 提供）
- **补丁**:
  - `0001-CMakeLists.txt.patch`：OHOS sysroot 无独立 libm.so，空置 CMake
    的 `MATH_LIBRARY-NOTFOUND`，避免污染所有链接行（zxcvbn-c 2.6 同款先例）
  - `0002-src-CMakeLists.txt.patch`：静态构建时安装 `libplfit.a`
    （上游只声明了动态库 artifact kind）
- **测试**: 上游 CTest 9 项全部在 `conan create` 内执行并通过；test_package
  含 C 消费者 API 测试与 CLI 冒烟测试

## 依赖

无

## 功能验证

```bash
pkg-config --modversion libplfit   # 期望输出: 0.9.6
plfit -v                           # 期望输出: plfit 0.9.6
plgen -s 42 2000 2.5 | plfit -b    # 生成 alpha=2.5 样本并拟合，输出 D 行
```

## 参考

- 上游仓库: https://github.com/ntamas/plfit
- 源码 tag: https://github.com/ntamas/plfit/releases/tag/0.9.6（tag 归档即发布形态）
