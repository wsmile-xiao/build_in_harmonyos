- **三方库名称**：openal（OpenAL Soft，OpenAL 3D 音频 API 的软件实现）
- **上游版本**：1.24.1（发布源 https://github.com/kcat/openal-soft/archive/refs/tags/1.24.1.tar.gz ，本地实测 SHA256 e1b6ec960e00bfed3d480330274b0f102dc10e4ae0dbb70fd9db80d6978165b1）
- **上游仓库地址**：https://github.com/kcat/openal-soft
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E092（CMAKE_SYSTEM_NAME=HarmonyOS 平台识别）；本次新增知识草稿 `knowledge/drafts/openal-1.24.1-alext-prototypes-loopback.kv/.md`（alext.h 扩展函数原型守卫 + loopback 无头验证法）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 1 | 来源：tests/example.t.cpp（ExampleTest.Basic，GoogleTest，经 CMake FetchContent 拉取；ALSOFT_TESTS 默认 OFF） |
| 集成测试 | 0 | 上游无（tests/ 目录仅此 1 个文件，无 ctest 注册项） |
| 其他测试 | 0 | 上游无 |
| **合计** | **1** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 1 | 不变 | tests/example.t.cpp 去依赖移植为 test_package/upstream_basic.cpp（保留原断言体），随 conan create 真机执行 |
| 集成测试 | 0 | 不变 | 上游无 |
| 鸿蒙特有测试 | 33 | 新增 | test_package/test_openal.c：null 后端 18 断言（设备/上下文/版本字符串/缓冲区/源状态机/AL_INVALID_ENUM 负路径）+ ALC_SOFT_loopback 15 断言（8kHz mono/short 格式协商、alcRenderSamplesSOFT 实渲染 220Hz 正弦、peak=16383（0.5FS）、过零 54 次≈2×频率×时长） |
| **合计** | **34** | **+33** | 实测 34/34 全部通过 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 补充：上游 tests/example.t.cpp 原样保留在源码树中未做任何修改；因上游用 GTest
> FetchContent（交叉构建需联网拉取 gtest，不可用），故将其用例体**原样移植**为独立文件
> `test_package/upstream_basic.cpp`（新增文件，非改动上游文件）。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游无有效可执行测试，适配后补全了测试（请在下方说明）
- [ ] **否**，上游已有测试用例覆盖

> - **补全的测试范围**：为库的完整消费者工作流新增 33 个断言（设备/上下文/缓冲/源/错误路径/实渲染波形校验），并移植上游唯一 GTest 用例为可执行版本
> - **补全原因**：上游仅 1 个"只验证能编译"的 GTest 用例且依赖 FetchContent 联网拉 gtest，交叉构建环境不可执行；OHOS 无音频设备，需要无头验证路径
> - **新增测试文件清单**：
>   1. `test_package/test_openal.c` — 端到端消费者：null 后端 + ALC_SOFT_loopback 实渲染断言（33 断言）
>   2. `test_package/upstream_basic.cpp` — 上游 tests/example.t.cpp 的去依赖移植版（1 断言）

## 验证结果

- 编译状态：通过（conan create，profile ohos-aarch64：os=OHOS/armv8/clang 15/libc++/cppstd=17，产物 libopenal.a）
- 上游测试用例通过率：1/1（100%）
- 新增测试用例通过率：33/33（100%）

## 补充说明

- **零补丁**：1.24.1 全项目 C++17（对比仓内 openal/1.25.2 为 C++20、在 OHOS libc++15 上需 9 个兼容补丁），clang 15/libc++ 15 直接满足，patches/ 为空。
- **OHOS 取舍**：静态库（LIBTYPE=STATIC，OHOS 无系统 libopenal，避免 SONAME/同名冲突）；外部音频后端全部关闭（ALSA/PipeWire/PulseAudio/JACK/OSS/Solaris/SNDIO/PortAudio/SDL2/Oboe/OpenSL/CoreAudio/Wave），仅保留上游无条件编译的 Null + loopback，无音频设备即可完成全部功能验证；不内嵌 HRTF 数据集（与仓内 1.25.2 口径一致）；NEON 开启。
- **本地验证链**：conan create + test_package 真机执行 34/34 通过；conan-verify G0–G4 全 PASS（reports/conan-verify-report.md）；finish W3 本地 CI 模拟通过（.ci-result.json 由工具写入）；W4 审计 pass（P0=0 P1=0，2 条 P3 建议，reports/audit-result.json）。
- **包名说明**：本仓对同一上游存在两个历史目录——`archives/o/openal/`（2026-08-03 【积分赛】1.25.2，本 PR 沿用此包名）与 `archives/o/openal-soft/`（1.24.3 旧档 + 1.25.2 知识库扩展）。本 PR 只新增 `archives/o/openal/1.24.1/`，不触碰其他目录；如评审要求统一命名可后续迁移。
- **已知限制**：无真实音频设备验证（设备相关后端在 OHOS 无对应系统服务）；HRTF 数据集未内嵌，HRTF 相关空间化功能需消费方自行提供数据文件。
- 构建日志（reports/conan-create.log、w3-local-ci.log）按仓库规范仅留存工作区不入库，验证结论以本描述与 CI 结果为准。
