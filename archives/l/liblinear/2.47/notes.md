# liblinear 2.47 — 适配笔记

> 归档时间: 2026-09-24
> 状态: built（本机 conan create 双 profile 绿）

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | liblinear |
| 版本 | 2.47（上游 tag **v247**，非 "2.47"） |
| 上游 | https://github.com/cjlin1/liblinear |
| 许可 | BSD-3-Clause |
| 构建系统 | Makefile（上游无 cmake/configure） |
| 语言 | C/C++（linear.cpp/newton.cpp + train.c/predict.c + 内嵌 blas/） |

## 二、任务背景

任务 #14103（wave10 P0），taskBranch=feat/liblinear-2.47。
main 已有 liblinear/2.50 骨架归档（仅 manifest+notes，无 conanfile.py）——2.47 为版本倒挂件（2.47 < 2.50），合法。
无第三方依赖（内嵌 BLAS 子集 blas/blas.a）。

## 三、适配过程

### 构建要点
1. 上游 Makefile 变量：`CXX ?= g++`、`CC ?= gcc`，`AR ?= ar`、`RANLIB ?= ranlib`（blas/Makefile 内）。
2. OHOS 平台无 g++，且 conan buildenv 中 make 的 `AR`/`RANLIB` 需显式传：
   - `make CXX=clang++ CC=clang AR=llvm-ar RANLIB=llvm-ranlib -j1 all lib`
   - 踩坑①：`RANLIB=llvm-ar` 会让 blas/Makefile 执行 `llvm-ar blas.a`（缺 rcv 修饰）报 "expected [relpos]"。
   - 踩坑②：`AR='llvm-ar rcv'` 会拼成 `llvm-ar rcv rcv`（Makefile 里已有 rcv）报 "No such file"。正确形态是裸 `AR=llvm-ar`。
3. `lib` 目标产 `liblinear.so.5`（-Wl,-soname,liblinear.so.5）；`all` 目标产 train/predict。
4. 无 install 目标——package() 手动复制 linear.h/liblinear.so*/train/predict，并补 liblinear.so → liblinear.so.5 符号链接。

### 上游测试（rule4 全量口径）
上游 liblinear 无 make check/ctest 测试入口。官方验证方式 = README Quick Start：
1. `train heart_scale` → 训练模型（Accuracy 84.0741% 227/270）
2. `predict heart_scale heart_scale.model output` → 预测
本机实测：train 正常收敛（#iter=69, nSV=194），predict 输出正常。
test_package 内嵌 heart_scale 前 8 行样本，实测 predict 8/8 全对（Accuracy = 100% (8/8)）。

### 本机 conan create
```
export LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos:$LD_LIBRARY_PATH
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing -c tools.build:jobs=2 -nr
```
- `-nr`：制品仓 conan.cnb.cool 当日不可达（本机侧网络），liblinear 无外部依赖，本地全量构建不受影响。CI 侧走正常 remote 流程。
- 测试环境需 `llvm/lib/aarch64-linux-ohos`（含 libc++.so）——cmake 4.1.2 二进制动态依赖 libc++ 符号，默认 loader 路径找不到。

## 四、交付物清单

- conanfile.py（Makefile 构建配方）
- conandata.yml（GitHub v247 tarball + sha256）
- test_package/（CMake + CMakeDeps；API 冒烟 test_liblinear.cpp + train/predict CLI 工作流）
- commands.json（train/predict 命令行工具声明，R38）
- manifest.yaml ×2（软件级 + 版本级）
- notes.md（本文件）

## 五、版本号说明

- 上游 tag 形态 v247，对应版本号 2.47（linear.h LIBLINEAR_VERSION=247）。
- main 已有 2.50 骨架归档（无配方），本 2.47 为倒挂件，任务指定版本合法。
