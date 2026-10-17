# ngtcp2 1.22.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-07
- 编译器: clang/clang++
- 状态: published (conan-verify PASS)

## 编译步骤

```bash
# 1. 应用补丁
#    0001: config.guess 添加 HarmonyOS 检测
#    0002: configure umask 077→022 (HMDFS 权限修复)

# 2. 配置 (conan create 内部执行)
./configure --prefix=$PREFIX --enable-lib-only --with-openssl

# 3. 编译
make -j1

# 4. 安装
make install

# 5. 测试
make check  # PASS: 1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config.guess 不包含 HarmonyOS 检测逻辑 | 添加 HarmonyOS 检测补丁 (patch 0001) |
| 2 | HMDFS umask 权限问题 (E011) | HMDFS 文件系统的 UID 映射机制导致 umask 077 创建的临时目录无法写入 | 修改 configure 中 umask 077 为 umask 022 (patch 0002) |
| 3 | conan create 中 OpenSSL 未找到 | AutotoolsDeps 生成器未设置 PKG_CONFIG_PATH | 在 generate() 中手动设置 PKG_CONFIG_PATH |

## 依赖版本
- openssl/3.5.6.1.1 (Conan 制品仓)

## 验证结果

```bash
make check: PASS (1/1)
conan-verify: PASS (G0-G4 all passed)
```

## 补丁文件
1. 0001-config.guess.patch - 添加 HarmonyOS 系统检测到 config.guess
2. 0002-configure.patch - 修复 HMDFS umask 权限问题

## 结束

COMPLETED - ngtcp2 1.22.1 适配完成，所有质量门禁通过。
