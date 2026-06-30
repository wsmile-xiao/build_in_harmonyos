# fetchmail 6.6.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-04
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. **解压源码**: `tar xf fetchmail-6.6.4.tar.xz`
2. **应用补丁**:
   - `0001-config.guess.patch`：添加 HarmonyOS 平台识别
   - `0002-config.sub.patch`：添加 `ohos-linux` 三元组支持
   - `0003-configure.patch`：修复 umask 权限问题
3. **配置**: `./configure --prefix=/storage/Users/currentUser/usr/local --with-ssl=no`
4. **编译**: `make -j1`
5. **安装**: `make install DESTDIR=/storage/Users/currentUser/test-install-fetchmail-6.6.4`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 无法识别 HarmonyOS | config.guess 缺少检测 | 修改 config.guess |
| 2 | configure 无法识别三元组 | config.sub 缺少 ohos-linux | 修改 config.sub |
| 3 | umask 权限失败 | HMDFS hmmac 限制 | sed umask 077→022 |

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| fetchmail | 663KB | 主程序二进制 |
| fetchmail-6.6.4-ohos-aarch64.tar.gz | 872KB | 预编译包 |

---
**编译结束**: 2026-06-04 10:45
**最终状态**: published