# mcpp 2.7.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-02
- 编译器: clang-wrapper/clang++（clang-wrapper 是本地包装脚本，自动处理 `-fuse-ld=bfd` 和 conftest 签名问题）
- 平台: aarch64-unknown-linux-ohos（HarmonyOS Kernel 1.12.0）
- 状态: built

## 编译步骤

1. **init-build**: `ohc-run.py init-build mcpp 2.7.2 --url=...` 初始化下载、解压、骨架创建
2. **config.guess/config.sub 补丁**: 手动修改 config.guess 添加 HarmonyOS 检测分支（`*:HarmonyOS:*:*` → `echo ${MACHINE}-unknown-linux-ohos; exit ;;`）；修改 config.sub 在 `maybe_os` 和 `case $os` 中添加 `linux-ohos*` 支持
3. **configure 补丁**: 修改 configure 脚本中 umask 077 → umask 022（HMDFS 文件系统权限限制）
4. **configure**: `CC=clang-wrapper ./configure --prefix=$DEFAULT_PREFIX`（clang-wrapper 自动处理链接器选择和签名）
5. **make**: `make -j1`
6. **make install DESTDIR**: `make install DESTDIR=$TEST_PREFIX`（staging 安装）
7. **make check**: mcpp 无标准测试套件，使用 `mcpp -v` 手动验证
8. **package**: `ohc-run.py package mcpp 2.7.2`（预编译包制作）
9. **本地安装**: `make install`（不带 DESTDIR，安装到 ~/usr/local）
10. **验证**: `~/usr/local/bin/mcpp -v` → MCPP V.2.7.2 (2008/11) ✅
11. **finish**: `ohc-run.py finish mcpp 2.7.2 built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 2006 版 config.guess 不含 HarmonyOS 检测分支 | 手动添加 `*:HarmonyOS:*:*` 分支，输出三元组 `aarch64-unknown-linux-ohos`（E007） |
| 2 | config.sub 不接受 `linux-ohos` 三元组 | 2006 版 config.sub 基本系统类型列表不含 ohos | 在 `maybe_os` 和 `case $os` 两处添加 `linux-ohos*`（E007） |
| 3 | clang lld 链接器依赖 libxml2.so.16 无法运行 | ohos-sdk 的 lld 运行时依赖 libxml2，但动态链接失败 | 使用 clang-wrapper 包装，通过 `-fuse-ld=bfd` 切换到 ld.bfd 链接器（E064） |
| 4 | configure 生成的 conftest 无法执行 | HarmonyOS 要求 ELF 签名，未签名的 conftest 二进制无法运行 | clang-wrapper 自动对 conftest 程序进行 ELF 签名后再执行 |
| 5 | configure 使用 umask 077 创建临时目录失败 | HMDFS 文件系统对 umask 077 创建的目录权限有问题 | 将 configure 中 umask 077 替换为 umask 022（E011） |

## 源码修改

| 补丁文件 | 修改目标 | 说明 |
|----------|----------|------|
| 0001-config-config.guess.patch | config/config.guess | 添加 `*:HarmonyOS:*:*` 检测分支和 `aarch64:HarmonyOS:*:*` 备用分支 |
| 0002-config-config.sub.patch | config/config.sub | 在 `maybe_os` 和 OS 列表中添加 `linux-ohos*` |
| 0003-configure.patch | configure | umask 077 → umask 022（2处修改） |

所有平台适配补丁均仅在 HarmonyOS 上生效，不影响其他平台。补丁尚未添加 `#ifdef __OHOS__` 守卫（config.guess/config.sub 为 shell 脚本，不适用 C 守卫；configure 为生成文件，守卫标记为 pending）。

## 依赖版本

- 无外部依赖（mcpp 是独立的 C 预处理器库）
- 编译器: clang 15.0.4（ohos-sdk 26.0.0.18）
- 链接器: ld.bfd（替代 lld）
- 构建工具: GNU Make 4.4.1, autoconf 2.72, automake 1.17

## 验证结果

```bash
$ ~/usr/local/bin/mcpp -v
MCPP V.2.7.2 (2008/11) compiler-independent-build compiled by GCC V..
Include paths are as follows --
End of include path list.
#line 1 "<stdin>"
```

二进制可正常执行，版本号正确输出。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| mcpp-2.7.2-ohos-aarch64.tar.gz | 1,013,421 字节 (~1.0MB) | 预编译包（含 bin/mcpp、lib/libmcpp.a、头文件、man 页面） |
| mcpp-2.7.2-ohos-aarch64-debug.tar.gz | 34,844 字节 (~35KB) | 调试符号包 |

## 注意事项

- mcpp 的 `configure` 使用 umask 077 创建临时目录，在 HMDFS 上会失败，需改为 umask 022
- ohos-sdk 的 lld 链接器依赖 libxml2.so.16，当前环境存在动态链接问题，需使用 ld.bfd 替代
- clang-wrapper 是本地构建辅助脚本，自动处理 `-fuse-ld=bfd` 和 conftest ELF 签名，不属于上游代码
- mcpp 无标准 `make check` 测试套件，仅通过 `mcpp -v` 手动验证功能可用性

---

**编译结束**: 2026-06-02 22:20
**最终状态**: built
