## PR 信息

- 三方库名称：SDL2
- 上游版本：2.32.10
- 上游仓库地址：https://github.com/libsdl-org/SDL
- 适配路径：路径 A（基础适配）+ 路径 B（贡献创新）+ 路径 C（高难度挑战候选）
- 使用知识库：openharmony-compile-agent；E2164 原生消费者与观察者终态分离

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 300 | SDL2 testautomation 的 300 个适用逻辑用例 |
| 集成测试 | 15 | 15 个独立 CTest 容器入口 |
| 其他测试 | 0 | 8 个上游禁用用例计入清单但不计入执行分母 |
| **合计** | **315** | **不可变 predecessor 实际 315/315 通过** |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 315 | 不变 | 保留上游逻辑分母与独立入口 |
| 集成测试 | 0 | 不变 | 当前目标事务不增加独立集成入口 |
| 鸿蒙特有测试 | 4 | 新增 | core、invalid、OHAudio、NativeWindow/OpenGLES2 四个生产消费者 |
| **合计** | **319** | **+4** | 新增消费者以独立程序计数，不重复上游用例 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 上游 CTest 入口和测试源保持不变；OHOS 配置只改变后端选择和链接能力。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无目标平台原生后端覆盖，适配后补全了测试

> 补全的测试范围：
> - 补全原因：上游可移植测试不覆盖 OHOS 原生 OHAudio、NativeWindow/EGL/GLES2 的真实打开、渲染和生命周期。
> - 新增测试文件清单：
>   1. `archives/s/sdl2/2.32.10/test_package/test_core.c` — 公共 API、ABI 和生命周期
>   2. `archives/s/sdl2/2.32.10/test_package/test_native_audio.c` — 非 dummy OHAudio 回调和非静默帧进展
>   3. `archives/s/sdl2/2.32.10/test_package/test_native_video.c` — NativeWindow/OpenGLES2 创建、纹理读回和 present
>   4. `archives/s/sdl2/2.32.10/test_package/test_native_video_invalid.c` — surface tuple 的 fail-closed 负例

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：315/315（100%）
- 新增测试用例通过率：4/4（100%）

详细证据：
- 交叉构建 641/641 build edges；官方归档和 16 个补丁均按 SHA-256 绑定。
- 不可变 predecessor `task4328-param4-148108-a70` 提供 315/315 上游结果；当前 r104 事务保持独立的 upstream 0/0 范围。
- r104 在 `10.62.148.108:2222` 单次事务完成 `core_pass` 17、`invalid_pass` 14、`audio_pass`（ohaudio callbacks=17, frames=16320, nonzero=32640）和 `video_pass`（nativewindow/opengles2, 2090x1324 readback），终端消费者 4/4。
- r104 的 release 与 postrelease 均通过，WAL 21 条，任务自有 root 和进程均已清零。

## 补充说明

- 关联 Issue：#2449（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2449）
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：feat/sdl2-2.32.10
- 目标分支：main
- 目标关系：SDL2 2.32.10 是 DOSBox Staging Issue #1093 的真实前置依赖。
- 当前 PR 创建前不上传制品；合并后才允许按平台流程发布到 ohpcd。
- 路径 C 仅提交候选确认，最终分值和是否采纳以平台评审为准。
