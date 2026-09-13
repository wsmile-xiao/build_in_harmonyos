# chrootuid 1.3 适配笔记

## 编译环境
- 构建系统: raw Makefile（1993 年，无 configure）
- 编译日期: 2026-09-10
- 编译器: clang（OHOS aarch64）
- 状态: built

## 编译步骤

1. Conan 配方 build()：先删除 tarball 自带的 i386 预编译 ELF `chrootuid`，
   再 `make CC=clang CFLAGS='-O' chrootuid`（命令行变量覆写，codonw 先例）
2. package()：上游 install 目标写死 /usr/local 不可用 → 手动拷贝
   bin/chrootuid + share/man/man1/chrootuid.1 + licenses（README、chrootuid_license）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tarball 自带 1993 年 i386 预编译 ELF `chrootuid`，make 因目标新于源码静默跳过编译 | 上游发布习惯（含二进制） | build() 先 os.remove 预编译产物再 make；package 白名单拷贝防旧产物入包 |
| 2 | 上游 install 目标写死 /usr/local 且含 /usr/local/man | 1993 年惯例 | 不用 make install，conan copy() 手动打包（clzip 家族先例） |
| 3 | 官方源 ftp.porcupine.org 间歇 404/拒连（Apache 1.3） | 上游服务器老旧不稳定 | conandata 用 archive.ubuntu.com pristine 源 + Debian chrootuid_1.3-6.dsc 哈希互证（决策链记录） |

## 源码修改

无源码补丁（patches/ 为空）。

## 依赖版本

- 运行依赖：无（单文件 C，仅 libc）
- 构建工具依赖：无

## 验证结果

上游测试（静态清点）：

```text
Makefile 无 test/check 目标；源码树无测试文件
上游静态声明测试数 = 0
```

消费者测试 test_package（test.c）1 个：无参契约断言（rc=0）+ 完整参数
路径（rc=0；root 特权下可观察 exec 输出，非特权按契约静默——见 MANIFEST 说明）。

## 注意事项

- chroot(2)/setuid 功能路径需要 root 特权，CI/设备测试环境为非特权用户，
  该路径无法运行（E051 chroot 平台限制类）——如实列明，消费者测试断言的是
  参数契约与真实执行（rc 语义），未伪装 chroot 功能成功。
- 许可证为 Wietse Venema 自有宽松许可（见 chrootuid_license），非 GPL。
- R38：tool 类型，commands.json 已声明 chrootuid。
---

**编译结束**: 2026-09-10 23:31
**最终状态**: built
