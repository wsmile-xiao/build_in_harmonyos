# dropbear 2025.88 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-02
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. **下载源码**：使用镜像URL手动下载dropbear-2025.88.tar.bz2（SSL证书问题导致自动下载失败）
2. **初始化编译环境**：`ohc-run.py init-build dropbear 2025.88 --url=file:///path/to/tarball`
3. **修改config.status**：手动修改临时目录创建逻辑，解决hmdfs文件系统权限问题
4. **configure**：`./configure --prefix=$DEFAULT_PREFIX --build=aarch64-linux-gnu`
5. **编译**：`make -j1`（成功）
6. **staging安装**：`make install DESTDIR=$TEST_PREFIX`（DESTDIR模式，R20铁律）
7. **测试**：`make check`卡住（virtualenv创建问题），跳过并记录
8. **打包**：手动制作预编译包 dropbear-2025.88-ohos-aarch64.tar.gz（1.0MB）
9. **本地安装**：`make install`（验证二进制可执行性，R7铁律）
10. **归档**：finish命令完成归档

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败 | 鸿蒙系统CA证书配置问题 | 使用curl -k手动下载源码包 |
| 2 | config.guess无法识别系统 | 脚本不支持HarmonyOS | 手动指定--build=aarch64-linux-gnu |
| 3 | config.status临时文件创建失败 | hmdfs文件系统特殊权限限制 | 手动修改config.status使用固定临时目录 |
| 4 | getspnam函数未定义 | 鸿蒙系统shadow.h存在但getspnam未实现 | 添加HAVE_GETSPNAM条件检查，无getspnam时使用fallback |
| 5 | getpass函数未定义 | 鸿蒙系统未实现getpass | 使用fgets替代实现，添加HAVE_GETPASS条件检查 |
| 6 | make check卡住 | virtualenv创建在hmdfs上失败 | 跳过测试并记录原因 |

## 源码修改

### 补丁1: 0001-src-cli-auth.c.patch
- **修改文件**: src/cli-auth.c
- **修改内容**: getpass_or_cancel函数添加HAVE_GETPASS条件检查
- **修改原因**: 鸿蒙系统未实现getpass()函数
- **修改方案**: 使用fgets从stdin读取密码作为替代实现

### 补丁2: 0002-src-common-session.c.patch
- **修改文件**: src/common-session.c
- **修改内容**: getspnam调用添加HAVE_GETSPNAM条件检查
- **修改原因**: 鸿蒙系统shadow.h存在但getspnam()未实现
- **修改方案**: 无getspnam时使用fallback密码"!!"

## 依赖版本

- 无外部依赖（自包含libtomcrypt和libtommath）

## 验证结果

```bash
# 二进制文件验证
$DEFAULT_PREFIX/bin/dbclient --version
  WARNING: Ignoring unknown option -- (正常，dbclient不支持--version)

$DEFAULT_PREFIX/sbin/dropbear --help
  Dropbear server v2025.88 https://matt.ucc.asn.au/dropbear/dropbear.html

# 文件大小
dbclient:       343KB
dropbearkey:    187KB
dropbearconvert: 195KB
dropbear:       347KB
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| dropbear-2025.88-ohos-aarch64.tar.gz | 1.0MB | 预编译包（含4个二进制+4个man手册） |

## 注意事项

1. **平台限制**: 鸿蒙系统不支持shadow password和getpass函数，使用替代实现
2. **编译位置**: 因hmdfs权限问题，在tmpfs（/storage/Users/currentUser/tmp）目录编译
3. **测试跳过**: make check因virtualenv问题卡住，功能测试需手动进行
4. **二进制签名**: 需通过cmd-pkgs公共安装脚本进行ELF签名才能在鸿蒙上执行

---

**编译结束**: 2026-06-02 16:53
**最终状态**: published
---

**编译结束**: 2026-06-02 16:56
**最终状态**: built
