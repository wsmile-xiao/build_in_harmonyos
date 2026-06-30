# sqlcipher 4.16.0 编译笔记

## 编译信息
- 软件名称: sqlcipher
- 版本: 4.16.0
- 构建系统: autosetup
- 开始时间: 2026-05-20 16:50
- 结束时间: 2026-05-20 16:58

## 依赖处理
- **第一次尝试**: OpenSSL 1.1.1w（不兼容）
- **问题发现**: sqlcipher 4.16.0 移除了对 OpenSSL < 3.0 的支持
- **解决方案**: 安装 OpenSSL 3.5.6 预编译包
- OpenSSL 3.5.6 已安装到 ~/usr/local
- PKG_CONFIG_PATH 已设置

## 编译步骤

### Step 1: 平台适配
- 问题: autosetup-config.guess 无法识别 HarmonyOS
- 解决: 添加 HarmonyOS 识别逻辑，映射到 linux-gnu

### Step 2: Configure
- 参数: `--prefix=/storage/Users/currentUser/usr/local --with-tempstore=yes`
- CFLAGS: `-DSQLITE_HAS_CODEC -DSQLITE_EXTRA_INIT=sqlcipher_extra_init -DSQLITE_EXTRA_SHUTDOWN=sqlcipher_extra_shutdown -I/storage/Users/currentUser/usr/local/include`
- LDFLAGS: `-L/storage/Users/currentUser/usr/local/lib -lcrypto -lssl`
- 结果: 成功生成Makefile

### Step 3: Make
- 命令: `make -j2`
- 结果: 成功生成 sqlite3, libsqlite3.a, libsqlite3.so

### Step 4: Staging安装
- DESTDIR模式（R20铁律）
- TEST_PREFIX: ~/tmp/test-install-sqlcipher-4.16.0
- 手动安装（因为没有install命令）

### Step 5: 用户验证
- 安装到 DEFAULT_PREFIX（~/usr/local）
- 验证: sqlite3 --version 成功
- 加密功能测试: 成功

### Step 6: 打包
- 产物: sqlcipher-4.16.0-ohos-aarch64.tar.gz（6.0MB）
- 位置: archives/s/sqlcipher/4.16.0/packaging/

## 遇到的问题

### 问题1: OpenSSL版本不兼容
- **现象**: 编译失败，找不到 EVP_MAC_fetch, OSSL_PARAM 等符号
- **原因**: OpenSSL 1.1.1w 缺少 OpenSSL 3.x 的 API
- **解决**: 安装 OpenSSL 3.5.6 预编译包

### 问题2: HarmonyOS平台识别
- **现象**: configure 失败，无法识别系统类型
- **原因**: autosetup-config.guess 没有 HarmonyOS 支持
- **解决**: 修改 config.guess/config.sub 添加 HarmonyOS 识别

### 问题3: 缺少install命令
- **现象**: make install 失败
- **原因**: configure 时未找到 install binary
- **解决**: 手动安装文件

## 提取的知识点

### L1 平台真理（已写入knowledge/graph/draft/）
- **E105-draft-autosetup-config.kv**: autosetup构建系统平台适配
  - autosetup-config.guess/config.sub需要修改以支持HarmonyOS
  - 与E007（autotools-config）的区别：autosetup使用不同的文件名和位置
- HarmonyOS平台需要修改autosetup-config.guess/config.sub（已通过补丁固化）
- autosetup构建系统需要与GNU config不同的处理

### L2 模式经验
- SQLCipher 4.16.0+ 需要OpenSSL 3.x
- autosetup构建系统的configure参数传递方式
- 加密库编译的CFLAGS定义模式

### L3 本版笔记（已写入manifest.yaml）
- 具体的configure参数
- 依赖版本信息
- 遇到的具体问题及解决方案

## 编译总结
- 最终状态: built（编译成功，功能可用）
- 产物完整: sqlite3（可执行）、libsqlite3.a（静态库）、libsqlite3.so（动态库）
- 加密功能: 已验证可用
- 质量评估: 编译质量良好，建议发布为published状态
**下一步建议**: 提交到cmd-pkgs仓库，标记为published
---

**编译结束**: 2026-05-20 16:59
**最终状态**: built
