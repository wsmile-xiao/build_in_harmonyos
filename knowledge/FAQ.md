# 鸿蒙编译常见问题快速参考

> 详细错误排查见 `error-patterns.md` 和 `knowledge/graph/`（E001-E211）。

## 环境变量速查

| 变量 | 推荐值 | 用途 |
|------|--------|------|
| CC | clang | C 编译器 |
| CXX | clang++ | C++ 编译器 |
| AR | llvm-ar | 归档工具 |
| RANLIB | llvm-ranlib | 库索引 |
| CFLAGS | -fPIC -O2 | 编译标志 |
| TMPDIR | $HOME/tmp | 临时目录（/tmp 只读） |
| PATH | $HOME/usr/local/bin:$PATH | 命令路径 |
| LD_LIBRARY_PATH | $HOME/usr/local/lib | 共享库路径 |

## 三元组格式

| 架构 | 三元组 |
|------|--------|
| ARM64 | aarch64-unknown-linux-ohos |
| ARM32 | arm-unknown-linux-ohos |
| x86_64 | x86_64-unknown-linux-ohos |

## 知识文件索引

| 文件 | 内容 |
|------|------|
| operations/environment.md | 系统环境特性 |
| operations/build-systems.md | 构建系统识别与适配 |
| operations/debug-methodology.md | 问题排查流程 |
| error-patterns.md | 错误模式总览（E001-E211） |
| musl-compat.md | musl/glibc 兼容性差异 |
| operations/packaging.md | Conan 打包技术参考 |
| operations/python-extensions.md | Python 扩展编译 |
| operations/dependencies.md | 依赖关系图 |
| operations/harmonyos-specifics.md | 鸿蒙特异性 |

---

*文档版本: 2.1 · Conan 体系适配*
