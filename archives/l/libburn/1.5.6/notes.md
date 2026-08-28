# libburn 1.5.6 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-01
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. `init-build libburn 1.5.6 --url=https://files.libburnia-project.org/releases/libburn-1.5.6.tar.gz` (SSL下载失败，手动下载后使用 --no-download)
2. 替换 config.guess 和 config.sub（从已适配的 vifm 项目复制支持 HarmonyOS 的版本）
3. 移除 configure 中 umask 077（HMDFS 不支持 chmod，umask 077 创建的目录无法写入）
4. 运行 `./configure --prefix=/storage/Users/currentUser/usr/local` → 成功
5. `make -j2` → 编译成功
6. `make install DESTDIR=/storage/Users/currentUser/tmp/test-install-libburn-1.5.6` → staging 安装成功
7. `verify-build` → PASS (G1-G4)
8. `package` → 打包完成 (libburn-1.5.6-ohos-aarch64.tar.gz: 2.2MB)
9. `make install` (无 DESTDIR) → 本地安装成功
10. 验证: `cdrskin --version` → 1.5.6

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 旧版 config.guess (2014) 不包含 HarmonyOS 支持 | 从已适配的 vifm 项目复制含 ohos 支持的 config.guess/config.sub |
| 2 | configure 中 umask 077 导致 Permission denied | HMDFS 文件系统不支持 chmod (E046)，umask 077 创建的临时目录无法写入 | 新增 0004-configure-umask.patch 移除 umask 077 |
| 3 | SSL 下载失败 | 系统缺少 libburnia-project.org 的 SSL CA 证书 | 手动 curl -skL 下载 tarball |

## 源码修改

- config.guess: 替换为支持 HarmonyOS 的版本（从 vifm-0.14.3 复制）
- config.sub: 替换为支持 ohos 三元组的版本（从 vifm-0.14.3 复制）
- configure: 移除 umask 077（两处），解决 HMDFS 权限限制 (E046)

## 补丁说明（4个补丁）

| 补丁 | 类型 | 说明 |
|------|------|------|
| 0001-version.h.patch | 平台适配 | 添加版本宏定义 |
| 0002-config.guess.patch | 平台适配 | 支持 HarmonyOS 平台检测 |
| 0003-config.sub.patch | 平台适配 | 支持 ohos 三元组 |
| 0004-configure-umask.patch | 平台适配 | 移除 umask 077，解决 HMDFS 权限限制 (E046) |

> 旧补丁 0004-cdrskin-cdrskin.patch 和 0005-doc-doxygen.conf.patch 已移除：
> - 0004 是 libtool 生成的 wrapper 脚本（非源码修改，R6）
> - 0005 是 doxygen 文档配置（对功能无影响）

## 预编译包优化

| 优化项 | 原始 | 优化后 | 说明 |
|--------|------|--------|------|
| 主包体积 | 3.1MB | 2.2MB | 完整 strip + 移除 libburn.la |
| ELF strip | not stripped | stripped | llvm-strip --strip-all + .gnu_debuglink |
| RUNPATH | 硬编码路径 | $ORIGIN | 预编译包可移植部署 |
| 包内容 | 含 libburn.la、空目录 | 精简 | 移除 .la 文件和空 external 目录 |

## 依赖版本

- clang 15.0.4
- GNU Make 4.4.1
- autoconf 2.72
- automake 1.16.5
- libtool 2.4.7
- pkg-config 0.29.2
- GNU sed (预编译包)

## 验证结果

```bash
$ cdrskin --version
cdrskin 1.5.6 : limited cdrecord compatibility wrapper for libburn
libburn interface : 1.5.6
libburn in use : 1.5.6

$ PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig pkg-config --modversion libburn-1
1.5.6
```

## 功能测试结果 (2026-06-01)

| 测试项 | 结果 | 说明 |
|--------|------|------|
| burn_version() | ✅ | 返回 1.5.6 |
| burn_abort() | ✅ | 无崩溃 |
| 枚举值定义 | ✅ | BURN_DISC_*, BURN_WRITE_* 正常 |
| cdrskin --version | ✅ | 输出正确 |
| cdrskin --devices | ✅ | 无设备时优雅处理 |
| pkg-config | ✅ | modversion/libs/cflags 正确 |
| 符号导出 | ✅ | 205 个 burn_* API |
| ELF 签名 | ✅ | .note.ohos.ident 存在 |
| 预编译包 RPATH | ✅ | $ORIGIN 可移植路径 |

详见 `reports/functional-test-report.md`

## G0 干净构建验证 (2026-06-01)

✅ PASS: 4个补丁 + configure --prefix 即可从原始 tarball 完成完整的干净构建（configure → make → make install），无需任何人工介入。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libburn-1.5.6-ohos-aarch64.tar.gz | 2.2MB | 预编译包（已 stripped） |
| libburn-1.5.6-ohos-aarch64-debug.tar.gz | 864KB | 调试符号包 |

## 注意事项

- HMDFS 文件系统不支持 chmod (E046)，configure 中 umask 077 需要移除（已通过 0004 补丁固化）
- 无物理光驱环境下 API 调用正常（设备扫描返回 0 设备，不崩溃）**改进完成**: 2026-06-01 14:59
---

**编译结束**: 2026-08-28 16:13
**最终状态**: built
