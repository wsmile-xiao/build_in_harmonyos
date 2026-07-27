# microjson 1.6 适配笔记

## 编译环境
- 构建系统: makefile (plain make, no configure)
- 编译日期: 2026-07-15
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

1. 下载源码: `https://github.com/Otteri/microjson/archive/refs/tags/1.6.tar.gz`
2. 解压并进入源码目录
3. 修改 Makefile: 修复 example 链接规则（补丁 0001-Makefile.patch）
4. 直接编译 mjson.o: `clang -O -DDEBUG_ENABLE -g -DTIME_ENABLE -c -o mjson.o mjson.c`
5. 创建静态库: `llvm-ar rcs libmjson.a mjson.o && llvm-ranlib libmjson.a`
6. 运行测试: `make check` (test_microjson + test_microjson_wignore 均通过)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | example 编译失败: `cannot specify -o when generating multiple output files` | Makefile example 规则缺少显式 recipe，隐式规则将 mjson.c 作为额外源文件编译 | 添加显式 recipe，将 mjson.c 改为 mjson.o 依赖 |
| 2 | conan create: `No rule to make target 'mjson.o'` | Makefile 的 `.SUFFIXES` 声明清除了默认后缀列表，禁用了内置 .c→.o 规则 | 在 conanfile.py 中直接调用 cc 编译 mjson.o，不依赖 make 隐式规则 |
| 3 | conan create: `no such file or directory: 'mjson.c'` | self.run() 在 build folder 执行，源文件在 source folder | 使用 `self.source_folder` 拼接源文件路径 |
| 4 | test_package: `Library 'mjson' not found in package` | package() 从 self.source_folder 复制 libmjson.a，但文件在 build folder | 改用 `self.build_folder` 作为复制源 |
| 5 | test_package: `initializer element is not a compile-time constant` | test.c 中局部变量地址不是编译期常量，不能用于 static 数组初始化 | 改用文件作用域 static 变量（同上游 example1.c 模式） |

## 源码修改

- `patches/0001-Makefile.patch`: 修复 Makefile 中 example1-4 的链接规则，添加显式 recipe

## 依赖版本

无外部依赖（纯 C 标准库）

## 验证结果

```bash
# 上游测试
$ make check
./test_microjson
microjson unit test succeeded.
./test_microjson_wignore
...

# Conan L1 测试
$ conan create ... (test_package)
microjson L1 test passed: count=42, flag1=1, flag2=0, name=hello
```

## 注意事项

- Makefile 的 `.SUFFIXES` 会禁用内置编译规则，不能依赖 `make mjson.o`
- 库名为 `mjson`（不是 `microjson`），头文件为 `mjson.h`
- 静态库为 `libmjson.a`
---

**编译结束**: 2026-07-15 09:23
**最终状态**: built
