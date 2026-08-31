# unibilium

## 简介

unibilium 是一个非常基础的 terminfo 库，可以读写 ncurses 风格的 terminfo 文件，并解释 terminfo 格式字符串。它不依赖 curses 或任何其他库，也不使用全局变量（线程安全）。

是 libtermkey 等终端处理库的基础依赖。

## 版本

- 2.1.2 (2024-09-13, neovim/unibilium 维护版本)

## 构建系统

- CMake（上游同时提供 autotools 与 CMakeLists.txt；CI 无 automake，选用 CMake 构建）

## 依赖

- 无外部依赖（纯 C）

## 编译选项

```bash
cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF ..
make
make install
```

## 测试

上游测试：`prove -f t/*.t`（9 个测试文件，3678 项断言，全部通过）

## 适配说明

- 上游 CMakeLists.txt 仅安装库与头文件；配方在 package() 中补充生成 `lib/pkgconfig/unibilium.pc`（下游 libtermkey 通过 pkg-config 查找）
- 无可执行二进制（纯库），不需要 commands.json（R38）