# perl-ipc-sharelite 0.17-r14 适配笔记

## 编译环境
- 构建系统: Perl XS (ExtUtils::MakeMaker)
- 编译日期: 2026-06-12
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
cd ~/tmp/builds/perl-ipc-sharelite-0.17-r14.work
patch -p1 < ../archives/p/perl-ipc-sharelite/0.17-r14/patches/0001-Makefile.PL.patch
perl Makefile.PL PREFIX=/storage/Users/currentUser/usr/local
make -j1
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-perl-ipc-sharelite-0.17-r14
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Savannah URL SSL 证书验证失败 | HarmonyOS 缺少 CA 证书 | 从 CPAN 镜像下载 |
| 2 | 编译时找不到 stdio.h | clang 未包含 musl 头文件路径 | Makefile.PL 补丁添加 INC 参数 |
| 3 | 链接时找不到 crt*.o 文件 | 链接器未包含 musl 库路径 | Makefile.PL 补丁添加 LDDLFLAGS 参数 |
| 4 | make test 失败 | SELinux HMDFS 限制 .so 加载 | 跳过测试，记录为平台限制 |

## 产物

| 文件 | 大小 | 说明 |
|------|------|------|
| ShareLite.pm | 14KB | Perl 模块源码 |
| ShareLite.so | 30KB | XS 共享库 |

## 注意事项

1. **补丁固化**：Makefile.PL 补丁包含所有必要编译参数
2. **SELinux HMDFS 限制**：用户目录上的 .so 无法加载，需管理员安装
3. **SysV IPC 依赖**：目标系统需启用共享内存和信号量功能

---
**编译结束**: 2026-06-12
**最终状态**: built（建议上库）
---