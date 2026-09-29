# inversify-cpp 2.1.0 适配笔记

## 编译环境
- 构建系统: header-only（上游唯一构建面是 Bazel，设备与 CI worker 均无 bazel ⇒ 按上游 BUILD 参数等价直编直跑）
- 编译日期: 2026-09-28
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，libc++ 15004）
- 状态: built

## 编译步骤

1. `conan create` → `source()` 按 `conandata.yml` 官方 HTTPS URL 下载 tag `2.1.0` 归档
   （sha256 与 CCI 逐字一致，144131 字节），`strip_root=True` 解包。
2. `build()`（上游测试集成）：
   ```sh
   clang++ -std=c++17 -DINVERSIFY_BINDING_INSPECTION \
     -I <src>/include -I <src>/third_party -I <src>/test \
     <src>/test/{main,auto_resolve,constant_resolve,dynamic_resolve,inspection,speed}.cpp \
     -o <build>/inversify-cpp-upstream-test
   <build>/inversify-cpp-upstream-test
   ```
   命令与上游根 `BUILD` 的 `cc_binary("test")`（copts `-std=c++17 -pedantic-errors -Wall -Wextra
   -Wshadow -Wunused`、deps catch2 + inversify + test_mocks、`-DINVERSIFY_BINDING_INSPECTION`）
   等价对齐；单进程顺序编译 6 个 TU，不引入 `-j` 超订（affinity 8 vs os.cpu_count 20）。
   汇总行 `All tests passed (25 assertions in 5 test cases)`。
3. `package()`：只交付 `include/mosure/**`（**11 个头**：9 个 `mosure/*.hpp` + `exceptions/resolution.hpp` + `interfaces/icontainer.hpp`；上游另有 `single_include/` 单头**不随包交付**）与 `licenses/LICENSE`；
   `package_info()` 置 `cmake_file_name=inversify-cpp`、`cmake_target_name=inversify-cpp::inversify-cpp`、
   `bindirs=libdirs=[]`。
4. `test_package/`：`find_package(inversify-cpp)` 消费真实交付头，23 条运行期 check +
   2 条编译期 static_assert，`test()` 用 `self.run` 真跑消费者二进制。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无 CMake/autotools/Makefile 构建入口，只有 Bazel（`BUILD`/`WORKSPACE`/`.bazelrc`） | 上游只维护 Bazel 面 | header-only 配方在 `build()` 按上游 `cc_binary("test")` 的参数等价直编直跑；不引入 Bazel、不加构建系统补丁（零补丁） |
| 2 | 消费者测试首版 `std::make_unique<EnglishGreeter>` 构造失败 | 自动注入按 `Injectable<U>` 声明的依赖列表构造；未声明时传入的参数包不匹配 | 按上游 mock 惯例给消费者侧类型写 `template<> struct inversify::Injectable<T> : inversify::Inject<...>`（消费者测试文件内，不改上游） |
| 3 | `lang-preflight` 首跑报 `env_unsupported`（detected=python） | 工具 `--src` 传空时回落到任务 worktree（容器层脚本多为 Python） | 以 `$BUILD_SRC_DIR` 显式传 `--src` 重跑 → `detected=cpp`、rc=0；空 `--src` 假终态已入工作区 feedback |
| 4 | 消费者断言计数自报 1（实为 2） | `constexpr bool k_static_asserts = 2;` 被隐式转成 `true` 打印成 1 | 改 `constexpr int`（类型与语义一致），避免计数口径失真 |

## 源码修改

无补丁（`patches_applied: []`）：上游 `test/*.cpp` 与 `include/**` 在 clang 15 + libc++ 15004
下原样可编译可运行（W0 编译探针 + 干净轮 `conan create` 双证）。

## 依赖版本

- 运行期：**0**（与任务卡一致，`requirements()` 不存在）
- 构建期：0（上游 Catch2 v2 单头 vendored 在 `third_party/catch2/catch.hpp`，无需 `test_requires`）

## 验证结果

```bash
# W0 编译探针（aarch64/OHOS，源码树直编）
clang++ -std=c++17 -DINVERSIFY_BINDING_INSPECTION -I include -I third_party -I test test/*.cpp -o upstream-test
# → rc=0（3 条 -Winconsistent-missing-override 警告，0 error）
HOME=$TASK_DIR/test-home ./upstream-test
# → rc=0，All tests passed (25 assertions in 5 test cases)

# 采信轮（清缓存四步 + conan-verify + 证据副本）
sh tools/conan_verify_round.sh inversify-cpp 2.1.0 --repo "$TARGET_REPO" --task-dir "$TASK_DIR"

# 消费者
./test_inversify_cpp → inversify-cpp consumer checks: 23 run, 0 failed（rc=0）
```

## 注意事项

- header-only 形态命中 conan-verify 路径解析缺陷（G4/L2/L4/L5 走「跳过」分支却并列打 ✅），
  按判读口径以 `⏭️ 跳过` 为准并人工补测（`reports/conan-verify-supplement.md`）。
- tag 形态是 **`2.1.0`（无 v 前缀）**，URL 与版本目录均按无前缀形态。
- `manifest.yaml` 的 `status` 按 O5 口径保持 `built`，合并 + CI upload 确认后才可 `published`。
