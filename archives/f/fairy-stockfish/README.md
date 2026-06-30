# fairy-stockfish

**描述**: Fairy-Stockfish 是一个支持多种国际象棋变体的 UCI/XBoard 棋类引擎，基于 Stockfish 衍生开发。

**主页**: https://github.com/fairy-stockfish/Fairy-Stockfish  
**许可证**: GPL-3.0  

## 已编译版本

| 版本 | 状态 | 日期 | 构建系统 | 编译器 | 架构 |
|------|------|------|----------|--------|------|
| 14 | published | 2026-06-29 | Makefile | clang 15.0.4 | armv8 (AArch64) |

## 构建说明

fairy-stockfish 使用自定义 Makefile（非 autotools/cmake），构建命令：

```bash
make build ARCH=armv8 COMP=clang
```

### 关键适配

1. **移除 -latomic**: 鸿蒙 aarch64 平台无 libatomic 库，ARMv8 原子操作内建
2. **静态链接 C++ 运行时**: 添加 `-static-libstdc++` 满足 R26 铁律
3. **ghfast.top 镜像**: GitHub 直连超时，使用镜像 URL

### 产物

- `bin/stockfish` — 棋类引擎可执行文件 (ELF64 AArch64)
- 仅依赖系统库 `libc.so`
