# libxcrypt

## 简介

libxcrypt 是一个现代的扩展 crypt 库，支持多种密码哈希算法，包括传统的 DES crypt、MD5 crypt、Blowfish crypt（bcrypt）以及 SHA256/SHA512 crypt。它是 GNU libc crypt 功能的现代替代实现，设计为可独立安装和链接。

## 主要功能

- **多种哈希算法支持**：descrypt、md5crypt、bcrypt、sha256crypt、sha512crypt
- **API 兼容性**：提供与传统 crypt() 函数兼容的接口
- **线程安全**：提供 crypt_r() 等可重入函数
- **盐值生成**：提供 crypt_gensalt() 系列函数用于生成安全的盐值
- **可扩展性**：支持添加新的哈希算法模块

## OHOS 适配

### 已知问题与解决方案

1. **HMDFS 权限限制**：
   - **问题**：autotools 的 configure 脚本在 HMDFS 文件系统上无法创建临时文件（umask 077）
   - **解决方案**：修改 configure 中的 `umask 077` 为 `umask 022`（见补丁 0003-configure.patch）

2. **平台识别**：
   - **问题**：config.guess/config.sub 无法识别 HarmonyOS 平台
   - **解决方案**：添加 HarmonyOS 平台识别和三元组支持（见补丁 0001、0002）

3. **编译器警告**：
   - **问题**：clang 对 GNU inline asm 扩展发出警告（lib/util-xbzero.c）
   - **解决方案**：添加 `-Wno-language-extension-token` 编译标志

### 与 Linux 的差异

- HMDFS 文件系统对临时文件创建有严格限制（SELinux 策略）
- 需要显式设置 umask 才能正常编译
- clang 编译器对 GNU 扩展的警告更严格

### 配套知识草稿

- `knowledge/drafts/E232-draft-2301.{kv,md}`：仅在存在同名 `.libs` ELF 时通过 shell 启动无扩展名 Libtool wrapper。
- `knowledge/drafts/E233-draft-2301.{kv,md}`：目标 libc 缺 API 时，独立测试须链接库内准确的 fallback 对象。
- 两组草稿随 libxcrypt 4.5.2 软件 PR 提交，不修改正式 `knowledge/graph/index.tsv`；适配路径保持 A+B。

## 依赖关系

### 编译依赖
- 无外部依赖（可独立编译）

### 运行依赖
- 无外部依赖（静态链接时）
- 动态链接时需要 libc

## 参考资料

- **官方仓库**：https://github.com/besser82/libxcrypt
- **发布页面**：https://github.com/besser82/libxcrypt/releases
- **文档**：https://github.com/besser82/libxcrypt/blob/master/README.md
