- **三方库名称**：libxext
- **上游版本**：libXext 1.3.6（Conan 版本 6.4.0 对应 `libXext.so.6.4.0` ABI）
- **上游仓库地址**：https://gitlab.freedesktop.org/xorg/lib/libXext
- **适配路径**：路径 A（基础适配）
- **使用知识库**：适配共性问题与首次真机启动避坑指南

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：libXext 1.3.6 release tarball；源码无 `check_PROGRAMS`/`TESTS` |
| 集成测试 | 0 | 来源：`make check` 审计；无实质可执行上游测试 |
| 其他测试 | 0 | 上游仅生成库和文档/spec 目标 |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游未提供单元测试套件 |
| 集成测试 | 0 | 不变 | 上游未提供集成测试套件 |
| 鸿蒙特有测试 | 1 | 新增 | `test_package/test.c` 链接 libXext 并调用核心本地 API，不依赖 X server |
| **合计** | **1** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

- **补全的测试范围**：新增 1 个 Conan consumer smoke test，覆盖 libXext 链接与 `XextCreateExtension()`、`XextFindDisplay()`、`XSetExtensionErrorHandler()`、`XMissingExtension()` 等本地 API。
- **补全原因**：libXext 1.3.6 上游 release 未提供实质测试套件；本包作为 X11 扩展库，CI 环境无 X server，因此新增不依赖图形服务的消费者测试验证核心链接/API 可用性。
- **新增测试文件清单**：
  1. `archives/l/libxext/6.4.0/test_package/test.c` — libXext consumer link + API smoke test

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（N/A，上游未提供实质测试套件；源码无 `check_PROGRAMS`/`TESTS`，`make check` 无可执行用例）
- 新增测试用例通过率：1/1（100%），`test_package` 编译并运行通过，输出 `libxext api smoke ok`

## 补充说明

- 本 PR 只新增 `archives/l/libxext/6.4.0/` 下的 libxext 配方、元数据和 test_package，不修改 libx11、libxscrnsaver 或基础设施目录。
- 包名沿用历史消费者依赖的小写 `libxext/6.4.0`；目录同步使用小写 `archives/l/libxext/6.4.0/`，避免 REL upload 从路径推导出大小写不一致的 Conan ref；源码使用 upstream `libXext 1.3.6`，对应产物 `libXext.so.6.4.0`。
- W0 依赖检查确认 `libx11/6.4.0` 已发布并可解析，`xorgproto/2025.1` 已发布。
- OHOS 单包 CI 已通过：`CI_PACKAGES="archives/l/libxext/6.4.0" zsh ci/conan/build_and_test.sh`，`Build Summary` 为 Total 1 / Success 1 / Failed 0。
- 原适配验证日志：`/storage/Users/currentUser/libxext-6.4.0-ci-20260809-140503.log`；2026-08-10 已用小写路径复跑通过。
- 远端构建环境中 `/data/service/hnp/bin` 下的 shell/compiler 路径不可用，配方和 test_package 均在本包内回落到实际可用的 `$HOME/usr/local/bin` LLVM 工具与 `/system/bin/sh`，不修改共享 profile。
- 远端无 `pkg-config` 可执行文件，配方通过 Conan 依赖目录生成 `XEXT_CFLAGS` 与 `XEXT_LIBS`。
