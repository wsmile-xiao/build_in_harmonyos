## PR 信息
- **三方库名称**：Cassiopee
- **上游版本**：1.0.9
- **上游仓库地址**：https://github.com/osallou/cassiopee-c（源码归档端点：https://codeload.github.com/osallou/cassiopee-c/tar.gz/1.0.9?filename=cassiopee-1.0.9.tar.gz）
- **适配路径**：路径 B（贡献创新）
- **使用知识库**：openharmony-compile-agent；E017、E540

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 13 | 上游 CppUnit，`test/test.h` / `test/test.cxx` |
| 集成测试 | 0 | 上游未提供独立消费者集成测试 |
| 其他测试 | 0 | 无 |
| **合计** | **13** | 13 个 CppUnit 方法由 CTest 执行 |

上游测试方法完整清单：`testIndex`、`testIndexWithReduction`、`testSearchInReduction`、`testAmbiguity`、`testSearchWithError`、`testSearchAfterN`、`testSearchWithN`、`testReducedSearchAfterN`、`testReducedSearchWithN`、`testProtein`、`testLoadSave`、`testMultiIndex`、`testSearchWithMorphism`。

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 13 | 不变 | 上游 CppUnit 测试全部保留并执行，13/13 通过 |
| 集成测试 | 1 | 新增 | Conan test package 消费者测试，真实链接并调用 Cassiopee API |
| 鸿蒙特有测试 | 0 | 无新增 | W3 HarmonyOS 交叉编译和运行验证覆盖平台构建 |
| **合计** | **14** | **+1** | |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

未修改 `test/test.h`、`test/test.cxx`、测试注册项或断言。补丁仅修改构建和安装逻辑：使用 Conan CMake targets，移除 `/usr/local/lib`，禁用可选 OpenMP，构建静态 `cassie` 库，并安装库及 `Cassiopee.h`。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无独立消费者测试，适配后补全了测试

- **补全的测试范围**：新增 1 个消费者集成测试，验证 Conan 安装包能够被下游通过 `cassiopee::cassiopee` 发现、编译、链接和运行，并调用 `CassieIndexer` / `CassieSearch`。
- **补全原因**：上游测试直接在源码构建树中运行，未覆盖已安装 Conan 包的消费者边界。
- **新增测试文件清单**：
  1. `test_package/consumer.cpp` — 调用 Cassiopee 公开 API 并校验搜索结果。
  2. `test_package/CMakeLists.txt` — 仅链接 `cassiopee::cassiopee`。
  3. `test_package/sequence.txt` — 消费者测试输入。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：13/13（100%）
- 新增测试用例通过率：1/1（100%）
- Conan 验证：G1、G2、G3、G4、L2、L4、L5 全部通过
- W3 本地 CI 模拟：通过
- W4 独立审计：通过，P0=0、P1=0

### 验证命令和结果
```text
python3 .../ohc-run.py conan-verify cassiopee 1.0.9
结果：G1/G2/G3/G4/L2/L4/L5 全部通过

python3 .../ohc-run.py finish cassiopee 1.0.9 built
结果：W3 本地 CI 模拟通过；setup.sh 通过；build_and_test.sh 通过

python3 .../ohc-run.py verify-build cassiopee 1.0.9
结果：质量报告 PASS，G1/G2/G3/G4 全部通过

独立 W4 审计
结果：PASS，P0=0，P1=0
```

## 补充说明

- 版本级及软件级状态为 `built`，表示本地配方验证和 W3 已通过，尚未完成制品仓上传。
- 上游原始下载站点不可用，配方使用官方 GitHub tag archive，并记录 SHA256。
- 上游动态库布局会产生 HarmonyOS 加载器无法解析的相对 `DT_NEEDED`；适配采用静态 `cassie` 库。
- 直接依赖为 `boost/1.90.0.4`、`glog/0.7.1`；`cppunit/1.15.1` 仅用于上游测试构建。
