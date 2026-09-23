- **三方库名称**：libxi
- **上游版本**：libXi 1.8.3（对应 `libXi.so.6.1.0`）
- **上游仓库地址**：https://gitlab.freedesktop.org/xorg/lib/libXi
- **适配路径**：路径 A（基础适配）
- **使用知识库**：适配共性问题与首次真机启动避坑指南

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：libXi 1.8.3 release tarball；源码无 `check_PROGRAMS`/`TESTS` |
| 集成测试 | 0 | 来源：`make check` 审计；无实质可执行上游测试 |
| 其他测试 | 0 | 上游仅生成库和文档/spec 目标 |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游未提供单元测试套件 |
| 集成测试 | 0 | 不变 | 上游未提供集成测试套件 |
| 鸿蒙特有测试 | 2 | 新增 | `api_surface.c`（79 个导出符号强类型重定位）+ `version_contract.c`（XI2 事件 opcode / ABI 类型），均不依赖 X server |
| **合计** | **2** | **+2** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

- **补全的测试范围**：新增 2 个 Conan consumer smoke test，覆盖 libXi 链接与完整 ABI 面（XInput v1/v2 共 79 个符号）及协议常量/公共类型。
- **补全原因**：libXi 1.8.3 上游 release 未提供实质测试套件；本包作为 X11 输入扩展库，CI 环境无 X server，因此新增不依赖图形服务的消费者测试验证核心链接/API 可用性。
- **新增测试文件清单**：
  1. `archives/l/libxi/1.8.3/test_package/api_surface.c` — libXi consumer link + ABI surface test
  2. `archives/l/libxi/1.8.3/test_package/version_contract.c` — XI2 协议常量 + ABI 类型测试

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（N/A，上游未提供实质测试套件；源码无 `check_PROGRAMS`/`TESTS`，`make check` 无可执行用例）
- 新增测试用例通过率：2/2（100%），`test_package` 编译并通过静态验证，运行由 GitCode CI 在 PR 上执行

## 补充说明

- 本 PR 只新增 `archives/l/libxi/1.8.3/` 下的 libxi 配方、元数据和 test_package，不修改依赖包或基础设施目录。
- 包名沿用小写 `libxi/1.8.3`；目录使用小写 `archives/l/libxi/1.8.3/`，避免 REL upload 从路径推导出大小写不一致的 Conan ref。
- libXi 是 libXtst/1.2.5（平台任务 3717）的硬前置，本 PR 先于 libXtst 提交。
- 依赖图闭合（cmd-pkgs Track B）：`libx11/6.4.0`、`libxext/6.4.0`、`xorgproto/2025.1` 均已发布到 ohpcd remote（含 OHOS armv8 binary）。
- 关键决策：不引入 libxfixes/6.0.2（其 pin 在 libx11/1.8.13 Track A 且要求 libX11.la）；以 `xfixes.pc` 桩 + vendor 的 `Xfixes.h`（仅 `PointerBarrier` typedef，构建期使用，不安装）满足 configure 期需求。产物 libXi.so 不链接 libXfixes.so。
