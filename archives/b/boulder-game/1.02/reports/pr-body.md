- **三方库名称**：boulder-game
- **上游版本**：1.02（程序标题 v1.02，固定提交 7bdb085f6da06c0f201ed20c957ae47ac92eae51）
- **上游仓库地址**：https://github.com/rh-galaxy/boulder
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）
- **使用知识库**：build_in_harmonyos SKILL.md、E088/E073/E474/E489、SDL2 nativewindow 适配记录；新增 DRAFT-boulder-hap-cxx-runtime

本次适配使原有 Boulder 游戏及地图编辑器通过 ArkUI XComponent 在 OpenHarmony PC 上运行。复用上游 C++ 游戏、渲染、音频、地图读写逻辑，补充窗口宿主、输入转发、可写目录和 Conan 打包；修复 HAP 私有命名空间缺少 C++ 运行库的问题。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 固定上游源码无测试套件 |
| 集成测试 | 0 | 桌面 Makefile 无 check/test 目标 |
| 其他测试 | 0 | vendored SDL_test 头文件不是 Boulder 测试 |
| **合计** | **0** | 不把新增回归测试算作上游测试 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | |
| 集成测试 | 3 | +3 | CTest：assets、map-roundtrip、missing-assets |
| 鸿蒙特有测试 | 1 | 新增 | Conan test_package 在 OHOS 真机执行安装产物功能回归及 HAP 模块/运行库完整性检查 |
| **合计** | **4** | **+4** | 按命名测试入口计数；人工 GUI 测试不混入统计 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例。
- [ ] **是**。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**。
- [x] **是**，上游无自动测试套件，补充适配回归测试。

- **补全范围**：14 图片、25 地图、18 WAV 音效、1 Vorbis 音乐解码；地图保存重载检查尺寸、参数、描述、钻石、钥匙参数和边界；缺资源负例；安装产物检查。
- **补全原因**：原游戏只提供桌面构建目标，缺少可供移植验证的自动测试入口。
- **新增测试文件清单**：
  1. 补丁新增 `harmony/check.cpp` 与根 `CMakeLists.txt`：3 项 CTest。
  2. `archives/b/boulder-game/1.02/test_package/test.sh`、`conanfile.py`、`MANIFEST.yml`：真机消费者测试。

## 验证结果

- 编译状态：Conan 干净构建及 DevEco 签名 HAP 构建通过。
- 上游测试用例通过率：不适用（0 项，无上游套件）。
- 新增测试用例通过率：4/4（100%）。
- 真机成品复验：菜单、Enter 进入关卡、Right 移动、游戏/首页/编辑器往返通过，保存的地图可读取。
- 前期人工验证还覆盖绘制、S 保存、L 重载、重启持久化、F3 笔刷；用户确认背景音乐可听见。
- 详细证据见 `1.02/reports/test-report.md`；官方 W3 与独立审计报告随归档提交。

## 补充说明

画布固定 1024×768，编辑器入口为 newlevel.map，没有外部目录选择器及滚轮转发。Conan 包提供可配置个人签名的 ArkUI 工程，不包含证书或密码。命令行 boulder-check 为资源/地图测试工具，图形游戏由 HAP 启动。

Conan 验证器的 package ID 解析未成功，L2/L4/L5 自动步骤被跳过，不将其当作已执行测试；消费者功能测试和实际 HAP 运行已独立验证。


## 路径 B 知识贡献说明

- **草稿**：`knowledge/drafts/DRAFT-boulder-hap-cxx-runtime.kv/.md`，主题为 Conan 预编译 C++ 模块进入 HAP 后的 SDK 运行库装载契约。
- **真实触发**：Conan 构建和消费者测试通过，实际 HAP 原生调用却报 `libc++_shared.so` 在 `ndk/moduleNs_default` namespace 中不可见；修复后最终 HAP 菜单、关卡、移动和编辑器往返通过。
- **增量**：明确作为 E088 的 HAP 打包场景扩展候选，不宣称首次发现 namespace。补充实际编译器定位匹配 SDK 运行库、目标 ABI 私有打包和 NOTICE、Conan 到 HAP 的产物来源核查及真机运行步骤。它解决同类预编译 C++ 模块的应用打包问题，不是只改游戏逻辑的补丁。
- **查重**：核对 origin/main `7bc9ccf891aafe69f98abf323f0adc1f1fc271d1` 的知识正文/草稿，并对比 E088、E073、E474、E489 与 Curtain 宿主草稿；差异和边界见知识 Markdown。官方 draft-review 建议 `create`，最高相似 E088=0.29；此建议不替代委员会复审，可由维护者决定并入 E088。
- **证据**：`reports/hap-runtime-evidence.md`、`reports/hap-artifact-evidence.json`、`reports/knowledge-draft-review.json`。
- **范围**：实证为 Boulder 游戏/编辑器、aarch64、SDK 26.0.0.18；没有宣称第二项目、所有 SDK 或通用 ELF 自动依赖解析器已验证。
- **申请**：按【知识库扩展】申报 A+B，最终 B 定级及计分以委员会复审为准。
