# pachi

## 简介

Pachi 是一个模块化的围棋（Go/Weiqi/Baduk）引擎框架，默认 UCT 引擎结合 Monte Carlo 与树搜索（UCB1AMAF + RAVE），semi-random Moggy playout。19x19 可达 KGS 3d 水平，9x9 可达 7d。

## 功能概述

- GTP 协议客户端（`pachi` 二进制），可配合 GoGui/Sabaki/Lizzie 或 kgsGtp 使用
- UCT 引擎、多种 playout 策略、tactics 库
- 自带 t-unit 单元测试与 GTP 回归测试

## OHOS 适配

### 适配要点

- 标准 Makefile 工程，无 configure，使用 `Makefile` + `Makefile.linux`：
  ```bash
  make DCNN=0 JOSEKIFIX=0 GENERIC=1 CC=clang CXX=clang++ -j1
  ```
- 默认 `DCNN=1 JOSEKIFIX=1` 需要 Caffe/Boost/OpenBLAS/KataGo，OHOS/CI 无此依赖，必须关闭，仅保留纯 MCTS 引擎
- `GENERIC=1` 避免 `-march=native`，保证分发二进制可移植
- 编译器必须从 Conan 配置取（R33），`make -j1`（R9）
- 无标准 `make install` 语义，按 `BINDIR/DATADIR` 手动安装 `pachi` 与数据文件

### 已知问题

- DCNN 与 josekifix（含 KataGo CPU 构建，需 cmake+Eigen+在线模型下载）在 OHOS 上不支持，已关闭
- t-unit 的 `run_tests` 上游脚本依赖 `git ls-files`，源码归档无 `.git`，配方改为直接枚举 `t-unit/*.t` 运行

### 与 Linux 的差异

- Linux 全功能构建含 dcnn/josekifix；OHOS 仅 nodcnn 构建，棋力略低但功能完整

## 依赖

### 编译依赖
- 无外部依赖（nodcnn 构建仅需 libc/libm/pthread/dl）
- 编译器：clang

### 运行依赖
- 无（单可执行文件；数据文件随包安装）

## 功能验证

```bash
pachi --version
echo "boardsize 9\nclear_board\ngenmove b\nquit" | pachi -d0 -t =100
```

## 参考

- 官方仓库：https://github.com/pasky/pachi
- 官网：http://pachi.or.cz/
- 构建说明：INSTALL.md
