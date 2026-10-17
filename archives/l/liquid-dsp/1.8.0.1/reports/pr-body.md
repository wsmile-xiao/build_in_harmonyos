建议 PR 标题：`【知识库扩展】liquid-dsp 1.8.0.1：固化 CMake static-only 包导出身份一致性`

- **三方库名称**：liquid-dsp
- **上游版本**：v1.8.0（适配修订版本 1.8.0.1）
- **上游仓库地址**：https://github.com/jgaeddert/liquid-dsp
- **适配路径**：路径 B（知识库扩展；同时包含基础适配产物）
- **使用知识库**：新增 `E327-draft-D220`；E216/E278 仅用于相邻问题去重

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 1341 | 来源：上游 `xautotest` 聚合测试目标 |
| 集成测试 | 0 | 上游未单独分类 |
| 其他测试 | 0 | 无 |
| **合计** | **1341** | 另含 716520 个上游断言 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 1341 | 不变 | 未裁剪、未修改上游测试 |
| 集成测试 | 0 | 不变 | 上游未单独分类 |
| Conan/CMake 包消费检查 | 3 | 新增 | `test_package` 的 API/版本/窗口消费者检查 |
| **合计** | **1344** | **+3** | 包消费检查不宣称为上游测试创新 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

补丁只修复 CMake 安装导出名称；配方启用原有 `BUILD_AUTOTESTS` 并调用 CTest。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

新增的 3 个 `test_package` 检查用于 Conan/CMake 包消费合同，不作为“上游无测试补全”申报。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：1341/1341（100%），716520/716520 checks
- 新增测试用例通过率：3/3（100%）

## 补充说明

- Issue：#2206；分支：`fix/liquid-dsp-1.8.0.1-2206`；一库一 issue、一分支、一 PR。
- W0：无必需外部依赖；可选 FFTW 已关闭并使用内置 FFT，不混入依赖适配。
- Shadow CI：`xuguowei-liquid-dsp-liquid-dsp-issue-2206-shadow-r8r2-d1b4882a00-20260816-001734-29564`；被测提交 `d1b4882a00e3`；归档 SHA256 `426dfb52d71c2df908895998605bb6afcc38c5902218f81f831ac030935a35ef`；外层/内部 exit 0，stderr 0 字节，Total 1 / Success 1 / Failed 0；L0/L1/L5 pass，L2 skip（库包无 bin），L4 为补丁文本扫描 warning。
- B 类对照：`xuguowei-liquid-dsp-issue-2206-path-b-evidence-r3-20260815-225009-42915`，同源修复前后对照 exit 0；修复前 canonical `find_package` 失败，修复后消费者编译、链接、运行通过。
- B 类 draft：`knowledge/drafts/E327-draft-D220.{kv,md}`；证据：`archives/l/liquid-dsp/1.8.0.1/reports/knowledge-expansion-evidence.md`。
- 诚实边界：1.8.0 历史报告已有 liquid-dsp 专属修复；本次新增贡献是可复用知识抽象、正式 before/after 证据和相邻条目去重。
- 安装产物：`include/liquid/liquid.h`、`lib/libliquid.a`、`lib/cmake/liquid/`、`lib/pkgconfig/liquid-dsp.pc`。
- 已知告警：CMake HarmonyOS platform module、`/proc/meminfo` 和 make jobserver FIFO 信息不阻塞构建；未将其列为本知识条目根因。
