# coinmp 1.8.4 适配笔记

## 编译环境
- 构建系统: autotools（COIN-OR 递归 configure：顶层 + CoinMP/）
- 编译日期: 2026-09-21
- 编译器: clang/clang++ 15.0.4
- 状态: built

## 编译步骤
```bash
# 1. 依赖（制品仓已全部发布）
#    cbc/2.10.13、clp/1.17.10、cgl/0.60.10.1、coin-or/0.108.12、
#    coinutils/2.11.13、zlib/1.3.1

# 2. 修补 config.sub（2019-02-24 版不识别 musl 三元组）
#    在 kernel-OS 列表和 OS 后缀列表加 linux-musl*

# 3. configure（静态）
./configure --prefix=/ --build=aarch64-unknown-linux-musl \
  --host=aarch64-unknown-linux-musl --disable-dependency-tracking \
  --disable-shared --enable-static \
  --with-cbc-incdir=... --with-cbc-lib='...libOsiCbc.a ...libCbcSolver.a ...libCbc.a ...'

# 4. config.status 修补（HMDFS umask 077 + SGID）：
#    sed 's|mktemp -d -q "./confstatXXXXXX"|mkdir -p ./conftmp|' \
#    sed 's|tmp=./confstat$$-$RANDOM|tmp=./conftmp|' + umask 022 后重跑

# 5. Makefile 中 -l* 替换为依赖包绝对 .a 路径（libtool .la 无效路径规避）

# 6. make -j1 && make -j1 check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.sub: `machine aarch64-unknown-linux not recognized` | CoinMP 1.8.4 自带 2019-02-24 config.sub 不识别 aarch64-unknown-linux-musl 四段式三元组 | build() 中 Python 文本替换，在 kernel-OS 列表加 `linux-musl*`、OS 后缀列表加 `-linux-musl*`（已实测验证） |
| 2 | libtool 解析依赖包 `.la` 报 `'//lib/libClp.la' is not a valid libtool archive` | conan 依赖包 .la 内 libdir='//lib' 无效 | configure 注入 --with-cbc-lib 绝对路径 + make 前 sed 替换 Makefile 中 -l* 为绝对 .a 路径 |
| 3 | configure confstat 临时目录不可写 | HMDFS umask 077 + SGID | 修补 config.status（mktemp→mkdir conftmp + umask 022）并重跑 |
| 4 | 运行时 `libc++_shared.so` 找不到（LD_LIBRARY_PATH 缺 SDK） | OHOS SDK libc++ 不在默认搜索路径 | test_package 从编译器 resource-dir 推导 SDK lib 目录注入 LD_LIBRARY_PATH（同 abseil 先例） |
| 5 | static 模式 libtool 硬链接 `Operation not permitted` | 本地 HMDFS 不支持跨目录硬链接（libCoinMP.lax） | 修正 cbc.pc 残留 .cache/conan2 路径后静态打包成功 |

## 依赖版本
- cbc/2.10.13（含 coinutils/clp/cgl/coin-or/zlib 传递闭包）
- clp/1.17.10
- cgl/0.60.10.1（修复版：含 CglLandP 头文件与符号）
- coin-or/0.108.12（Osi）
- coinutils/2.11.13
- zlib/1.3.1

## 验证结果
```bash
# 上游测试（make test → unitTest）：exit 0，8 个 LP/MIP 问题全部 Optimal
# CoinTest/Afiro/Bakery/Exmip1/GamsSos1a/GamsSos2a/P0033/SemiCont
# conan-verify：G0-G4 + L2/L4/L5 全 PASS
# test_package 消费者：CoinMP C-API 求解 CoinTest，目标值 1428729.28571 匹配
```

## 交付物
- libCoinMP.a（静态，含 COIN-OR 依赖闭合）
- CoinMP.h / CoinMPConfig.h / config_coinmp.h
- coinmp.pc

## 注意事项
- CoinMP 是 C-API 接口库，封装 CLP/CBC/CGL；configure 只探测 Cbc（cbc clp osi-clp），依赖闭包经 cbc 传递
- 上游无独立测试框架（make check 空），测试入口为 make test（unitTest）
---

**编译结束**: 2026-09-21 11:47
**最终状态**: built
