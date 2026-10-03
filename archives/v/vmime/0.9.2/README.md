# vmime 0.9.2

## 概述

vmime 是一个开源的 C++ 邮件库，支持 MIME、SMTP、POP3、IMAP 等协议。本版本已适配到 HarmonyOS PC（aarch64-linux-ohos）平台。

## 版本信息

- **上游版本**: 0.9.2
- **适配版本**: 0.9.2
- **平台**: HarmonyOS PC (aarch64-linux-ohos)
- **Conan 引用**: vmime/0.9.2（Conan 2，无 channel 语法）

## 依赖

- **OpenSSL**: 1.1.1w（TLS 支持）
- **libiconv**: 1.17.1（字符集转换）
- **cppunit**: 1.15.1（test_requires，仅供编译上游测试套件）

## 编译选项

- `shared`: 是否构建共享库（默认 False）
- `fPIC`: 是否启用位置无关代码（默认 True）
- `with_tls`: 是否启用 TLS 支持（默认 True）
- `with_sasl`: 是否启用 SASL 支持（默认 False，需要 gsasl）

## 使用示例

```python
# conanfile.py
requires = "vmime/0.9.2"
```

## 补丁说明

本版本包含 8 个补丁：

1. **0001-CMakeLists.txt.patch**: 仅构建静态库时生成 export-shared.hpp，修复测试目标依赖并链接 vmime-static，为 OpenSSL/iconv 添加 INTERFACE_LINK_LIBRARIES
2. **0002-src-vmime-encoding.cpp.patch**: 将 `std::bind2nd` 替换为 lambda 表达式以兼容 C++17
3. **0003-src-vmime-net-tls-openssl-TLSSocket_OpenSSL.cpp.patch**: 将静态 BIO_METHOD 初始化转换为 BIO_meth_* API 以兼容 OpenSSL 1.1.0+ 的不透明 BIO；懒加载经 C++11 magic static 实现线程安全（先完整填充再发布），并对 BIO_meth_new 失败显式抛异常
4. **0004-src-vmime-net-tls-openssl-TLSSocket_OpenSSL.hpp.patch**: 声明静态 sm_customBIOMethod 指针和 ensureCustomBIOMethod() 辅助函数
5. **0005-src-vmime-platforms-posix-posixHandler.cpp.patch**: 将 G_mutex 移动到全局作用域，并为 getLocalCharset 添加 VMIME_HAVE_PTHREAD 保护
6. **0006-src-vmime-platforms-posix-posixSocket.cpp.patch**: 修复 strerror_r 的 GNU/POSIX 兼容性问题
7. **0007-tests-net-maildir-maildirStoreTest.cpp.patch**: 上游测试 maildirStoreTest 硬编码 /tmp 临时目录，OHOS 上 /tmp 只读，改为读环境变量 TMPDIR
8. **0008-tests-parser-fileContentHandlerTest.cpp.patch**: 上游测试 fileContentHandlerTest 硬编码 /tmp 临时目录，同上改为读 TMPDIR

## 测试

- **上游测试**: cppunit 驱动的 453 个 CppUnit 测试用例（58 个测试可执行文件），在 conanfile build() 中使用 ctest 真实执行，100% 通过
- **test_package/**: 消费者冒烟测试，构造 MIME 报文→序列化→重解析并逐字段断言
- **test_consumer/**: 端到端消费者用例，conan install 解析已发布包后以公开 API 编译运行（构造附件→写文件→重解析→附件逐字节校验）
- **test_ohos/**: 鸿蒙专项验证（aarch64 ELF/宿主路径泄漏/TMPDIR 兼容/iconv 链接/no bind2nd），5/5 通过
