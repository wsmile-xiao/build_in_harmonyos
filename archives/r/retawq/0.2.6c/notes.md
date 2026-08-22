# retawq 0.2.6c 适配笔记

## 编译环境
- 构建系统: makefile (classical Makefile, not autotools)
- 编译日期: 2026-08-22
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 使用 conan 安装 ncurses/6.4 依赖
2. 创建 libncurses.a -> libncursesw.a 符号链接 (conan ncurses 提供 widechar 版本)
3. 修改 Makefile: CC=gcc → CC=clang, 添加 ncurses include/lib 路径
4. `make config` 生成 .config 头文件 (configure script simulation)
5. `make retawqbin` 编译目标文件并链接
6. `make install` 安装到 staging 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 脚本失败: "can't create subst: Permission denied" | itchconfig 生成的 configure 脚本使用 exec fd 重定向, OHOS 文件系统不支持 | 使用 classical Makefile 替代 configure 脚本 |
| 2 | -lncurses 找不到库 | conan ncurses 包提供 libncursesw.a (widechar), 非 libncurses.a | 创建符号链接 libncurses.a → libncursesw.a |
| 3 | 编译器警告 (void-pointer-to-int-cast 等) | 上游代码使用 int/pointer 转换宏, 64 位平台指针大于 int | 警告不影响编译, 保留上游行为 |

## 源码修改

无补丁文件。Makefile 修改通过 conanfile.py 的 build() 方法在编译时动态设置 CC/CFLAGS/LDFLAGS。

## 依赖版本

- ncurses/6.4 (conan 制品仓)
- pthreads (系统 libc)

## 验证结果

```bash
$ file retawq
retawq: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), stripped

$ llvm-readelf -d retawq | grep FLAGS
  (FLAGS)        BIND_NOW
  (FLAGS_1)      NOW PIE
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/retawq-0.2.6c | 主程序二进制 |
| bin/retawq → retawq-0.2.6c | 符号链接 |
| man/man1/retawq.1 | man 手册 |
| doc/retawq/ | HTML 文档 |

## 注意事项

- retawq 的 configure 脚本由 itchconfig 生成, 非标准 autoconf, 在 OHOS 上因 fd 重定向问题无法运行
- conan ncurses 包提供 libncursesw.a (widechar), 需要创建 libncurses.a 符号链接
- 二进制需要 ELF 签名才能在 OHOS 上执行 (CI 流水线 sign.sh 处理)
---

**编译结束**: 2026-08-22 09:05
**最终状态**: built

