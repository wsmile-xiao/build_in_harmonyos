# iperf 2.2.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-26 (conan 适配)
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 SourceForge 下载源码 tarball
2. 应用 config.guess/config.sub 补丁（OHOS 平台识别）
3. 修改 headers.h（解决 linux/socket.h 与 sys/socket.h 冲突）
4. 修改 checksums.c（适配 musl udphdr 结构体）
5. configure --prefix=$DEFAULT_PREFIX
6. make -j2
7. make install DESTDIR=$TEST_PREFIX
8. make install（安装到本地）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 补丁缺少 exit 语句 | 添加 echo "$GUESS" && exit ;; |
| 2 | config.sub 报错 "Kernel 'linux' not known to work with OS 'ohos'" | linux-ohos 组合未添加到验证列表 | 添加 linux-ohos* 到 kernel-os 验证 |
| 3 | sockaddr_storage 重复定义 | linux/tcp.h 包含 linux/socket.h 与 sys/socket.h 冲突 | 使用宏别名 #define sockaddr_storage sockaddr_storage_ohos_alias |
| 4 | udphdr.check 成员不存在 | musl libc 使用 uh_sum 命名 | 添加 #ifdef __OHOS__ 条件编译 |
| 5 | config.status "Permission denied" 创建 subs1.awk | mktemp -d with umask 077 在 HarmonyOS 上创建的目录无法写入 (HMDFS/SELinux 限制) | conanfile.py build() 中 patch config.status 使用 mkdir 代替 mktemp |
| 6 | CI 报 "checking whether the C++ compiler works... no / C++ compiler cannot create executables"（PR #4399，2026-08-27 两台 worker #31972/#31982 均失败，本地同命令通过） | CI worker 沙箱（buildbot AppSpawn）中 TMPDIR 指向受限目录时，clang 把中间目标文件写到 $TMPDIR 失败（bas55 2.0 记录的同款 CI 故障模式；iperf 2.x 以 C++ 为主，configure 先做 C++ 检查所以最先暴露） | conanfile.py build() 显式将 TMPDIR 接管为 conan 构建目录（必然可写）；另在 configure 失败时 dump config.log 关键段（失败的编译命令+报错）到 conan 输出，CI 失败评论可直接定位根因 |

## 验证结果

```bash
$ iperf --version
iperf version 2.2.1 (4 Nov 2024) pthreads
```

## 上游测试 (make check)

所有 16 个测试失败，原因是测试脚本使用 `#!/bin/bash` shebang，而 HarmonyOS 上 bash 位于 `/data/service/hnp/bin/bash`，`/bin/bash` 不存在。这是平台限制，不影响 iperf 功能。

## Conan 适配

- package_type: application
- 构建系统: Autotools (configure + make)
- 无外部依赖
- test_package: 运行 `iperf --version` 验证二进制可用

---

**编译结束**: 2026-08-26
**CI 修复**: 2026-09-17 — TMPDIR 沙箱加固 + config.log 失败诊断（问题 #6）；移除 configure 不支持的 --enable-static/--disable-shared（消除 unrecognized options 告警）；license 由 MIT 更正为 NCSA（上游 COPYING 为伊利诺伊大学/NCSA 许可）。本地三重复验通过：CI 环境模拟（env -i 最小 PATH/CI TMPDIR）、敌意 TMPDIR（/nonexistent 下构建仍过）、坏 CXX 诊断输出验证。
**最终状态**: built (conan 适配完成)
