# tipidee 0.0.6.0 适配笔记

## 编译环境
- 构建系统: skarnet custom configure + Makefile
- 编译日期: 2026-08-22
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# tipidee depends on skalibs - build skalibs first
CC=clang ./configure \
  --prefix=$PREFIX \
  --with-include=$SKALIBS_PREFIX/include \
  --with-lib=$SKALIBS_PREFIX/lib \
  --with-dynlib=$SKALIBS_PREFIX/lib \
  --with-sysdeps=$SKALIBS_PREFIX/lib/skalibs/sysdeps \
  --enable-pkgconfig \
  --disable-shared
make -j1
make install DESTDIR=$STAGING
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 sysdeps 目录不存在 | skarnet 默认从 $PREFIX/lib/skalibs/sysdeps 查找 sysdeps | 显式指定 --with-sysdeps 指向 skalibs 安装目录 |
| 2 | CI L0i 连续 4 次失败 registry_unreachable | require 的 skalibs/2.14.4.0 从未发布到制品仓（PR #6206 未合入）；cnb.cool 对不存在包返回 "system acceleration policy not enabled" 非 404 错误，被 CI 误分类 | 依赖切换到已发布的 skalibs/2.15.1.0（main 已合入且二进制已在制品仓） |
| 3 | CI 环境 CC/PATH 不可用风险 | build() 未用 env="conanbuild"，CI worker 默认 PATH 不含 /data/service/hnp/bin | build()/package() 所有 self.run 加 env="conanbuild"（CC/CXX/PATH 由 profile 注入），并按 skalibs 配方模式注入 --sysroot |

## 源码修改

无补丁。tipidee 源码在 OHOS 上原生编译完全通过。

## 依赖版本

- skalibs/2.15.1.0 (提供 libskarnet 和 sysdeps；原 2.14.4.0 的 PR #6206 未合入、从未发布到制品仓，CI L0i 依赖闸因此连续失败，故切换到已发布的 2.15.1.0)

## 验证结果

```bash
$ make check
# No test suite defined, exit 0
$ ./tipideed --version
tipideed: pid xxxx: usage: tipideed [ -f cdbfile ] [ -d basedir ] [ -R ] [ -U ]
$ ./tipidee-config --version
# tipidee-config works (spawns tipidee-config-preprocess)
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libtipidee.a | 静态库 |
| bin/tipideed | HTTP 守护进程 |
| bin/tipidee-config | 配置工具 |
| libexec/tipidee-config-preprocess | 配置预处理器 |
| libexec/ls.cgi | CGI 目录列表 |
| include/tipidee/*.h | 头文件 |

## 注意事项

- tipidee 依赖 skalibs 的 sysdeps 目录，该目录在 skalibs configure 阶段自动生成
- conanfile.py 通过 self.dependencies["skalibs"].package_folder 构造 sysdeps 路径
- 产物同时包含库和可执行文件
---

**编译结束**: 2026-09-17 14:24
**最终状态**: built
