- **三方库名称**：cdecode
- **上游版本**：libb64 1.2（Conan 版本 1.0.0 对应上游 libb64 1.2 base64 编解码库）
- **上游仓库地址**：https://sourceforge.net/projects/libb64/
- **适配路径**：路径 A（基础适配）
- **使用知识库**：适配共性问题与首次真机启动避坑指南

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：libb64 1.2 release tarball；src/Makefile 仅构建静态库，无 TESTS 目标 |
| 集成测试 | 0 | 来源：`make` 审计；无实质可执行上游测试 |
| 其他测试 | 0 | 上游含 base64 CLI 示例程序与 benchmark，无断言测试 |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游未提供单元测试套件 |
| 集成测试 | 0 | 不变 | 上游未提供集成测试套件 |
| 鸿蒙特有测试 | 1 | 新增 | `test_package/test.c` 链接打包的 libb64.a，对字节缓冲做 base64 流式编解码往返并断言已知向量 |
| **合计** | **1** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

- **补全的测试范围**：新增 1 个 Conan consumer smoke test，链接打包的 `libb64.a`，用 `base64_encode_block`/`base64_decode_block` 流式 API 对 `"Hello, OHOS cdecode!"` 做编解码往返，断言编码结果等于已知向量 `SGVsbG8sIE9IT1MgY2RlY29kZSE=` 且解码还原。
- **补全原因**：libb64 1.2 上游未提供测试套件；本测试绑定实际静态库产物，验证库在 OHOS 上可链接、可运行并正确实现 base64。
- **新增测试文件清单**：
  1. `archives/c/cdecode/1.0.0/test_package/test.c` — base64 roundtrip + 已知向量断言

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（N/A，上游未提供实质测试套件；src/Makefile 无 TESTS/check_PROGRAMS）
- 新增测试用例通过率：1/1（100%），`test_package` 编译链接运行通过，输出 `cdecode: base64 roundtrip ok`

## 补充说明

- 本 PR 只新增 `archives/c/cdecode/1.0.0/` 下的 cdecode 配方、元数据和 test_package，不修改其他目录。
- cdecode 为依赖单一文件（cdecode.c/cencode.c）、仅用 libc 的裸 Makefile 静态库，无 configure 步骤、无第三方依赖；配方以显式 clang CC + llvm-ar AR 构建，`-j1` 并在 build 目录内设置 TMPDIR/TMP/TEMP，规避远端 worker 无 /tmp 的竞态。
- 静态库包（library）产物 `libb64.a` 安装到 `lib/`，头文件到 `include/b64/`，`cpp_info.libs=["b64"]`；OHOS 运行 probe ELF 前由 test_package 用 binary-sign-tool 签名并用 llvm-readelf 校验 `.codesign`。
- 源码归档取自 Debian 官方源（deb.debian.org）的上游同名 tarball，sha256 已验证与上游一致；本网络 GitHub 不可达。
