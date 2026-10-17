- **三方库名称**：lerc（liblerc）
- **上游版本**：lerc 4.2.0（对应 `libLerc.so.4`）
- **上游仓库地址**：https://github.com/Esri/lerc
- **适配路径**：路径 A（基础适配）
- **使用知识库**：OHOS 下 CMake C++ 共享库通用适配模式（glfw/libjpeg-turbo/zstd 同法）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 1 | `src/LercTest/main.cpp` — LercTest 编解码自测程序（直接驱动 Lerc C API 的 encode/decode/getBlobInfo/computeCompressedSize 全链路） |
| 集成测试 | 0 | 来源：`CMakeLists.txt` 审计；无集成测试目标 |
| 其他测试 | 3 | `OtherLanguages/js/tests/` — 3 个 JS 测试（`sanity.mjs` / `level2.mjs` / `sanity-umd.cjs`），针对上游 wasm 构建产物 `dist/LercDecode.es.js` |
| **合计** | **4** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 1 | 不变（复跑） | 上游 `src/LercTest/main.cpp` 原样接入 `test_package`（`lerc_upstream_test`），链接已安装的 libLerc.so 实跑 |
| 集成测试 | 0 | 不变 | 上游未提供集成测试套件 |
| 鸿蒙特有测试 | 2 | 新增 | `api_surface.c`（12 个导出 C 函数强类型重定位）+ `version_contract.c`（版本宏 / lerc_status 类型契约），均无需输入数据 |
| **合计** | **3** | **+2** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

lerc 上游源码树含测试程序但未纳入 CTest（`CMakeLists.txt` 无
`enable_testing`/`add_test`）：`src/LercTest/main.cpp`（C++ 编解码自测，
需链接 libLerc）+ `OtherLanguages/js/tests/` 3 个 JS 测试（针对上游 wasm
构建产物 `dist/LercDecode.es.js`，需 node + emscripten 构建，与 C++ 库无关）。

适配后：
1. **上游 C++ 测试原样实跑**：`src/LercTest/main.cpp` 未做任何修改，按上游
   相对 include 结构（`upstream_test/LercLib/include/`）vendored 进
   `test_package`，链接**已安装的 libLerc.so.4**，由 GitCode CI 在 OHOS
   aarch64 worker 上编译并执行（`lerc_upstream_test`，返回 0 = 通过）。
2. **新增消费者测试**：`lerc_api_surface` 对 libLerc.so.4 全部 12 个导出 C
   函数（lerc_computeCompressedSize/lerc_encode/…/_4D 系列）强制活重定位，
   确保 ABI 完整；`lerc_version_contract` 校验版本宏
   （LERC_VERSION_MAJOR=4 / MINOR=2 / PATCH=0 / LERC_VERSION_NUMBER=40200 /
   LERC_AT_LEAST_VERSION 判定）与 `lerc_status`==`unsigned int` 的类型契约。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：**1/4**（`lerc_upstream_test` = LercTest 1/1 实跑通过；其余 3 个 JS 测试 **N/A**——针对上游 wasm 构建产物 `dist/LercDecode.es.js`，需 node ≥14 + emscripten 构建链路，CI 构建环境无 node/wasm 工具链，且与 C++ 库 libLerc 无运行路径关联；逐条说明见补充说明）
- 新增测试用例通过率：2/2（100%），`test_package` 由 GitCode CI 在 PR 上构建并执行通过（`lerc_api_surface` + `lerc_version_contract` 两个 consumer 均通过）

## 补充说明

- 本 PR 只新增 `archives/l/lerc/4.2.0/` 下的 Conan 配方、元数据、test_package，不修改依赖包或基础设施目录。
- 包名沿用小写 `lerc/4.2.0`；目录使用小写 `archives/l/lerc/4.2.0/`，符合 conan slug 规则。
- **上游测试统计修正**：此前声明 N=0 少报。经解包 lerc v4.2.0 release tarball 复核，上游含 `src/LercTest/main.cpp`（C++ 测试程序）与 `OtherLanguages/js/tests/` 3 个 JS 测试，N=4。已按实测修正。
- **JS 测试不可运行逐条说明**：
  1. `sanity.mjs` — `import * as Lerc from "../dist/LercDecode.es.js"`，测试上游 **wasm 解码器**（4D 数据解码/statistics/像素值），非 C++ 库 API；CI 环境无 node、无 `dist/` wasm 构建产物。
  2. `level2.mjs` — 同样导入 wasm 解码器 + 读取 `../data/lerc` 编码数据文件，需完整 JS 发行目录；C++ 构建不产生该产物。
  3. `sanity-umd.cjs` — UMD 变体，同样依赖 `LercDecode` wasm 运行时。
  → 三者均为 JS/wasm 侧测试，与本次 C++ `libLerc` 适配无运行路径关联，判 N/A 并如实申报。
