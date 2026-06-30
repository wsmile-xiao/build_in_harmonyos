# ipopt

## 软件描述

IPOPT (Interior Point OPTimizer) 是 COIN-OR 项目的一个开源非线性优化求解器。

- **官方主页**: https://coin-or.github.io/Ipopt/
- **许可证**: EPL-2.0

## 编译状态

| 版本 | 状态 | 编译日期 | 构建系统 | 说明 |
|------|------|----------|----------|------|
| 3.14.19 | built | 2026-05-29 | autotools | 使用 OpenBLAS 作为 BLAS/LAPACK 后端 |

## 库文件

- `libipopt.so` - IPOPT 主库
- `libsipopt.so` - sIPOPT 扩展库

## 依赖

- OpenBLAS 0.3.26 (BLAS/LAPACK 后端)

## 编译说明

### 已知问题

1. **平台适配**: 需要修改 config.guess/config.sub 支持 OpenHarmony
2. **OpenBLAS**: 需要使用 USE_THREAD=0 编译的 OpenBLAS，避免 pthread_setaffinity_np 问题
3. **LAPACK**: 使用 OpenBLAS 内置的 LAPACK wrapper

### 补丁文件

主要补丁：
- config.guess.patch - OpenHarmony 系统识别
- config.sub.patch - OpenHarmony triplet 支持

## 使用方法

```bash
# 通过 pkg-config 使用
pkg-config --cflags ipopt
pkg-config --libs ipopt
```
