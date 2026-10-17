# augustus

## 简介

Augustus 是真核生物基因结构预测软件，使用隐马尔可夫模型预测基因组中蛋白质编码基因的位置和结构。C/C++ 编写，Makefile 构建，产物为多个命令行工具（`bin/augustus` 等）及 140MB 物种模型数据 `config/`。

- 上游仓库: https://github.com/Gaius-Augustus/Augustus
- License: Artistic-1.0
- 构建系统: Makefile（无 configure，直接 make）

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 3.5.0 | built | 2026-08-30 |

## 依赖

- **无 conan 依赖**（minimal 配置）
  - ZIPINPUT=false：关闭 boost_iostreams（gzip 输入）
  - COMPGENEPRED=false：关闭比较基因预测（CGP），消除 gsl/lpsolve/suitesparse/sqlite/mysql

## 编译说明

```bash
conan create archives/a/augustus/3.5.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## HarmonyOS 平台适配

- 上游 Makefile 硬编码 `CXX ?= g++`；构建时经 conan conf 传 CXX=clang++（R33）
- 上游 install 目标建 PREFIX/bin 符号链接；HMFS 上符号链接受限，package() 直接打包 bin/ + config/
- 可执行 ELF 需 binary-sign-tool 自签（E077/E082），否则 OHOS 内核拒绝执行

## 运行说明

```bash
export AUGUSTUS_CONFIG_PATH=<包内 config/ 路径>
augustus --species=human <input.fa>
```
