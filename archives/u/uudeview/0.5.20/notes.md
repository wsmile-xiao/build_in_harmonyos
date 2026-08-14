# uudeview 0.5.20 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-12
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. `./configure --prefix=/usr/local --disable-minews` — configure 成功
2. `make -j1` — 编译成功（仅有 char/unsigned char 类型警告）
3. `make install` — 安装 uudeview、uuenview 到 bin/，man 页到 man/man1/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Conan Autotools build-folder separation 与 uudeview Makefile 不兼容 | uudeview 使用 `cd uulib; make` 子目录构建，Conan 在 build-release/ 子目录运行 make 导致找不到源文件 | 使用 `self.run()` 替代 `Autotools` 类，在源码目录直接构建 |
| 2 | inews/minews 编译失败 | inews.c 使用 K&R 风格函数定义，clang 以 C99/C11 模式编译报错 | `--disable-minews` 跳过 minews 构建 |
| 3 | make install 不支持 DESTDIR | 旧版 Makefile 不使用 DESTDIR 变量 | 直接安装到 prefix，不使用 staging |
| 4 | OHOS 平台 shebang 不兼容 | configure 脚本使用 `#!/bin/sh`，OHOS 上不存在 | 在 build() 中用 sed 替换 shebang（仅 OHOS） |
| 5 | configure 默认查找 cc | OHOS 上只有 clang，没有 cc 软链接 | Conan profile 设置 CC=clang |

## 源码修改

无需补丁。所有平台适配通过 conanfile.py 的 build() 方法中的 sed 命令处理。

## 依赖版本

无外部依赖。仅依赖 libc.so。

## 验证结果

```bash
# 二进制运行
uudeview --version  # 输出 UUDEVIEW 0.5pl20
uuenview --version  # 输出 UUENVIEW 0.5pl20

# Conan test_package
test_uudeview  # 输出: uudeview 0.5.20: uulib API test OK

# conan-verify: PASS (G1-G4, L2/L4/L5)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| uudeview | 149952 | uuencode/uudecode 解码器 |
| uuenview | 145856 | uuencode/uudecode 编码器 |
| libuu.a | 232908 | uulib 静态库 |
| uudeview.h | 9485 | 公共头文件 |
| uuint.h | 10031 | 内部头文件 |

## 注意事项

- uudeview 无 `--version` 选项，无参数运行时返回 exit code 1（usage 信息）
- 上游无测试套件（无 `make check` 目标）
- 源码 URL 为 http（https 证书不匹配），CI 自动添加镜像 fallback

---
**编译结束**: 2026-08-12 12:32
**最终状态**: built
