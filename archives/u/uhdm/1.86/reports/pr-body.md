## 三方库信息

- **三方库名称**：uhdm（UHDM — Universal Hardware Data Model，C++17 VPI 硬件数据模型库 + CLI 工具集）
- **上游版本**：v1.86
- **上游仓库地址**：https://github.com/chipsalliance/UHDM
- **适配路径**：路径 B（贡献创新 — 知识库扩展）
- **使用知识库**：openharmony-compile-agent（知识图谱命中：E092 CMake 未知平台、E002 /tmp 只读、E544-E3AD TMPDIR 口径、E543-66FA 族参考、E524/R49 依赖注入私有 prefix 口径）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 43 | gtest：tests/*.cpp 17 个套件（CMake `register_tests()` 显式枚举），ctest 注册 43 用例 |
| 集成测试 | 0 | 上游无集成测试 |
| 其他测试 | 0 | - |
| **合计** | **43** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 43 | 不变 | OHOS aarch64 实测 43/43 全绿（串行）；-j4 并发 7 条瞬时失败（共享 TMPDIR 竞态），串行复跑为口径 |
| 集成测试 | 0 | 不变 | - |
| 鸿蒙特有测试 | 2 | 新增 | test_package Conan L1 消费测试：VPI API 读写回环断言 + uhdm-dump CLI 冒烟（目标平台执行） |
| **合计** | **45** | **+2** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

> 43 个 gtest 用例在上游源码树中逐字执行（探索期 UHDM_BUILD_TESTS=ON 构建 17 个测试二进制），无 API 签名差异、无平台行为修改。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖

> 说明：上游已有完整 gtest 测试体系（43 用例）。test_package 新增的 2 项为 Conan L1 包消费级测试（验证安装头/库/CLI 可被下游正确使用），不属于对上游测试缺口的补全；上游 googletest 套件不进入制品（UHDM_BUILD_TESTS=OFF），由 CI 与探索期双口径留证覆盖。

## 验证结果

- 编译状态：通过（conan create 全绿 + W3 本地 CI 模拟 1/1 100%，.ci-result.json exit_code=0）
- 上游测试用例通过率：43/43（100%，OHOS aarch64 串行实测）
- 新增测试用例通过率：2/2（100%，test_package 于 conan create 内执行通过）

## 补充说明

1. **路径 B 申报内容**：知识图谱草稿 3 条（E429 家族，draft 状态，待主编审核提升）：
   - `E429-draft-DAB2`：CMake 未知平台（HarmonyOS）不产出 SONAME → shared 库 DT_NEEDED 内嵌相对构建路径 → 运行时 loader relocation 失败；对策=默认静态 + shared 时显式 `-Wl,-soname`（CMAKE_SONAME cache 变量在未知平台实测不生效）
   - `E429-draft-E718`：上游 third_party 子模块（capnproto/googletest）以 host 选项 + 制品仓 tool_requires 替代，工具可执行路径须消费方显式注入（tc.cache_variables）
   - `E429-draft-DCA9`：pip 构建期代码生成依赖 `--no-deps --target` 钉版进 build_folder 私有 prefix（R49/E524 范式）
2. **关键适配决策**：capnproto/1.3.0 双声明（tool_requires 供 capnpc/capnpc-c++ 代码生成 + requires 供链接期/公共头，protobuf/protoc 标准模式）；默认静态构建（上游 CMake 默认 + 平台 SONAME 缺口下的运行时健壮选择）；上游 PUBLIC 编译选项 `-include uhdm/config.h` 经 cmake_build_modules 构建模块携带；**上游源码零修改**（patches/ 为空）。
3. **测试执行环境**：OHOS aarch64 目标机原生执行（本机即目标平台）；-j4 并发首轮 7 条瞬时失败为共享 TMPDIR 竞态瞬态环境问题，非产品缺陷（串行 43/43 + 失败样本单独直跑全绿，双口径证据见 notes.md）。
4. **已知限制**：本地 L2/L4/L5 门禁因 conan cache 路径定位工具限制跳过，由 CI 干净环境复验；上游 gtest 套件不进制品（与 CI 只读 4 文件口径一致）。
5. **后续动作**：按任务约定 CI 与 AI 检视由维护者手动触发（PR 评论 `/rebuild`），随后 `submit uhdm 1.86 --resume` 续环闭环（R42）。
