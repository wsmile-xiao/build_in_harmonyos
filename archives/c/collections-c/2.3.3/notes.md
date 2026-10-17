# collections-c 2.3.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-06
- 编译器: clang/clang++（OHOS SDK, aarch64-unknown-linux-ohos）
- 状态: built（本地门禁/验证完成；制品上传由 CI/发布流水线完成）

## 编译步骤

```bash
# 源码（官方 codeload 快照，上游无 release/tag，钉定 master HEAD dbedaf9）
curl -L https://codeload.github.com/srdja/Collections-C/tar.gz/dbedaf9599716c9aa16c6e955fdc3ef76d5c5cca -o collections-c-2.3.3.tar.gz
# sha256: 045b6509493c9c4dbb4578800de497c3ad8154545c41fbb3a774d50f0a832600

# 配置与构建
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang
cmake --build build -j4

# 上游测试（munit）
cd build && ctest --output-on-failure   # 16/16 Passed, 249/249 用例
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cc_dynamic_pool 非 packed 模式返回的块未按 alignment_boundary 对齐（mod16≠0） | 上游 `padding = size % boundary` 无法把 free_ptr 圆整到边界；建池时首块未对齐（纯算法缺陷，与平台无关） | 补丁 0001：建池首块对齐 + 分配时按 `(ptr+size)%boundary` 圆整 padding；扩页路径同步对齐 |
| 2 | conan create 时 test_package 报 include/collectc 不存在 | 上游 CMake 静态分支未设置 PUBLIC_HEADER，cmake.install() 不安装头文件 | 配方 package() 显式拷贝 src/include/** → include/collectc/（含 memory/、sized/） |
| 3 | 上游 string_test.c 无法编译（缺 cc_string.h） | 上游仓库本身不含该头文件（真实上游排除条件） | 最小补丁实测失败，保留 uninstantiated 1 条（/string/new），记录于双口径台账 |

## 源码修改

- `patches/0001-src-memory-cc_dynamic_pool.c.patch`：修复 cc_dynamic_pool 对齐
  （cc_dynamic_pool_new_conf 首块对齐；cc_dynamic_pool_malloc padding 圆整 + 扩页路径对齐）。

## 依赖版本

- 无强制第三方依赖（纯 C，仅 libc/libm）。

## 验证结果

```bash
# 鸿蒙专项测试（test_package/test_ohos_adapt.c，真实 API）
./ohos_adapt_test
# OHOS pool alignment (16-byte boundary) OK
# OHOS stress test (20000 ops per container) OK
# collections-c OHOS adaptation test: PASS

# 消费者冒烟（test_package/test.c）
./consumer_test   # size=3 elem=2, exit 0

# conan-verify（8 道门禁 G0-G4 全过）
python3 scripts/ohc-run.py conan-verify collections-c 2.3.3
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py + conandata.yml | v3.0 Conan 配方（CMakeToolchain，静态默认） |
| test_package/ | 消费者冒烟 + 鸿蒙专项测试 + MANIFEST.yml |
| patches/0001-*.patch | 池对齐修复补丁 |
| knowledge/drafts/DRAFT-collections-c-2.3.3-*.{kv,md} | 路径 B 知识草稿（池对齐、静态分支头文件缺失） |

## 注意事项

- 上游无 release/tag：版本按任务下发 2.3.3，源码钉定官方 master HEAD commit dbedaf9（codeload 官方 tarball，SHA-256 已核验）。
- 测试统计双口径：`249/250 (99.6%)` 全量（源码声明 250）；`249/249 (100%)` 当前配置可执行集合。
