# uftrace

## 简介

uftrace 是一个用户态函数（调用图）追踪器，支持 C/C++/Rust 程序。它能记录函数调用关系、耗时、参数和返回值，常被用于性能分析和调试（类似 perf 但面向函数级追踪）。

## OHOS 适配

- **构建系统**: 手写 `./configure` 脚本（非 autotools）生成 `.config`，再由 Makefile 构建
- **补丁 0001**: 手写 configure 的 `uname -s` 检查不识别 HarmonyOS（OHOS 返回 `HarmonyOS` 而非 `Linux`），放宽为 `Linux|HarmonyOS`
- **依赖策略**: 上游无必需外部依赖；本版禁用全部可选特性（libelf/libdw/libpython/libstdc++/ncurses/capstone/libunwind/libtraceevent），走内置 rawelf 兜底解析器，保证最小可靠构建
- **package()**: 因 `make install` 依赖 pandoc 构建 man 页，改为手动复制 `uftrace` 二进制与 5 个 `libmcount*.so` 插桩库
- **产物签名**: 鸿蒙 XPM 要求可执行文件与 .so 代码签名
- **当前状态**: prepared（本机前置适配完成，待真机 shadow CI 验证）

## 依赖

- 无必需外部依赖（编译工具链 clang + make）
- 可选（仓库已适配，可后续启用）: elfutils 0.195（libelf/libdw）、capstone 5.0.7、ncurses 6.6

## 功能验证

```bash
uftrace --version     # uftrace v0.19
uftrace -L <lib/uftrace> ./program   # 通过 -L 指定 libmcount 插桩库路径
```

## 参考

- GitHub: https://github.com/namhyung/uftrace
- 源码: https://github.com/namhyung/uftrace/archive/refs/tags/v0.19.tar.gz
