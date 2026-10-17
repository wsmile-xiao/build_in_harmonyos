# vmime 0.9.2 适配笔记

## 适配环境

- **平台**: HarmonyOS PC (aarch64-linux-ohos)
- **SDK**: HarmonyOS SDK 26 (clang 15.0.4, libc++17)
- **构建系统**: CMake
- **Conan**: 2.29.1 (OHOS 适配版)

## 依赖处理

- **OpenSSL**: 使用 1.1.1w（TLS 支持）
- **libiconv**: 使用 1.17.1（OHOS sysroot 无 iconv.h）
- **cppunit**: 1.15.1（test_requires，仅构建期，测试套件依赖）
- **SASL**: 关闭（gsasl 未发布到制品仓）

## 编译修复

1. **std::bind2nd 移除**: C++17 已移除 `std::bind2nd`，替换为 lambda 表达式
2. **BIO_METHOD 不透明**: OpenSSL 1.1.0+ 的 BIO 已不透明，需使用 `BIO_meth_*` API；
   懒加载经 C++11 magic static 实现线程安全（先完整填充再发布，避免并发观察到部分初始化的 BIO_METHOD），并对 `BIO_meth_new` 失败显式抛异常
3. **pthread 回退**: OHOS 平台 pthread 在 libc 中，需回退到 `c` 库
4. **strerror_r 兼容性**: GNU 和 POSIX 的 `strerror_r` 返回类型不同，需显式转换
5. **静态库测试导出头**: 仅构建静态库时 upstream 不生成 export-shared.hpp，需复制 export-static.hpp 供测试目标编译
6. **测试目标链接**: 上游测试硬编码链接 `vmime` 目标，纯静态构建不存在该目标，改为 `vmime-static`

## 测试结果

- **上游测试**: 453 个 CppUnit 测试用例（58 个测试可执行文件），100% 通过
- **测试执行方式**: `VMIME_BUILD_TESTS=ON` 在 conanfile 的 build() 阶段通过 ctest 真实执行；
  测试失败会使构建失败（重跑仅用于补全失败明细，随后原样上抛，禁止测试全红仍产出包）
- **/tmp 只读适配**: fileContentHandlerTest 与 maildirStoreTest 原硬编码 `/tmp` 临时目录，
  OHOS 设备 `/tmp` 只读导致失败；已打补丁改为从 `TMPDIR` 环境变量取临时目录（build() 中
  指向构建目录下的可写目录），453/453 全部通过
- **test_package**: 消费者冒烟测试通过（构造 MIME 报文→序列化→重解析并逐字段断言）

## 新增测试

- **test_consumer/**: 消费者端到端用例（C1 构造消息+附件→序列化→写文件；C2 从文件重解析核查头部；C3 提取附件逐字节校验），使用 conan install 解析已发布包后以公开 API 编译运行
- **test_ohos/**: 鸿蒙专项验证（T1 aarch64 ELF；T2 无宿主路径泄漏；T3 TMPDIR 兼容；T4 iconv 链接；T5 无 std::bind2nd 残留），5/5 通过

## 注意事项

- 静态库构建时，OpenSSL 和 libiconv 通过 INTERFACE_LINK_LIBRARIES 传递
- 测试目标依赖 vmime-static 而非 vmime
- 使用 libc++17 标准库