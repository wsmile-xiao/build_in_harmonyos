# DRAFT — 上游 CMakeLists 内建 Conan 1 集成块在 Conan 2 下的适配处置

- **来源**: fruit 3.7.1 R01（google/fruit，CMake 构建的 C++ DI 框架），executor pc7-32，2026-09-28
- **同 stem 草稿**: `DRAFT-fruit-3.7.1-conan1-cmake-integration-block.kv`

## 问题

上游 CMakeLists.txt 以 Conan 1 时代的方式内建「是否由 Conan 构建」开关：

```cmake
set(FRUIT_IS_BEING_BUILT_BY_CONAN FALSE CACHE BOOL "...")
if("${FRUIT_IS_BEING_BUILT_BY_CONAN}")
  include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)   # Conan 1 生成器产物
  conan_basic_setup()                                  # Conan 1 命令
endif()
```

在本项目 OHOS 适配版 Conan 2.29.1 下：

- `conanbuildinfo.cmake` 不再生成 → `include could not find requested file`
- `conan_basic_setup` 命令不存在 → `Unknown CMake command "conan_basic_setup"`
- 若配方 `generate()` 把该开关设为 `YES`，`cmake.configure()` 必然失败（G2/W3 拦截）

## 根因

该开关绑定的是 Conan 1 的 CMake 集成协议（conan_basic_setup 负责设置依赖 include/lib 路径与编译选项）。Conan 2 改用 CMakeToolchain/CMakeDeps，无对应物；开关=YES 等于强制走一条不存在的路径。

## 方案（推荐，已实测）

配方 `generate()` **不设置**该开关（保持默认 FALSE），上游自然跳过 Conan 1 分支、走原生 CMake 构建：

```python
def generate(self):
    tc = CMakeToolchain(self)
    if self.settings.os == "OHOS":
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
    tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
    tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
    # 注意：不设 FRUIT_IS_BEING_BUILT_BY_CONAN=YES（Conan 2 无 Conan1 集成产物）
    tc.variables["FRUIT_USES_BOOST"] = "OFF"
    ...
```

行为说明（Release 构建类型下）：

- 上游 `if(NOT FRUIT_IS_BEING_BUILT_BY_CONAN)` 分支成立 → examples/tests 子目录被加入
- 但 `ALL` 默认目标只构建库本体（examples EXCLUDE_FROM_ALL；tests 的 pytest 套件仅注册不构建）
- 上游 pytest 套件在适配门禁单独 CMake 构建 + 运行（fruit: 336 声明 / 1201 实例全通过）

## 验证

- `conan create . --version=3.7.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64` → exit 0
- 上游 pytest：1201/1201 通过；test_package 消费者 + 鸿蒙专项测试编译/链接/运行通过
- 证据：`archives/f/fruit/3.7.1/reports/conan-create.log`（含修复前错误与修复后成功）

## 适用边界与反例

- **适用**: 上游 CMakeLists 以 `*_IS_BEING_BUILT_BY_CONAN`（或同类 Conan 1 标记）开启 `conan_basic_setup()`/`conanbuildinfo.cmake` 集成，且 Conan 2 适配仅需库本体（tests 可在门禁单独跑）。
- **不适用/反例**: 上游开关默认 TRUE 且无可绕开分支（无 `else` 路径）；或库本体构建也必须依赖该集成注入（此时应走 fallback：最小补丁移除集成块）。

## 与既有知识的关系

- `similar_to E321`（上游 Conan 1.x conanfile.py 迁移 2.x —— 对象是配方本身；本条目对象是 CMakeLists 内建集成块，四范围查重均未命中）
- `similar_to E470`（上游根目录 Bazel BUILD 与构建目录冲突 —— 同属「上游树内非常规文件/块与 Conan 2 工具冲突」族，但触发与方案不同）

## 查重表（四范围）

| 范围 | 结果 |
|---|---|
| 正式知识 knowledge/graph | 未命中（无 conanbuildinfo/conan_basic_setup 条目） |
| 图谱 index.tsv | 未命中 |
| 草稿 knowledge/drafts/ | 未命中 |
| recipes catalog | 未命中（fruit 无既有配方） |
