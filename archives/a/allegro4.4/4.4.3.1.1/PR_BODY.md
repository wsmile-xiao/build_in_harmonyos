## PR 信息

- 三方库名称：allegro4.4
- 上游版本：4.4.3.1（适配版本 4.4.3.1.1）
- 上游仓库地址：https://github.com/liballeg/allegro5
- 适配路径：路径 A（基础适配） / 路径 B（贡献创新）
- 使用知识库：openharmony-compile-agent；E2177 设备签名与目标执行边界；E2178 已发布版本的 successor identity 边界

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 官方 4.4.3.1 源码无可执行 CTest 用例 |
| 集成测试 | 0 | 官方构建未注册集成测试 |
| 其他测试 | 0 | 无 |
| **合计** | **0** | inventory 记录为 0 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试入口 |
| 集成测试 | 0 | 不变 | 上游无集成测试入口 |
| 鸿蒙特有测试 | 1 | 新增 | `test_package/core_contract.c` 调用 `allegro_init`、`allegro_exit` 验证目标链接与运行 |
| **合计** | **1** | **+1** | 宿主、目标构建和真机均执行 consumer |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试

- 补全的测试范围：新增 1 个最小 consumer contract
- 补全原因：上游源码没有可执行测试入口，需要验证 Conan target、头文件、库链接和初始化/退出 API
- 新增测试文件清单：
  1. `archives/a/allegro4.4/4.4.3.1.1/test_package/core_contract.c` — 调用 Allegro 核心 API

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（不适用）
- 新增测试用例通过率：1/1（100%）

## 补充说明

- 宿主最终 `conan create` 通过，consumer 输出 `allegro_core_contract PASS`。
- 目标 arm64 CMake configure/build/install 和 consumer build 通过。
- 真机 r4 使用 endpoint 真实 signer 完成执行验证，输出 `allegro_core_contract PASS`，RC=0；r1-r3 的 RC=126 已分别冻结，不与 r4 拼接。
- 源码使用官方 release URL，SHA-256 为 `ec19dbc9a021244582b4819b3583ee594b50141f9fcf6944a4ed8069cbf8d4d4`。
- 关联 Issue：#2566（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2566）
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：feat/allegro4.4-4.4.3.1.1
- 目标分支：main
