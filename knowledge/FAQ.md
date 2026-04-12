# 鸿蒙编译常见问题快速问答 (FAQ)

本文档提供鸿蒙系统上编译软件的常见问题快速解答。

---

<!-- ~~## 一、环境配置~~ → 已迁移至 E001(找不到编译器), E002(/tmp只读), environment.md §4(完整环境变量模板) -->

<!-- ~~## 二、编译错误~~ → 已迁移至 E001(cc不存在), E007(config.guess失败), E076(fstat/lseek非文件fd) -->

<!-- ~~## 三、链接错误~~ → 已迁移至 E078(BIND_NOW符号找不到), E016(OpenSSL no-asm), E042+E075(找不到库+C_INCLUDE_PATH冲突) -->

<!-- ~~## 四、运行时错误~~ → 已迁移至 E075(pkg-config空), E009/E055(SELinux子进程), E076(fstat Permission denied), E050/E073(软链接), E042/E078(RPATH/BIND_NOW) -->

<!-- ~~## 五、工具问题~~ → 已迁移至 E017(toybox expr/sed不兼容) -->

<!-- ~~## 六、构建系统~~ → 已迁移至 E007(Autotools适配), build-systems.md(构建系统识别/CMake) -->

<!-- ~~## 七、Python 相关~~ → 已迁移至 E033(curses宽字符), E080(venv symlink), python-extensions.md(扩展模块编译) -->

<!-- ~~## 八、调试技巧~~ → 已迁移至 debug-methodology.md -->

## 九、快速参考

### 环境变量速查

| 变量 | 推荐值 | 用途 |
|------|--------|------|
| CC | clang | C 编译器 |
| CXX | clang++ | C++ 编译器 |
| AR | llvm-ar | 归档工具 |
| RANLIB | llvm-ranlib | 库索引 |
| CFLAGS | -fPIC -O2 | 编译标志 |
| TMPDIR | $HOME/tmp | 临时目录 |
| PATH | $HOME/usr/local/bin:$PATH | 命令路径 |
| LD_LIBRARY_PATH | $HOME/usr/local/lib | 共享库路径 |

### 三元组格式

| 架构 | 三元组 |
|------|--------|
| ARM64 | aarch64-unknown-linux-ohos |
| ARM32 | arm-unknown-linux-ohos |
| x86_64 | x86_64-unknown-linux-ohos |

### 知识文件索引

| 文件 | 内容 |
|------|------|
| environment.md | 系统环境特性 |
| build-systems.md | 构建系统识别 |
| troubleshooting.md | 问题排查流程 |
| error-patterns.md | 44种错误模式 |
| musl-compat.md | musl/glibc 差异 |
| python-extensions.md | Python 扩展编译 |
| doc/E007.md | Autotools 适配 |
| harmonyos-specifics.md | 鸿蒙特异性 |
| dependencies.md | 依赖关系图 |

---

*文档版本: 1.1*  
*最后更新: 2026-03-26*