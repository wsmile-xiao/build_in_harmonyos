## PR 信息
- **三方库名称**：squirrel
- **上游版本**：3.2
- **上游仓库地址**：https://github.com/albertodemichelis/squirrel
- **适配路径**：路径 A（基础适配，无补丁）、路径 B（知识库扩展）
- **使用知识库**：E550、E551；Windows ohc Conan verify shell boundary；Windows finish dual-profile execution overlay

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 官方 v3.2 CMake 未注册 CTest 测试 |
| 集成测试 | 0 | 上游未提供集成测试目标 |
| 其他测试 | 0 | 无可执行的上游测试 |
| **合计** | **0** | 上游测试盘点为 0/0（不适用） |

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 一致 | 无上游单元测试 |
| 集成测试 | 0 | 一致 | 无上游集成测试 |
| 鸿蒙特有测试 | 1 | 新增 | test_package 实际调用公共 API |
| **合计** | **1** | | 新增消费者测试 1/1 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

上游没有测试文件，本次只新增 Conan test_package，不改写上游测试。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试

新增 `test_package/consumer.cpp`，调用 `sq_open`、`sq_pushroottable`、`sq_pop` 和 `sq_close`，验证静态库链接和真实公共 API 闭包。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（不适用）
- 新增测试用例通过率：1/1（100%）

### 编译验证
- 编译器: DevEco LLVM clang (aarch64-unknown-linux-ohos)
- 编译状态: 通过
- 构建系统: CMake
- 配置选项: `DISABLE_DYNAMIC=ON; DISABLE_STATIC=OFF; fPIC=ON`

### 产物验证
| 检查项 | 状态 | 详情 |
|---|---|---|
| 编译无错误 | PASS | Conan create 和 test_package 通过 |
| 产物存在性 | PASS | squirrel、sqstdlib、sq_static 产物存在 |
| ELF 格式 | PASS | 目标消费者为 aarch64-unknown-linux-ohos |
| 运行测试 | PASS | 目标设备消费者 1/1，RC=0 |
| 动态依赖 | PASS | 无第三方依赖，默认静态闭包 |

### 适配说明
- 显式把 Conan `shared` 映射到上游实际读取的 `DISABLE_DYNAMIC`/`DISABLE_STATIC`，静态构建启用 `fPIC`。
- 修正上游静态目标名 `squirrel::interpreter_static` 到实际 `sq_static`，并登记命令行产物。
- Windows 主配方和 test_package 使用参数列表、`env=None`、`shell=False` 调用 CMake；test_package 固定 Ninja。
- OHOS 默认 profile 缺少目标编译器/sysroot 时，使用任务自有 DevEco LLVM 闭包补齐并验证版本与哈希。

### 依赖
无外部 Conan 依赖；官方 CMake 只构建 squirrel、sqstdlib 和 sq。

### 测试结论
- 总体评价: Conan 本地验证、消费者测试和目标设备 W3 均通过。
- 已知限制: 交叉构建的可执行文件不在 Windows 主机运行，只在授权 OpenHarmony PC 端点使用原生自签工具验证。

### 遇到的问题与解决方案
- 上游未注册 CTest，使用实质公共 API consumer 补齐最小测试边界。
- Windows Conan OHOS 交叉构建存在 host/build profile 和 POSIX shell 边界，采用任务自有双 profile overlay 和参数列表调用解决。

### 验证命令
```
conan create archives/s/squirrel/3.2 --version=3.2 -pr:h=ohos-host-devco.profile -pr:b=windows-build.profile
cmake --preset conan-release
cmake --build build/Release
ctest --test-dir build/Release --output-on-failure
```

---

## 补充说明

- 关联 Issue：#2623
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：feat/squirrel-3.2
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
