## PR 信息

- **三方库名称**：MathGL（静态绘图核心）
- **上游版本**：8.0.3-ds.2（Debian 源码版本为 8.0.3+ds.2）
- **上游仓库地址**：https://mathgl.sourceforge.net/；权威 Debian 发行包：https://deb.debian.org/debian/pool/main/m/mathgl/mathgl_8.0.3+ds.2.orig.tar.xz
- **适配路径**：路径 A（基础适配）+ 路径 B（知识库扩展）
- **使用知识库**：本 PR 草稿 E2181-draft-2501；`conan-source-local-archive-w3` 用于真机离线源码输入

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 1 | 原生 `mgl_example --test --mini`，检查其测试 PNG。 |
| 集成测试 | 149 | `examples/samples.cpp` 声明 150 个名字，`full_test.cpp` 的全样例循环有意跳过 `icon`；其余 149 个各渲染并验证 PNG。 |
| 其他测试 | 0 | 没有 CTest 注册用例；GUI、Python、MPI 等未打包模块的测试不计入核心库范围。 |
| **合计** | **150** | 完整原生清单见 `reports/upstream-test-inventory.txt`。 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 1 | 不变 | 保留并执行原生 `--test` 模式。 |
| 集成测试 | 149 | 不变 | 每个原生样例均输出 PNG 且逐一验证签名。 |
| 鸿蒙特有测试 | 1 | +1 | `test_package/test_mathgl.cpp` 从安装包渲染 PNG 并校验签名。 |
| **合计** | **151** | **+1** | 真机上游 150/150，安装包消费者 1/1。 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

配方构建并运行原生 `mgl_example`；上游样例源码与测试逻辑未改变。匹配 Debian 侧文件只是恢复源码缺项。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

在现有 150 个原生场景之外，新增安装包层面的 PNG 渲染消费者，覆盖公开头、静态链接和 Conan zlib/libpng 依赖传递；文件为 `test_package/conanfile.py`、`test_package/CMakeLists.txt`、`test_package/test_mathgl.cpp`、`test_package/MANIFEST.yml`。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：150/150（100%）
- 新增测试用例通过率：1/1（100%）
- HarmonyOS PC aarch64 上 `conan create` 返回 0；完整日志 SHA-256 `adf59f18d6c1fc010f9fe32e98ccf4738068a00d9c2525e4fe89e4106472e3d0`，含 `MATHGL_UPSTREAM_PASS 150/150` 和 `MATHGL_PNG_OK`。
- 冻结运行 `mathgl-w3-20260929T051636Z` 单次 launch、精确传输/回读、release/postrelease，校验返回 `W3_VALIDATOR_PASS`；链头 SHA-256 `cbc546799c92cef29240cb02e847e108b96416c5cdd03be7c691d16e9431f7cd`。
- 当前尚未声称平台 CI、合并或制品仓发布通过。

---

## 补充说明

- 关联 Issue：#3573
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：2501_91199785:feat/mathgl-8.0.3-ds.2
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：Debian `+ds.2` 原始源码故意不含 `src/s_hull`，匹配 `debian.tar` 与 `debian/rules` 提供并恢复该 GPL-3 实现。本配方逐文件校验哈希并按 GPL-3-only 标注，未将其误称为 LGPL 核心。GUI、Python、MPI 等可选模块不在本包范围；查重和复用边界见 `reports/knowledge-dedup-result.json` 与配对草稿。
