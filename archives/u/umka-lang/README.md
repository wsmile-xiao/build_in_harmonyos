# Umka-lang

> Umka: a statically typed embeddable scripting language

## 简介

Umka 是一种静态类型的可嵌入脚本语言，支持闭包、动态数组、映射、接口、泛型、协程（fibers）、垃圾回收等特性。它设计为可嵌入 C/C++ 应用程序，提供类似 Lua 的轻量级脚本能力，同时具备静态类型检查的优势。

Umka 由 Vasiliy Tereshkov 开发，使用 BSD-2-Clause 许可证。

## OHOS 适配要点

1. **平台检测**：umka-lang 的 Makefile 通过 `uname -s` 检测平台。HarmonyOS 上 `uname -s` 返回 `HarmonyOS` 而非 `Linux`，导致平台分支不匹配。编译时需通过 `PLATFORM=Linux` 命令行参数覆盖。

2. **构建系统**：umka-lang 使用纯 Makefile 构建，**不是 autotools 项目**，没有 `configure` 脚本。直接执行 `make` + `make install` 即可。

3. **Conan 配方**：Conan 配方中 `build()` 和 `package()` 方法需使用 `cwd=self.source_folder`，因为 `basic_layout` 会将构建目录设为子目录，而 Makefile 位于源码根目录。

4. **编译器警告**：clang 不支持 `-s` 标志（Makefile 将其用于编译阶段），产生 `-Wunused-command-line-argument` 警告，不影响构建结果。

## 依赖

无外部依赖。仅需 C 编译器（clang）和 make。

## 功能验证

```bash
# 编译
make -j1 PLATFORM=Linux PREFIX=$HOME/usr/local

# 安装
make install PLATFORM=Linux PREFIX=$HOME/usr/local DESTDIR=/tmp/test-install

# 验证二进制
./build/umka
# 输出: Umka 1.5.5 (... 64 bit)

# 运行测试套件
cd tests/lib && cc -fPIC -O3 -c lib.c && cc -shared -fPIC *.o -o lib.umi && rm -f *.o && cd ..
./build/umka all.um
# exit code: 0 (测试通过)
```

## 参考

- [官方仓库](https://github.com/vtereshkov/umka-lang)
- [在线演示](https://vtereshkov.github.io/umka-lang/)
