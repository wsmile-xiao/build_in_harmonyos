# softhsm 2.6.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-20
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化构建环境：
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build softhsm 2.6.1 --url=file://$HOME/tmp/softhsm-2.6.1.tar.gz
   source .build-context-softhsm-2.6.1
   cd $BUILD_SRC_DIR
   ```

2. 安装依赖（预编译包）：
   ```bash
   curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- openssl 1.1.1w
   curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- sqlite3 3.49.1
   ```

3. 修复平台检测：
   ```bash
   # config.guess: 返回 aarch64-unknown-linux-gnu
   echo '#!/bin/sh
   echo aarch64-unknown-linux-gnu' > config.guess

   # config.sub: 直接返回输入参数
   echo '#!/bin/sh
   echo "$1"' > config.sub

   # configure umask: 077 → 022
   sed -i 's/umask 077/umask 022/g' configure
   ```

4. 配置编译：
   ```bash
   export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
   export CC=clang CXX=clang++
   ./configure --prefix=$DEFAULT_PREFIX --with-openssl=$HOME/usr/local --with-sqlite3=$HOME/usr/local
   ```

5. 编译安装：
   ```bash
   make -j1
   make install DESTDIR=$TEST_PREFIX
   ```

6. 验证与打包：
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py verify-build softhsm 2.6.1
   python3 $SKILL_ROOT/scripts/ohc-run.py package softhsm 2.6.1
   ```

7. 本地安装验证：
   ```bash
   make install  # 安装到 ~/usr/local
   ~/usr/local/bin/softhsm2-util --version  # 输出: 2.6.1
   ~/usr/local/bin/softhsm2-keyconv --version  # 输出: 2.6.1
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 脚本版本旧，不识别新系统 | 修改为直接返回 aarch64-unknown-linux-gnu |
| 2 | configure 报 "no acceptable C compiler" | CC/CXX 未设置 | 设置 export CC=clang CXX=clang++ |
| 3 | configure 报 umask permission issue | umask 077 导致目录权限问题 | sed 替换为 umask 022 |
| 4 | pkg-config 找不到 openssl/sqlite3 | PKG_CONFIG_PATH 未设置 | 设置 PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig |

## 源码修改

无正式补丁文件。平台检测修改为 inline 修改（记录于此）：
- config.guess: 简化为 echo aarch64-unknown-linux-gnu
- config.sub: 简化为 echo "$1"
- configure: umask 077 → 022

## 依赖版本

| 软件 | 版本 | 来源 |
|------|------|------|
| openssl | 1.1.1w | cmd-pkgs 预编译包 |
| sqlite3 | 3.49.1 | cmd-pkgs 预编译包 |

## 验证结果

```bash
$ ~/usr/local/bin/softhsm2-util --version
2.6.1

$ ~/usr/local/bin/softhsm2-keyconv --version
2.6.1
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| softhsm-2.6.1-ohos-aarch64.tar.gz | 13.8MB | 预编译包 |

## 注意事项

1. SoftHSM2 需要 libcrypto（OpenSSL）和 sqlite3 作为依赖
2. 平台检测文件（config.guess/config.sub）需要针对 HarmonyOS/aarch64 修改
3. 生成的库文件在 lib/softhsm/ 目录下（PKCS#11 模块）
4. configure 会检测 ECC/EDDSA/GOST 支持（取决于 OpenSSL 版本）

---
**编译结束**: 2026-05-20 15:52
**最终状态**: built（预编译包已制作，待发布）
---

**编译结束**: 2026-05-20 15:54
**最终状态**: built
