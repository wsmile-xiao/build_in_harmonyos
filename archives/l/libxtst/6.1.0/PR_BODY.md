- **三方库名称**：libxtst
- **上游版本**：libXtst 1.2.4（Conan 版本 6.1.0 对应 `libXtst.so.6.1.0` ABI）
- **上游仓库地址**：https://gitlab.freedesktop.org/xorg/lib/libXtst
- **适配路径**：路径 A（基础适配）
- **使用知识库**：适配共性问题与首次真机启动避坑指南

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：libXtst 1.2.4 release tarball；源码无 `check_PROGRAMS`/`TESTS` |
| 集成测试 | 0 | 来源：`make check` 审计；无实质可执行上游测试 |
| 其他测试 | 0 | 上游仅生成库和文档/spec 目标 |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游未提供单元测试套件 |
| 集成测试 | 0 | 不变 | 上游未提供集成测试套件 |
| 鸿蒙特有测试 | 1 | 新增 | `test_package/test.c` 链接 libXtst 并调用核心本地 API，不依赖 X server |
| **合计** | **1** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

- **补全的测试范围**：新增 1 个 Conan consumer smoke test，覆盖 libXtst 链接与 `XTestQueryExtension()` API 调用（函数指针签名与真实声明一致——5 参数）。
- **补全原因**：libXtst 1.2.4 上游 release 未提供实质测试套件；本包作为 X11 测试扩展库，CI 环境无 X server，因此新增不依赖图形服务的消费者测试验证核心链接/API 可用性。
- **新增测试文件清单**：
  1. `archives/l/libxtst/6.1.0/test_package/test.c` — libXtst consumer link + API smoke test

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（N/A，上游未提供实质测试套件；源码无 `check_PROGRAMS`/`TESTS`，`make check` 无可执行用例）
- 新增测试用例通过率：1/1（100%），`test_package` 编译并运行通过，输出 `libxtst symbol OK`（鸿蒙无 X server 时回退符号验证）

## 补充说明

- 本 PR 只新增 `archives/l/libxtst/6.1.0/` 下的 libxtst 配方、元数据和 test_package，不修改 libxi、libxfixes 或基础设施目录。
- 包名沿用历史消费者依赖的小写 `libxtst/6.1.0`；目录同步使用小写 `archives/l/libxtst/6.1.0/`；源码使用 upstream `libXtst 1.2.4`，对应产物 `libXtst.so.6.1.0`。
- W0 依赖检查确认 `libx11/6.4.0`、`libxext/6.4.0`、`libxi/6.1.0`、`libxfixes/6.1.0`、`xorgproto/2025.1` 已发布或同链处理。
- 源码换源 `xorg.freedesktop.org/archive/...`（releases 路径 CI 连接超时，与 libxi/libxfixes main 先例一致），sha256 一致。
- 配方包含完整 libXau.la 修复逻辑（占位 .la 生成 + libdir 修正 + 旧路径符号链接——与 libxi/libxfixes 已验证方案一致）。
