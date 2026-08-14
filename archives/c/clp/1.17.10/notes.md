# clp 1.17.10 适配笔记

## 基本信息
- 软件: clp (COIN-OR Linear Programming)
- 版本: 1.17.10
- 构建系统: autotools
- 依赖: coinutils/2.11.13、coin-or/0.108.12（Conan 依赖）

## 关键问题
### E072: config.guess 不识别 HarmonyOS
构建阶段将 HarmonyOS/HongMeng 映射为 Linux musl 三元组。

### 依赖说明
Clp 编译期需要 CoinUtils（ClpSimplex.hpp include coin/*.hpp）；Osi 是 OsiClp 子项目的依赖。
CoinUtils 和 Osi 通过 Conan 依赖分别提供为 coinutils/2.11.13 和
coin-or/0.108.12；构建时生成 osi.pc 兼容别名供上游 configure 发现。

## 编译命令
./configure --prefix=$DEFAULT_PREFIX CC=clang CXX=clang++ --enable-static --disable-shared
make -j1
make install
