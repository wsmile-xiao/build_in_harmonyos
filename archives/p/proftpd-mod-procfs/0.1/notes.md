# proftpd-mod-procfs 0.1 适配笔记

## 编译环境
- 构建系统: custom（prxs/clang 直接编译 DSO）
- 编译日期: 2026-08-11
- 编译器: clang 15.0.4（OHOS）
- 状态: published

## 编译步骤

1. `ohc-run.py init-build proftpd-mod-procfs 0.1 --url=https://github.com/Castaglia/proftpd-mod_procfs/archive/refs/tags/v0.1.tar.gz`
2. 验证依赖：proftpd 头文件树（conf.h/privs.h 闭包，73 个头文件）+ prxs 工具
3. 以 proftpd 1.3.9c 源码树为构建宿主（含头文件），mod_procfs.c 经 export_sources 附带
4. conanfile.py：clang -fPIC -DPR_SHARED_MODULE -DLINUX 直接编译 mod_procfs.c → mod_procfs.so
5. test_package：校验 mod_procfs.so ELF 有效性与 procfs_module 符号（R34）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | prxs 报 Permission denied | 构建树内 prxs 为 perl 脚本缺执行位 | chmod 755 修复 |
| 2 | prxs: libtool unable to infer tag | clang 无 --tag 推断 | 创建 libtool-cc-wrap 注入 --tag=CC |
| 3 | mod_procfs.c: config.h not found | 独立 tarball 无 proftpd 头文件 | 以 proftpd 1.3.9c 源码树为构建宿主（含头文件），复用 8 个 OHOS 补丁 |
| 4 | prxs 需 $sbindir/proftpd | prxs 校验 proftpd -l 含 mod_dso | 提供 stub proftpd 或改用 clang 直接编译 |

## 源码修改
无（纯 DSO 编译，无源码补丁）

## 测试结果
- 消费者验证：mod_procfs.so ELF 校验 + procfs_module 符号校验（3/3）
- 上游无独立测试（tests.pl 依赖完整 ProFTPD 环境）
---

**编译结束**: 2026-08-11 12:26
**最终状态**: published
