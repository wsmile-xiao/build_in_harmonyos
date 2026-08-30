- **三方库名称**：libxcvt
- **上游版本**：libxcvt 0.1.3（对应 `libxcvt.so.0.1.3`）
- **上游仓库地址**：https://gitlab.freedesktop.org/xorg/lib/libxcvt
- **适配路径**：路径 A（基础适配） + 知识库扩展（draft 解决一类问题）
- **使用知识库**：OHOS 下零依赖 Meson 库的通用工具链修复模式

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：libxcvt 0.1.3 release tarball；meson 工程仅编译 `libxcvt` 库与 `cvt` 工具，无 test target |
| 集成测试 | 0 | 来源：meson.build 审计；无 `test()` 声明 |
| 其他测试 | 0 | 上游仅生成库、`cvt` 可执行文件与 man 目标 |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游未提供单元测试套件 |
| 集成测试 | 0 | 不变 | 上游未提供集成测试套件 |
| 鸿蒙特有测试 | 2 | 新增 | `api_surface.c`（导出符号强类型重定位）+ `version_contract.c`（RandR 兼容 flag / ABI 类型 / 1920x1080@60 CVT 时序验证） |
| **合计** | **2** | **+2** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

libxcvt 上游是纯计算库（VESA CVT 时序生成），无任何自动化测试。适配后新增
两个不依赖图形环境的消费者测试：`libxcvt_api_surface` 对 libxcvt.so.0 唯一
导出函数 `libxcvt_gen_mode_info` 强制活重定位，确保 ABI 完整；
`libxcvt_version_contract` 校验与 RandR 对齐的 5 个 mode flag、公共结构体 ABI，
并用 `libxcvt_gen_mode_info(1920,1080,60,false,false)` 验证生成时序的字段不变量。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（N/A，已手工核验 libxcvt-0.1.3 release tarball：meson 工程仅编译 `libxcvt` 库与 `cvt` 工具，无 `test()` target、无 `test/` 目录，`meson test` 无可执行用例）
- 新增测试用例通过率：2/2（100%），`test_package` 由 GitCode CI 在 PR 上构建并执行通过（`libxcvt_api_surface` + `libxcvt_version_contract` 两个 consumer 均通过）

## 补充说明

- 本 PR 只新增 `archives/l/libxcvt/0.1.3/` 下的 Conan 配方、元数据、test_package，不修改依赖包或基础设施目录。
- 包名沿用小写 `libxcvt/0.1.3`；目录使用小写 `archives/l/libxcvt/0.1.3/`，符合 conan slug 规则。
- 上游测试用例统计已通过解包 libxcvt-0.1.3 release tarball 手工核验（meson 工程无 `test()` 声明、无 `test/` 目录），不存在少报。

## 知识库扩展

复用 OHOS 下零依赖 Meson 库的通用工具链修复模式。libxcvt 是纯计算库（VESA CVT 时序生成），无外部依赖，Meson 构建。本 PR 的知识点：零依赖 Meson 库在 OHOS 上可直接用 MesonToolchain 交叉构建，无需 PkgConfigDeps/AutotoolsDeps；`cvt` 可执行工具与库一并产出，通过 `cmake` Meson 选项控制是否构建。本 PR 是 X server / libdrm 消费者通过 libxcvt 生成 RandR mode info 的构建前置。
