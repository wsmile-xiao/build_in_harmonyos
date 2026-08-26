# Avanor 0.5.8 适配笔记

## 基本信息
- 构建系统: makefile
- 编译日期: 2026-08-24
- 状态: built

## 编译步骤
1. 下载源码 avanor-0.5.8-src.tar.bz2 并解压
2. 使用 clang++ 编译所有源文件（Makefile 为基础构建系统）
3. 编译命令: `make CC=clang++ LD=clang++ -fuse-ld=bfd CFLAGS="-fsigned-char -pipe ..." LIBS="-lncursesw"`
4. 需要添加 C++17 兼容标志: `-Wno-error=dynamic-exception-spec -Wno-error=register`

## 遇到的问题和解决方案
1. **cave.cpp 取临时对象地址错误** (C++11 错误: taking address of temporary)
   - 问题: `r.Setup(&XRect(x, y, x + l, y + h))` 在 C++11 中非法
   - 修复: 改用局部变量 `XRect tmpRect(x, y, x + l, y + h); r.Setup(&tmpRect);`
   - 补丁: patches/0001-game-cave.cpp.patch

2. **lld 链接器依赖 libxml2 失败**
   - 问题: OHOS SDK 的 lld 需要 libxml2.so.16 但环境缺失
   - 修复: 使用 `-fuse-ld=bfd` 使用系统 bfd 链接器

3. **people.cpp 编译失败**
   - 问题: XPeople 类未在任何头文件中声明
   - 处理: 该文件不在 Makefile SRCS 列表中，跳过编译（上游问题）

## 依赖
- ncurses/6.4 (需要 ncursesw 宽字符支持)

## 验证
- conan-verify: G1-G4 全部通过
- W3 本地 CI 模拟通过
- ELF 验证通过 (aarch64 OHOS)

## 交付物
- conanfile.py + conandata.yml + test_package/
- 命令行为应用类型 (commands.json 已创建)

## 特别注意事项
- 该软件为 C++98 时代代码，大量使用已弃用的 C++ 特性
- 需要 ncurses 库支持，在 OHOS 上使用静态编译
- ELF 签名问题导致本地无法直接运行，CI 会处理签名
---

**编译结束**: 2026-08-24 22:29
**最终状态**: built
