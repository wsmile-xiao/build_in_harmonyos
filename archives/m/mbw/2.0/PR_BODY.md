- **三方库名称**：mbw
- **上游版本**：mbw 2.0（Conan 版本 2.0 对应上游 mbw 2.0 内存带宽基准工具）
- **上游仓库地址**：https://github.com/raas/mbw
- **适配路径**：路径 A（基础适配）
- **使用知识库**：适配共性问题与首次真机启动避坑指南

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：mbw 2.0 release tarball；源码为单文件 mbw.c，Makefile 仅 `mbw: mbw.c`，无 TESTS 目标 |
| 集成测试 | 0 | 来源：`make check` 审计；无实质可执行上游测试 |
| 其他测试 | 0 | 上游仅生成 mbw 可执行文件与 man page |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游未提供单元测试套件 |
| 集成测试 | 0 | 不变 | 上游未提供集成测试套件 |
| 鸿蒙特有测试 | 1 | 新增 | `test_package/test_mbw.sh` 直接运行打包的 mbw 二进制，对 8 MiB 数组执行单次迭代并断言产出带宽结果 |
| **合计** | **1** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

- **补全的测试范围**：新增 1 个 Conan consumer smoke test，直接运行打包的 `bin/mbw` 二进制（`-n 1 -a 8`，8 MiB 数组单次迭代），断言退出码为 0 且输出包含 `Copy:` 带宽测量结果。
- **补全原因**：mbw 2.0 上游为基准测试工具，无自动化测试套件；本测试绑定实际构建产物，验证二进制在 OHOS 上可签名、可执行并产出测量。
- **新增测试文件清单**：
  1. `archives/m/mbw/2.0/test_package/test_mbw.sh` — mbw binary run + 带宽输出断言

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（N/A，上游未提供实质测试套件；源码无 TESTS/check_PROGRAMS）
- 新增测试用例通过率：1/1（100%），`test_package` 运行打包的 mbw 二进制通过，输出 `ok: mbw benchmark ran and produced a bandwidth result`

## 补充说明

- 本 PR 只新增 `archives/m/mbw/2.0/` 下的 mbw 配方、元数据和 test_package，不修改其他目录。
- mbw 为依赖单一文件（mbw.c）、仅用 libc 的裸 Makefile 工具，无 configure 步骤、无第三方依赖；配方以显式 clang CC 构建，`-j1` 并在 build 目录内设置 TMPDIR/TMP/TEMP，规避远端 worker 无 /tmp 的竞态。
- 工具类包（application）产物安装到 `bin/`；OHOS 运行 ELF 前由 test_package 用 binary-sign-tool 签名并用 llvm-readelf 校验 `.codesign`。
- 源码归档取自 Debian 官方源（deb.debian.org）的上游同名 tarball，sha256 已验证与上游一致；本网络 GitHub 不可达。
