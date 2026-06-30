# chadwick 0.10.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-26
- 编译器: clang/clang++
- 状态: built (conan-verify 通过)

## 编译步骤

1. init-build 下载源码包（GitHub 超时，使用 curl -L --insecure 手动下载）
2. source .build-context-chadwick-0.10.0 && cd $BUILD_SRC_DIR
3. 替换 config.guess/config.sub（系统 automake 1.17 版本）
4. 运行 autoreconf -fi（修复 automake 版本不匹配）
5. sed 修复 umask 077 → umask 022（HMDFS SGID 权限问题）
6. ./configure --prefix=$DEFAULT_PREFIX
7. make -j1
8. make install DESTDIR=$TEST_PREFIX
9. make check（通过，无测试套件）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别平台 | 旧版 config.guess 不支持 HarmonyOS | 替换为 automake 1.17 的 config.guess/config.sub |
| 2 | config.status 创建临时文件 Permission denied | umask 077 导致 HMDFS SGID 目录无法写入 | sed 替换 umask 077 → umask 022 |
| 3 | automake 版本不匹配 | configure.ac 需要 automake 1.16.3，系统为 1.16.5 | 运行 autoreconf -fi 重新生成构建系统 |
| 4 | GitHub 下载超时 | 网络问题 | curl -L --insecure 手动下载，conandata.yml URL 保持原始 HTTPS |

## 源码修改

探索阶段修改（R3: 不生成 .patch，记录 notes）:
1. config.guess/config.sub: 替换为 automake 1.17 版本
2. configure: sed 's/umask 077/umask 022/g'（2处）
3. autoreconf -fi 重新生成 configure/Makefile.in 等

## 依赖版本

无依赖

## 验证结果

```bash
# make check 通过（无测试套件）
# 安装产物:
# bin/: cwbox, cwcomment, cwdaily, cwevent, cwgame, cwsub
# lib/: libchadwick.a, libchadwick.so*, libchadwick.la
# include/chadwick/: book.h, box.h, chadwick.h, file.h, game.h, gameiter.h, league.h, parse.h, roster.h, util.h
```

## 注意事项

- chadwick 是终端工具（棒球数据处理），R26 要求静态链接
- HMDFS 文件系统 SGID 继承导致 umask 077 创建的目录无法写入文件
- chmod 在 HarmonyOS 上不生效（E046, SELinux 限制）
---

**编译结束**: 2026-06-29 16:39
**最终状态**: built
