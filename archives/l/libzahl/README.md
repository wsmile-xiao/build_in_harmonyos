# libzahl

## 基本信息

| 属性 | 值 |
|------|-----|
| 名称 | libzahl |
| 版本 | 1.0 |
| 描述 | Suckless big integer library for arbitrary size integers |
| 类别 | foundation/math |
| 许可证 | ISC |
| 构建系统 | Makefile |
| URL | https://git.suckless.org/libzahl |

## 功能说明

libzahl 是一个 suckless 风格的 C 大整数库，仅支持整数运算。它提供基本位运算、基本算术、模乘与模幂、随机数生成、数论函数、字符串互转与封送交换等能力。

## 主要特性

- 无外部依赖：仅依赖 libc，纯 C99 实现
- 上游明确非线程安全
- 错误处理使用 setjmp/longjmp
- 上游仅构建静态库 libzahl.a

## 编译选项

```bash
make CC=clang AR=llvm-ar RANLIB=llvm-ranlib -j1 libzahl.a
make CC=clang AR=llvm-ar RANLIB=llvm-ranlib -j1 test && ./test
```

## 关键文件

| 文件 | 说明 |
|------|------|
| zahl.h | 主头文件，包含全部公开 API |
| libzahl.a | 静态库 |
| test.c | 上游官方测试源 |
| test-generate.py | 上游随机测试生成器 |

## 相关链接

- 官方仓库：https://git.suckless.org/libzahl
- GitHub 镜像：https://github.com/maandree/libzahl
