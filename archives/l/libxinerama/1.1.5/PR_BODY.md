- **三方库名称**：libxinerama
- **上游版本**：libXinerama 1.1.5（对应 `libXinerama.so.1.0.0`）
- **上游仓库地址**：https://gitlab.freedesktop.org/xorg/lib/libxinerama
- **适配路径**：路径 A（基础适配）
- **使用知识库**：OHOS 下 X.Org autotools 库的通用工具链修复模式；头文件级依赖
  transitive_headers 消费（知识 E340）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：libXinerama 1.1.5 release tarball；源码无 `check_PROGRAMS`/`TESTS` |
| 集成测试 | 0 | 来源：`make check` 审计；无实质可执行上游测试 |
| 其他测试 | 0 | 上游仅生成库和文档/spec 目标 |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游未提供单元测试套件 |
| 集成测试 | 0 | 不变 | 上游未提供集成测试套件 |
| 鸿蒙特有测试 | 2 | 新增 | `api_surface.c`（4 个导出符号强类型重定位）+ `version_contract.c`（XineramaScreenInfo ABI 布局 / Xlib 类型），均不依赖 X server |
| **合计** | **2** | **+2** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

libXinerama 上游只发布源码与文档目标，无任何自动化测试。适配后新增两个
不依赖 X server 的消费者测试：`libxinerama_api_surface` 对
libXinerama.so.1 全部 4 个导出函数强制活重定位，确保 ABI 完整；
`libxinerama_version_contract` 校验 XineramaScreenInfo 结构体 ABI 布局
（12 字节、五个固定偏移）与 Xlib 类型可用性。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（N/A，已手工核验 libXinerama-1.1.5 release tarball：无 `test/` 目录、根 `Makefile.am` 无 `check_PROGRAMS`/`TESTS`，`make check` 无可执行用例）
- 新增测试用例通过率：2/2（100%），`test_package` 由 GitCode CI 在 PR 上构建并执行通过（`libxinerama_api_surface` + `libxinerama_version_contract` 两个 consumer 均通过）

## 补充说明

- 本 PR 只新增 `archives/l/libxinerama/1.1.5/` 下的 Conan 配方、元数据与 test_package，不修改依赖包或基础设施目录。
- 包名沿用小写 `libxinerama/1.1.5`；目录使用小写 `archives/l/libxinerama/1.1.5/`，符合 conan slug 规则。
- 上游测试用例统计已通过解包 libXinerama-1.1.5 release tarball 手工核验（无 `test/` 目录、无 `check_PROGRAMS`/`TESTS`），不存在少报。
- 配方与仓内已合入的 libxinerama/1.1.6 同构（上游 1.1.5→1.1.6 源码为同一单文件 `src/Xinerama.c`，4 个导出符号与 ABI 布局完全一致），仅版本号与源码 URL/sha256 不同。
