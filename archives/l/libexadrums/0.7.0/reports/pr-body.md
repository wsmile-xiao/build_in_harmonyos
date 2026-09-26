- **三方库名称**：libexadrums（eXaDrums）
- **上游版本**：v0.7.0
- **上游仓库地址**：https://github.com/SpintroniK/libeXaDrums
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无正式测试套件（无 make check 目标） |
| 集成测试 | 0 | 上游无集成测试 |
| 其他测试 | 0 | 上游仅提供示例代码，无测试框架 |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试可对照 |
| 集成测试 | 0 | 不变 | 上游无集成测试 |
| 鸿蒙特有测试 | 4 | 新增 | test_package 对公共 API 的真实调用（GetVersion / GetDevices / AlsaParameters XML 往返 device+sampleRate），用自定义 CHECK 宏保证 Release(-DNDEBUG) 下仍真实执行 |
| **合计** | **4** | **+4** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游无测试用例，适配后补全了测试

> - **补全的测试范围**：为验证 OHOS 适配后公共 API 可用，新增 test_package（consumer 端冒烟测试），覆盖 3 个方面、共 4 条断言。
> - **补全原因**：上游库仅提供示例代码、无正式测试框架；为避免静默回归，补充对 GetVersion / ALSA 设备枚举 / AlsaParameters XML 往返的真实调用测试。
> - **新增测试文件清单**：
>   1. `test_package/test.cpp` — 4 条 CHECK 断言（非 `<cassert>`，避免 Release -DNDEBUG 剔除）
>   2. `test_package/CMakeLists.txt` — 编译/链接 test_package
>   3. `test_package/conanfile.py` — 运行期 LD_LIBRARY_PATH 注入

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（不适用，上游无测试）
- 新增测试用例通过率：4/4（100%）

## 补充说明

- OHOS 无 ALSA，内嵌静态 ALSA stub（libasound.a + 头），音频播放为 no-op；snd_pcm_open 成功、GetDevices 返回 1 个合成播放设备。
- 公共头仍 `#include <alsa/asoundlib.h>`，stub 头随包安装到 `include/alsa/` 保证下游可编译。
- 上游硬依赖 tinyxml2 / minizip，由 Conan（ohpcd）提供，通过 AutotoolsDeps 注入。
- **适配完整性说明（R40）**：本适配为**编译级适配**——库的构建、链接、公共 API 符号均可用；但音频输出后端因 OHOS 无 ALSA 而被整体桩化为 no-op（`snd_*` 空实现），真实发声功能未在 OHOS 上实现。下游若需真实音频，须提供 OHOS 音频后端替代。测试断言覆盖 API 可用性（版本 / 设备枚举 / 参数序列化），不覆盖真实音频播放。
- test_package 使用自定义 CHECK 宏（非 `<cassert>`）：OHOS CI profile 为 `build_type=Release`（`-DNDEBUG`），`assert()` 会被预处理剔除导致测试退化为恒返回 0 的空壳；CHECK 在 Debug/Release 下均编译生效，失败时打印文件行号并以非零码退出。
