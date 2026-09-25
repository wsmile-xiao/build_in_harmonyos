- **三方库名称**：sonivox
- **上游版本**：v3.6.16
- **上游仓库地址**：https://github.com/pedrolcl/sonivox
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无（预扫描命中 E092「CMake 无 HarmonyOS platform module」，仅作风险确认，未触发适配分支）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 33 | 来源：`test/SonivoxTest.cpp`（GoogleTest 参数化套件：3 个 TEST_P × 11 组参数，`gtest_discover_tests` 展开为 33 个 ctest 用例） |
| 集成测试 | 0 | 上游无独立集成测试 |
| 其他测试 | 0 | — |
| **合计** | **33** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 33 | 不变 | 上游套件**零修改**，真机独立构建树 33/33 通过 |
| 集成测试 | 0 | 不变 | — |
| 鸿蒙特有测试 | 19 | 新增 | `test_package/test.c`（消费者视角回归）：EAS 配置契约（版本/采样率/声道）+ 生成 SMF 离线渲染（帧数/非静音）+ 坏文件负例 + 生命周期 |
| **合计** | **52** | **+19** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 说明：上游 CMake 默认 `BUILD_TESTING=ON` 时 configure 期需联网下载 81MB DLS 音色库
> 并 FetchContent 拉取 GoogleTest；交付 conanfile 固定 `BUILD_TESTING=OFF` 保证
> `conan create` 自包含。上游测试以**独立构建树、上游源码与用例原样**在真机运行：

```
cmake -DBUILD_TESTING=ON -DCMAKE_PREFIX_PATH=<gtest-1.17.0> \
      -DBUILD_EXAMPLE=OFF && cmake --build . && ctest --output-on-failure
→ 100% tests passed out of 33（含 6 组 DLS 参数，DLS 按上游 size+MD5 校验）
```

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 上游自带 33 个 GoogleTest 用例且全部实跑通过；另按赛道要求新增软件级
> 消费者回归测试 `test_package/test.c`（19 项断言，计入上表「鸿蒙特有测试」列）。

## 验证结果

- 编译状态：通过（`conan-verify` G0-G4 全 PASS，`conan create` 成功，test_package 1/1 通过）
- 上游测试用例通过率：33/33（100%）
- 新增测试用例通过率：19/19（100%）
- 真机 CLI 验证：`sonivoxrender ants.mid` → rc=0，3,816,448 bytes PCM（非静音，峰值 32768）

## 补充说明

1. **零补丁**：上游 v3.6.16 在 OHOS SDK clang 15.0.4 下原样编译通过（静态库/共享库/CLI/测试全构建成功），`patches/` 为空；无平台宏、无源码修改。
2. **已知限制（不计问题）**：`sonivoxrender --version/--help` 上游实现返回退出码 1（`example/sonivoxrender.c` 的 `case 'v'/'h'` 分支直接 `return EXIT_FAILURE`），CI L2 smoke 判 non-blocking warn；为保持上游一致，本适配不修改该行为。
3. **命令声明（R38）**：交付包含 `bin/sonivoxrender`，软件级 `commands.json`（type=tool）已提供。
4. **依赖**：无 conan 依赖（仅 libm）；无系统同名库冲突（G3 PASS）。默认静态库
   （`shared=False`），可选 `-o sonivox*:shared=True` 出共享库。
5. **测试证据**：`reports/conan-create.log`、`reports/conan-verify-report.md`、`reports/test-report.md`。
