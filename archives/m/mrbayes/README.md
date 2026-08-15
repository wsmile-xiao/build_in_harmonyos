# mrbayes - Bayesian Inference of Phylogeny

## 描述
MrBayes 是用于贝叶斯系统发育推断的科学计算程序，基于马尔可夫链蒙特卡洛（MCMC）方法对进化树、替换模型参数与分化时间进行后验分布采样。被广泛应用于系统发育学、分子进化与生物信息学研究。

## 版本信息
- 当前版本: 3.2.7a
- 发布日期: 2019-10
- 主页: https://nbisweden.github.io/MrBayes/
- 上游仓库: https://github.com/NBISweden/MrBayes

## 编译方法
```bash
# 标准 autotools 编译（上游方式）
./configure
make
make install

# 鸿蒙适配编译（无 readline/beagle/MPI，见 conanfile.py）
./configure --prefix=/usr/local \
    --with-mpi=no --with-readline=no --with-beagle=no \
    --enable-sse=no --enable-avx=no --enable-fma=no
make -j1
make install
```

## 依赖
- 编译依赖: C 编译器（clang）、make、sh
- 运行依赖: libc (musl)、libm
- 可选依赖（已禁用）: readline（交互式补全）、beagle-lib（GPU 加速）、MPI

## 功能
- NEXUS 数据格式解析（DNA/RNA/蛋白质/形态/限制性位点数据）
- 多种替换模型与分区分析（JC69/K80/HKY/GTR 等）
- MCMC 采样（Metropolis 耦合 MCMCMC、加热链）
- 模型选择（贝叶斯因子、可逆跳 MCMC）
- 分子钟与化石标定分化时间估计
- 树汇总（多数一致树、可信度区间）

## 安装验证
```bash
mb --version
# 或批量模式运行：
mb < dataset.nex
```

## 许可证
GPL-2.0-or-later（源码头声明 "version 2 of the License, or any later version"；发布包 COPYING 为 GPLv3 文本）
