# DRAFT: 上游测试框架 submodule 空目录 — conan test_requires + CMakeDeps 替代

> 来源: kangaru 4.3.2 HarmonyOS 适配（header-only DI 库）
> 状态: 草稿 (draft) — 与 DRAFT-kangaru-4.3.2-catch2-submodule-test-requires.kv 配对

## 问题

kangaru 4.3.2 官方 GitHub release tarball 不含 `.gitmodules` 指向的 submodule
内容：`test/third_party/Catch2` 与 `benchmark/third_party/benchmark` 均为空目录。
上游 `test/CMakeLists.txt` 写法：

```cmake
find_package(Catch2 QUIET)
...
if (NOT Catch2_FOUND)
    add_subdirectory(third_party/Catch2)   # ← 空目录 → 无 CMakeLists.txt → 配置失败
endif()
```

`conan create` 时报错 `The source directory ... does not contain a CMakeLists.txt file`。

## 根因

- GitHub 官方 tarball 只落地 submodule 的目录骨架（gitlink 不会随 tar 归档内容）；
- 上游"找不到框架就回退 vendored submodule"是常见模式，空 submodule 使回退路径直接崩溃；
- 对**测试框架**（非库本体功能）submodule，E150 的 manual-download（复制源码进树）
  会污染源码树产生 diff；E425 的"保持空占位"仅适合不需要该 submodule 内容的场景。

## 方案

recipe 中让 `find_package(Catch2)` 直接命中 conan 提供的包：

```python
def requirements(self):
    self.test_requires("catch2/2.13.10-r0")   # 只进测试/消费者，不进下游 requires

def generate(self):
    deps = CMakeDeps(self)
    deps.generate()                            # 生成 Catch2Config.cmake
    tc = CMakeToolchain(self)
    ...
```

- `test_requires` 语义: 仅为构建/测试本包提供，不传播给消费者；
- `CMakeDeps` 依据 catch2 配方的
  `cpp_info.set_property("cmake_file_name", "Catch2")` 生成 `Catch2Config.cmake`，
  上游 `find_package(Catch2)` 命中 `Catch2::Catch2` target，不再走空 submodule 回退；
- 空 submodule 目录保留原样（不删除、不下载、不写入），官方源码零 diff。

## 验证

```bash
conan create archives/k/kangaru/4.3.2 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing
# G2 PASS；test_package (4 断言) + OHOS 专项 (6/6) + 上游 ctest 21/21 全绿
```

- 本地 W3 全量 21/21（109 TEST_CASE 台账见 reports/test-run-ledger.log）；
- conan-verify G0-G4 + L2/L4/L5 全门禁通过。

## 适用边界

- C++ 库上游以 git submodule vendoring 测试框架（Catch2/doctest/gtest/google-benchmark），
  且官方 release tarball 不含 submodule 内容；
- Conan 2.x（本项目 2.29.1）+ ohpcd 制品仓有对应测试框架包；
- header-only 库测试套件秒级时可无条件在 build() 运行；重库可加 options 门控。
- 与 E150（manual-download 源码进树）、E425/E426（嵌入式 SDK 空占位裁剪）互补，
  本方案用于"测试必须真跑"的场景。

## 查重差异

| 范围 | 结果 |
|------|------|
| graph 正式条目 | E150 部分覆盖（方向相关，方案不同）；E425/E426 场景不同；E321/E322 配方骨架不含本手段 |
| doc/ | 无直接条目 |
| drafts/ | DRAFT-qtscxml-6.11.1-qt6-submodule-cmake-find（Qt6 submodule）相关；无 Catch2+test_requires+CMakeDeps 现成草稿 |
| 结论 | 部分覆盖、存在新增差异 → 路径 B 草稿 |