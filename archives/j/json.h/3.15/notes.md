# json.h 3.15 适配笔记

## 编译环境
- 构建系统: header-only（无构建系统；上游测试用 cmake）
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，OHOS aarch64 工具链）
- 状态: built

## 编译步骤

json.h 为单头文件 C/C++ JSON 解析库（上游无 v3.15 tag，仅有 pre-ai 与 main；
分析端绑定版本 3.15，源码固定到官方 main commit 671f1a382b 的 commit 归档）。
配方按 header-only 打包 json.h → include/：

```bash
# 上游测试（test/ CMake 项目）
cmake -S test -B build -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++
cmake --build build -j20
ctest --test-dir build --output-on-failure

# 配方验证（W3 / conan-verify）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试 test_shared.h 编译失败：`error: unknown warning group '-Wunsafe-buffer-usage', ignored [-Werror,-Wunknown-warning-option]` | `-Wunsafe-buffer-usage` 仅 Clang>=16 存在，OHOS clang 15 不识别；无条件 `#pragma clang diagnostic ignored` 配合上游 -Weverything -Werror 提升为错误 | `__has_warning("-Wunsafe-buffer-usage")` 守卫（与同文件 -Wglobal-constructors 等既有模式一致）；登记 patches/0001 + conandata patches（E550 草稿） |
| 2 | init-build 把 test/ 子目录误提升为源码根，json.h 头文件丢失 | 单头文件库根目录无构建标记（CMakeLists 在 test/ 内），提升逻辑按构建标记找源码 | 重建 work/orig 源码树：json.h 留在根，test/ 保留为子目录；tarball SHA-256 复核一致 |
| 3 | conan create 报 `Imported target "json.h" includes non-existent path .../p/include` | package() 中 copy() 的 dst 相对路径按进程 CWD 解析，落到构建目录 | dst 改用 `os.path.join(self.package_folder, "include")` 绝对路径（E321/picojson 既有知识） |
| 4 | conan create 报 `Package type is 'library', but no 'shared' option declared` | header-only 库 package_type 应为 header-library | package_type = "header-library" |
| 5 | conan-verify G1 失败 | header-only 配方缺少 build()/export_sources/apply_conandata_patches 方法声明 | 补齐空 build() + export_sources + apply_conandata_patches（E257 既有知识：header-only no-op build） |

## 源码修改

- patches/0001-test-test_shared.h.patch：test/test_shared.h 顶部
  `-Wunsafe-buffer-usage` pragma 用 `#if __has_warning(...)` 守卫（+2/-0），
  保证上游测试可在 OHOS clang 15 下编译运行；该文件属上游测试源，不入包。

## 依赖版本

无第三方依赖（纯单头文件库，Unlicense 许可）。

## 验证结果

```bash
# 上游测试（含 9 个语言标准分支 × 185 声明 = 1665 注册用例）
./json_test          # 1665/1665 passed
ctest --output-on-failure  # 4/4 (json_test/address/undefined/thread) passed
# 鸿蒙专项测试（test_ohos/ohos_test.c，公开 API 验证 4 组）
./ohos_test          # ALL OHOS json.h special tests passed
# 消费者（test_package/test_package.c，真实解析并断言 version==3）
./test_json_h        # json.h consumer test passed: parsed object, version=3
# W3 本地 CI
conan create ...     # exit_code=0（.ci-result.json log_sha256 可追溯）
```

## 测试统计（双口径）

- 上游源码声明: 185（test_shared.h 中 JSON_TEST ×157 + JSON_TEST_F ×28）
- 当前配置注册/执行: 1665（9 标准分支 × 185，json_test 全部通过）
- 通过率: 1665/1665（100%）；失败 0；未运行 0
- 上游 sanitizer 变体: address/undefined/thread 通过；memory 按上游探测规则
  compile=FALSE 未注册（非用户用例，不计入声明分母）

## 交付物

无二进制打包产物（header-only：include/json.h + licenses/LICENSE）。

## 注意事项

- 上游无 v3.15 tag：版本 3.15 由分析端绑定，源码固定官方 main commit
  671f1a382b（tarball SHA-256 b06abf52...，json.h 内容 SHA-256 82997541...）。
- W3 JC 门禁命中的 archives/c/cloog/0.21.1 与 archives/k/kics/2.1.20 三个
  隐藏标记文件为其他库既有基线（提交前已存在），已按基线隔离规则复验
  （隔离→重跑 W3 通过→原样恢复，SHA-256 前后一致 e3b0c442...），未修改、
  未提交、未写入知识库或 PR。
- 知识库扩展（路径 B）：E550 草稿（.kv + .md 配对）与 json.h 归档同 PR 交付。
