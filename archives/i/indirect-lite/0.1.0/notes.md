# indirect-lite 0.1.0 适配笔记

## 编译环境
- 构建系统: cmake（header-only INTERFACE library）
- 编译日期: 2026-09-02
- 编译器: clang 15.0.4 / clang++（OHOS PC aarch64，libc++-ohos）
- 状态: published

## 编译步骤

```bash
# 源码下载（GitHub 直连超时，通过 ghfast.top 镜像下载官方 tag tarball）
# sha256: 47598b351ed897df4a0f897ab0d30079ce95043648aa978de13575b7ef706fc3

# 原生验证编译（确认上游测试可跑）
cmake -DCMAKE_INSTALL_PREFIX=... -DINDIRECT_VALUE_LITE_OPT_BUILD_TESTS=ON -DINDIRECT_VALUE_LITE_OPT_BUILD_EXAMPLES=ON ..
make -j2 && ctest --output-on-failure   # 4/4 全过

# Conan 配方验证（OHOS aarch64 profile）
python3 scripts/ohc-run.py conan-verify indirect-lite 0.1.0   # G0-G4/L2/L4/L5 全绿
python3 scripts/ohc-run.py finish indirect-lite 0.1.0 published  # W3 本地 CI 模拟通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连下载超时 | 本机到 github.com 网络不可达 | 用 ghfast.top 镜像下载官方 tag tarball，conandata.yml 仍保留官方 URL（CI 侧自动注入镜像），SHA-256 核验一致 |
| 2 | cpp11 测试目标编译失败：`no template named 'is_null_pointer' in namespace 'std'` | `std::is_null_pointer` 是 C++14 特性；OHOS libc++（libcxx-ohos）严格按标准版本暴露，-std=c++11 下不存在；上游头文件声明支持 C++11 但 relational-operator 扩展直接用该 C++14 trait | 头文件 `std11` polyfill 命名空间新增 C++11 回退实现（`std::is_same<remove_cv<T>, nullptr_t>`），12 处 operator enable_if 改用 `std11::is_null_pointer` |
| 3 | conan-verify G1 失败：缺 export_sources/补丁应用 | 初版配方未按 Conan 2 头文件库规范 | 补 `export_sources()=export_conandata_patches(self)`、`source()` 中 `apply_conandata_patches(self)` |
| 4 | conan create 中补丁未生效 | conandata.yml 的 patches 未登记（初版为空） | 按仓库标准格式登记 patch_file + description + type |
| 5 | test_package 编译失败（误用私有/非法 API） | 消费者测试写了 `reset()`（私有成员）与 `p->operator int&()`（非法表达式） | 改为仅用公开 API：operator->/swap/move 构造/value/has_value |
| 6 | W3 JC 全量扫描误报其他库垃圾文件 | 本地分支无提交时 JC 降级 full 模式扫描整个 worktree | 先提交本库变更使 JC 以增量模式只检本库文件 |

## 源码修改

- `patches/0001-include-nonstd-indirect_value.hpp.patch`：
  - 新增 `nonstd::iv::std11::is_null_pointer` C++11 polyfill（C++14 及以上 `using std::is_null_pointer`）
  - 12 处 relational operator 的 `std::is_null_pointer<...>` 改为 `std11::is_null_pointer<...>`

## 依赖版本

- 无第三方运行时依赖（header-only）
- 工具链: clang 15.0.4 / CMake 4.1.2 / Conan 2.29.1（OHOS 适配版）

## 验证结果

```bash
# 上游测试（lest，54 个 CASE x 4 标准目标）
ctest --output-on-failure   # test-cpp11/cpp14/cpp17/cpp20 全部 PASSED
# 通过率: 54/54 = 100%（全目录发现 54 个独立上游用例）

# 消费者测试
./test_indirect_lite       # PASS

# W3 本地 CI 模拟
# setup.sh + build_and_test.sh 通过，Pass rate: 100% (1/1)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py / conandata.yml / test_package/ | Conan 2.x 配方（header-library），conan create 生成头文件 + CMake config 产物 |
| patches/0001-*.patch | C++11 is_null_pointer polyfill |

## 注意事项

- 本库为 header-only，无二进制产物，`package_type=header-library`，`cpp_info.libs=[]`。
- conandata.yml 保持官方 GitHub URL；本地下载的镜像路径绝不入仓。
- E130（change-cxx-standard）与本候选部分重叠但方案不同：E130 建议整体提升测试标准到 C++17，本修复以 polyfill 保留 C++11 支持（更小改动、不丢 C++11 兼容），见知识候选台账。

---

**编译结束**: 2026-09-02 23:31
**最终状态**: published