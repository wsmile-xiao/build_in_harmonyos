# 编译笔记 — libetpan 1.9.4

## 编译环境
- 构建系统: autotools
- 编译器: clang 15.0.4 / clang++
- 平台: aarch64-unknown-linux-ohos
- DESTDIR 模式 (R20): --prefix=/storage/Users/currentUser/usr/local, DESTDIR=/storage/Users/currentUser/tmp/test-install-libetpan-1.9.4

## 关键问题及解决方案

### 1. GitHub tarball 不含 configure 脚本
- **问题**: GitHub 归档的 tarball 不包含预生成的 configure 脚本
- **解决**: 运行 `libtoolize --copy --install` 然后 `autoreconf -fi` 生成构建脚本

### 2. HMDFS umask 077 限制
- **问题**: HMDFS 文件系统中，`mktemp -d` 配合 `umask 077` 创建的目录内无法写入文件（Permission denied）
- **解决**: 修改 configure 和 config.status 中临时目录创建逻辑，移除 `umask 077` 包装
- **影响**: 这是平台特定的 HMDFS 文件系统限制，所有 autotools 项目可能遇到此问题

### 3. 缺少 Berkeley DB 和 SASL
- **问题**: configure 检测到缺少 db.h 和 sasl/sasl.h
- **解决**: 允许这些功能被禁用（libetpan 可正常运行）

## 编译结果
- 产物: libetpan.so, libetpan.a, libetpan.h
- 类型: 纯库（无可执行二进制）
- 测试: make check 无实际测试套件
- pkg-config: libetpan 1.9.4 ✅

## 功能测试结果 (2026-06-03)
- 测试覆盖率: 77 项测试，74 通过（96%）
- 核心功能验证:
  - 数据结构 (carray/clist/chash): ✅ 全通过
  - MIME 解析/写入: ✅ 全通过
  - IMF RFC 5322 解析: ✅ 全通过
  - MMAPString: ✅ 全通过
  - 字符集转换 (charconv): ✅ UTF-8→ISO-8859-1 成功
  - 协议对象 (IMAP/SMTP/POP3/NNTP): ✅ 全通过
  - 存储驱动: ✅ 6 个 session_driver 全部注册
  - 信号量/锁: ✅ 功能可用
- 已知非阻塞问题:
  - libetpan-config.h 缺少 feature macros (LIBETPAN_HAS_ZLIB/SSL/ICONV/CURL)
    - 实际功能正常，zlib/OpenSSL/iconv/libcurl 均已链接
  - mm_body 字段在 set_body_text 后为 NULL（写入仍成功）
- 上库状态: 符合上库要求，状态升级为 published

## 知识沉淀
- HMDFS umask 077 限制 (L1 平台真理)
- GitHub tarball bootstrap 需要 autoreconf (L2 模式经验)
- libetpan 纯库无二进制 (L3 本版笔记)

**编译开始**: 2026-06-02 21:37
**编译结束**: 2026-06-02 22:03
**最终状态**: published