# pmccabe

> McCabe 复杂度分析工具，用于度量 C/C++ 源代码的圈复杂度。

## 简介

pmccabe 是一组代码分析工具，最初由 Hewlett-Packard 开发，基于 GPL-2.0 许可证发布。主要功能包括：

- **pmccabe**: 计算 C/C++ 源代码的 McCabe 圈复杂度（cyclomatic complexity），支持多种输出模式（排序、非排序、详细/摘要）
- **decomment**: 从 C/C++ 源文件中移除注释
- **codechanges**: 分析代码变更（shell 脚本）
- **vifn**: 函数索引查看器（shell 脚本）

pmccabe 通过将所有 C 源文件合并为单一编译单元（combined.c）进行编译，使用 `-fwhole-program` 优化。

## OHOS 适配要点

1. **构建系统为纯 Makefile**：虽然 init-build 标注为 autotools，但 pmccabe 实际使用纯 Makefile，没有 configure 脚本。直接 `make CC=clang` 即可编译。
2. **INSTALL 变量需覆盖**：Makefile 中 `INSTALL = install -o root -g root`，在鸿蒙上因无 root 用户会失败，需覆盖为 `INSTALL="install"`。
3. **make -j 并行构建不可用**：HMDFS 文件系统不支持 mkfifo，`make -j2` 会报 `Operation not permitted`。使用单线程 make。
4. **无外部依赖**：pmccabe 仅依赖系统 libc，不需要任何第三方库。
5. **pmccabe 无参数读 stdin**：pmccabe 不带参数时会从标准输入读取，导致挂起。脚本化测试时需传入文件参数。
6. **getopt.c 旧式声明警告**：编译时产生 8 个 deprecated-non-prototype 警告，来自 getopt.c 的 K&R 风格函数声明，不影响功能。

## 排除与替代

无。所有程序（pmccabe、decomment、codechanges、vifn）均正常工作。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| 无 | - | pmccabe 是纯 C 工具，仅依赖系统 libc |

## 功能验证

```bash
# 编译
make CC=clang CXX=clang++

# 安装
make install DESTDIR=$TEST_PREFIX INSTALL="install"

# 运行测试套件
make test

# 功能验证
echo 'int main() { return 0; }' > test.c
pmccabe test.c
```

## 参考

- [GitLab 仓库](https://gitlab.com/pmccabe/pmccabe)
- [McCabe 复杂度 - Wikipedia](https://en.wikipedia.org/wiki/Cyclomatic_complexity)
