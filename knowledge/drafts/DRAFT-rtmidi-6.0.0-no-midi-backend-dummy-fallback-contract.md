**DRAFT-rtmidi-6.0.0-no-midi-backend-dummy-fallback-contract — 无 MIDI 子系统平台的 rtmidi 适配：源码级 dummy 自动回退 + "空后端构建必须证明回退生效"的验证契约**

触发：OHOS PC 无 ALSA/JACK/CoreMIDI 等任何 MIDI 子系统，rtmidi 的 CMake 在此环境下静默产出空 API 列表继续构建；功能兜底发生在源码预处理层（RtMidi.cpp:88-90 自动 `#define __RTMIDI_DUMMY__`），构建日志完全不可见。修复不是补丁而是验证契约：apinames（上游断言型测试）+ 消费者 dummy 行为断言 + 完整消费者生命周期，证明"可用的 dummy 库"而非"静默 0 后端库"。真机端到端执行（EVID 见第 4 节）。

**身份与当前结论**

| 字段 | 内容 |
|---|---|
| 草稿 ID | `DRAFT-rtmidi-6.0.0-no-midi-backend-dummy-fallback-contract` |
| 配套结构化文件 | `knowledge/drafts/DRAFT-rtmidi-6.0.0-no-midi-backend-dummy-fallback-contract.kv` |
| 当前状态 | 已有验证证据待审（真机 target-executed） |
| 建议去向 | 新增模式（验证契约类） |
| 实际贡献者 | atomcode-executor |
| 来源任务/PR | ohpcd contrib-2590；PR 创建后回填 |
| 提取方式 | 新适配过程提炼 |
| 本次交付 PR | 未创建（创建后回填） |
| 包及配方版本 | rtmidi / 6.0.0 |
| 上游版本与源码 | 6.0.0 tag；https://github.com/thestk/rtmidi/archive/refs/tags/6.0.0.tar.gz；sha256 ef7bcda27fee6936b651c29ebe9544c74959d0b1583b716ce80a1c6fea7617f0 |
| 知识来源提交 | （PR 分支提交后回填） |
| 被验证提交 | （PR 分支提交后回填） |
| 最后更新 | 2026-09-20 |

**1. 触发条件与可辨认现象**

| 条件 | 实际值 | 影响 |
|---|---|---|
| 平台 | OHOS PC aarch64（无 MIDI 子系统） | CMake 探测 ALSA/JACK 全部落空 |
| 构建 | 上游 CMake ≥3.24；空 API_LIST 不报错 | 静默继续构建 |
| 回退位置 | RtMidi.cpp:88-90（预处理层） | 构建日志无后端信息 |

可辨认现象（正例，EVID-02 apinames 输出）：`API names by identifier (C++): * 7 'dummy': 'dummy'`；反例形态（未验证即申报时的风险面）：构建全绿但 `getCompiledApi` 返回空列表。
建议签名：`dummy|API names by identifier|no functionality`（dummy 构造器警告串 "provides no functionality" 由运行输出实证）。

**2. 根因与排除项**

根因：rtmidi 的后端选择分两层——CMake 层（探测库、填 API_DEFS/API_LIST）与源码层（无任何后端宏时自动 dummy）。CMake 层在无后端时**既不 fatal 也不提示**；源码层回退不可见于日志。因此"构建成功"与"dummy 生效"之间需要显式证据桥接。

| 可能原因 | 检查 | 结论 |
|---|---|---|
| CMake 需显式开 dummy 选项 | grep CMakeLists 无 RTMIDI_API_DUMMY 选项 | 已排除（上游无此开关） |
| 空后端构建会 fatal | 仅 Jack 显式请求才 FATAL_ERROR | 已排除 |

**3. 最小修复与选择条件**

无补丁。验证契约四条（复用前核对目标库是否有源码级回退；若无（如静默 0 后端的库），须补后端或如实标注能力边界）：
1. build() 运行 `tests/apinames`（真实断言：API 名称映射，exit 1 on failure）；
2. 消费者断言 dummy 契约：getCompiledApi 含 RTMIDI_DUMMY、portCount()==0、openPort 静默 no-op 且 isPortOpen()==false、sendMessage 不崩、getApiDisplayName(-1)=="Unknown"；
3. 另运行真实链接库的完整消费者生命周期：发现 dummy API、创建输入/输出会话、开关虚拟端口、投递 NoteOn/NoteOff 并关闭，证明消费者流程可完成而非仅执行断言；
4. 如实申报：dummy 是"可编译但无功能"后端，OHOS 上无真实 MIDI 能力（边界写入 notes/PR）。

**4. 验证矩阵（真机执行后回填终值）**

| 证据 ID | 类型 | 入口 | 结果 | 日志 |
|---|---|---|---|---|
| EVID-01 | target-executed | conan create（含 apinames+testcapi） | 【待回填】 | job conan-create.log |
| EVID-02 | target-executed | ./tests/apinames 输出 | 【实测】`* 5 'dummy': 'Dummy'`；修复前为空列表 | 同上 |
| EVID-03 | target-executed | 消费者 8 断言 | 【实测】通过 | 2026-09-25 真机 conan create |
| EVID-04 | target-executed | 完整消费者生命周期 | 【实测】通过（ctest 2/2） | 2026-09-25 真机 conan create |

**测试统计**：上游 apinames+testcapi 2/2；消费者 8/8 契约断言 + 1/1 完整生命周期（全部真机执行）。

**5. 边界与禁止做法**

| 可复用前提 | 已验证 | 未验证 |
|---|---|---|
| 库有源码级 no-hardware 回退 | rtmidi 6.0.0 @ OHOS | 其他音频/输入库（需个案确认回退层） |

| 错误做法 | 原因 | 后果 |
|---|---|---|
| 构建成功即申报（forbid_1） | 空后端是合法构建路径 | 下游运行期才发现全 API 不可用 |

**6. 已有知识关系**：E100（libjpeg 运行期 CPU 探测符号缺失——探测型，机制不同）、E140（CMake 平台检测缺口——检测层）。本条补"源码预处理层静默回退的验证契约"，无重复。检索 2026-09-20 未命中同类。

**7. 自检**：- [x] ID/文件/doc_file 一致；- [x] KV 单行；- [x] 证据待回填项已显式标注；- [ ] PR 编号回填。剩余动作：提交 → PR → 回填编号。
