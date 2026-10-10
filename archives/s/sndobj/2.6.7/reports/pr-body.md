## PR 信息

- **三方库名称**：sndobj
- **上游版本**：2.6.7
- **上游仓库地址**：https://sourceforge.net/projects/sndobj/files/SndObj%20Library%20Sources/SndObj-2.6.7/
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）
- **使用知识库**：新增 `knowledge/drafts/E999-draft-SD67.{kv,md}`，记录非 Windows GUID signedness 的可复用诊断与最小修复；最终编号由主编确认。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
| --- | ---: | --- |
| 单元测试 | 0 | `SConstruct` 无注册的自动测试目标。 |
| 集成测试 | 0 | 无非交互式自动集成测试。 |
| 其他测试 | 0 | `src/examples/test.cpp` 与 `python/test.py` 是实时音频硬件示例，不属于此 `NO_RTIO` 核心包的自动用例。 |
| **合计** | **0** | 0/0 不写成 100%。 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
| --- | ---: | --- | --- |
| 单元测试 | 0 | 不变 | 未修改上游测试。 |
| 集成测试 | 0 | 不变 | 未修改上游测试。 |
| 鸿蒙特有测试 | 3 | 新增 +3 | 安装后 `HarmTable`/`Oscili` 消费者验证表、处理和输出。 |
| **合计** | **3** | **+3** | 目标机 3/3 条件通过。 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

上游 `src/examples/test.cpp` 和 `python/test.py` 均保留原样。源码补丁只修正非 Windows GUID 兼容字段。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无注册的非交互式测试，适配后补全了测试

- **补全的测试范围**：已安装的可移植核心，`HarmTable` 初始化、`Oscili::DoProcess()` 以及有限且非零的音频样本。
- **补全原因**：上游仅提供依赖实时音频设备的示例，不能证明 `NO_RTIO` 制品被外部消费者正常链接与运行。
- **新增测试文件清单**：`archives/s/sndobj/2.6.7/test_package/consumer.cpp`、`CMakeLists.txt`、`conanfile.py` 和 `MANIFEST.yml`。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（不适用）
- 新增测试用例通过率：3/3（100%）
- 真机证据：`sndobj-w3-20261003T174232Z`，鸿蒙 PC arm64 `conan create` RC 0，12/12 回执 `W3_PASS`；目标日志 SHA-256 `bd48ebace8e9646f99baf3e7f4d3716090a409cd047992d8ec00b42c314f85d9`。
- 测试详情：`archives/s/sndobj/2.6.7/reports/test-report.md`。

## 补充说明

- **关联 Issue**：[#3730](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3730)
- **队伍名称**：诶，云朵
- **申请人显示标识**：2501_91199785
- **源分支**：feat/sndobj-2.6.7
- **目标分支**：main
- **已知限制**：配方显式启用 `NO_RTIO`，只交付可移植核心及上游捆绑 FFTW 2；实时音频设备后端、Python/Java 封装和硬件示例未验证。
- **当前 CI**：按用户要求暂缓；真机结果不等同于比赛 worker 的 PR CI。
- **发布边界**：仅在合并后由维护者执行 `/release` 发布到 ohpcd。
