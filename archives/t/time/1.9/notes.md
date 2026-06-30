# time 1.9 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-21
- 编译器: clang 15.0.4 (alias gcc/cc)
- 状态: built

## 编译步骤

1. **下载源码**: 从 GNU FTP 下载 time-1.9.tar.gz
2. **初始化**: ohc-run.py init-build time 1.9
3. **修复 config.guess/config.sub**: 复制 automake-1.16 的最新版本（支持 HarmonyOS）
4. **修复 configure umask**: 修改 umask 077 为 umask 022（E011 HMDFS 权限问题）
5. **手动 configure**: 在源码目录运行 configure（避免构建目录权限问题）
6. **手动编译缺失对象**: 编译 getopt.c、getopt1.c、error.c（configure 检测 getopt 不兼容）
7. **更新 libtime.a**: 将缺失对象文件添加到静态库
8. **手动链接**: 重新链接生成 time 可执行文件
9. **手动安装**: 跳过 makeinfo 依赖，直接安装二进制文件
10. **安全验证**: time --version 成功运行

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 版本过旧（2018-03-08） | 复制 automake-1.16 最新版本（E007） |
| 2 | configure Permission denied | HMDFS umask 077 权限限制 | 修改 configure 中的 umask 077 为 022（E011） |
| 3 | config.status 创建临时文件失败 | HMDFS 权限映射问题 | 在源码目录直接运行 configure |
| 4 | 缺少 gcc/cc 编译器 | configure 默认查找 gcc | 创建 cc/gcc 符号链接到 clang |
| 5 | make jobserver FIFO 失败 | SELinux 禁止 FIFO 创建 | 使用 make -j1 单线程编译（E074） |
| 6 | 链接错误 rpl_optarg/rpl_getopt_long/error | getopt 检测为不兼容，但替换库未编译进 libtime.a | 手动编译 getopt.c、getopt1.c、error.c 并添加到静态库 |
| 7 | make install 缺少 makeinfo | texinfo 包缺失 | 手动安装二进制文件，跳过文档生成 |

## 源码修改

### build-aux/config.guess
- 替换为 automake-1.16 版本（支持 HarmonyOS）

### build-aux/config.sub
- 替换为 automake-1.16 版本（支持 HarmonyOS）

### configure
- 修改 umask 077 为 umask 022（E011 HMDFS 权限修复）

## 依赖版本

- clang 15.0.4
- GNU Make 4.4.1
- automake 1.16
- autoconf 2.72
- gawk 5.4.0
- grep 3.12
- findutils 4.9.0
- diffutils 3.10

## 验证结果

```bash
time --version
time (GNU Time) 1.9
Copyright (C) 2018 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>.
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| time | 74KB | GNU time 可执行文件 |

## 注意事项

1. **E011 HMDFS umask 问题**: 所有 autotools 项目在 HMDFS 上 configure 都会遇到此问题，必须修改 umask 077 为 022
2. **configure 检测不完整**: time 1.9 的 configure 检测 getopt 为"不兼容"，但 Makefile 没有自动编译替换库，需要手动处理
3. **手动编译流程**: 由于 HMDFS 权限和 configure 检测问题，本次编译采用大量手动操作，不适合自动化流程
4. **推荐改进**: 未来可考虑将缺失的 gnulib 对象文件编译规则添加到 Makefile，或修改 configure 检测逻辑

---

**编译结束**: 2026-05-21 15:18
**最终状态**: built（手动编译完成，未执行自动化 finish 流程）