# robin-hood-hashing 3.11.5 适配笔记

## 编译环境
- 构建系统: cmake（header-only，无编译）
- 编译日期: 2026-09-08
- 编译器: clang 15.0.4 / clang++ (OHOS SDK 26.0.0.18, aarch64-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 1. init-build（官方 tag 3.11.5 tarball）
python3 scripts/ohc-run.py init-build robin-hood-hashing 3.11.5 --url=https://github.com/martinus/robin-hood-hashing

# 2. lang-preflight: detected=cpp, 通过

# 3. 上游测试构建（独立 CMake 项目模式，构建单一 rh 可执行）
cd $BUILD_SRC_DIR && mkdir -p build && cd build
cmake .. -DCMAKE_CXX_STANDARD=14 -DCMAKE_BUILD_TYPE=Release \
  -DCLANG_TIDY_PROGRAM= \
  -DCMAKE_CXX_FLAGS="-fPIC -O2 -Wno-sign-conversion -Wno-error=sign-conversion"
make rh -j4
./rh   # 127/127 test cases, 2,164,686 assertions, 0 failed

# 4. 配方：header-only（conanfile.py 无编译、package() 复制头文件）
# 5. conan create + test_package 消费者验证通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | clang 15 报 `__has_trivial_copy is deprecated` 且 -Werror 拦截 | clang 定义 `__GNUC__=4`，误入上游 `__GNUC__ < 5` 兼容分支，使用被弃用的内建宏 | 补丁 0001：条件加 `!defined(__clang__)`，改走 `std::is_trivially_copyable` |
| 2 | 测试程序编译被 clang-tidy warnings-as-errors 卡住 | 上游 CMakeLists 在 Clang 下 `find_program(clang-tidy)` 并启用 `CMAKE_CXX_CLANG_TIDY`，其 `misc-const-correctness`/`readability-identifier-length` 是测试代码风格问题 | 本地构建传 `-DCLANG_TIDY_PROGRAM=` 禁用（CI 不跑测试程序，只跑 conan create，不受影响） |
| 3 | `PERF_EVENT_IOC_ID` 宏触发 `-Wsign-conversion` | OHOS sysroot 的 perf_event.h `_IOR` 宏展开 unsigned long → int 比较 | 测试构建加 `-Wno-sign-conversion` |
| 4 | test_package 报 `Cannot determine link language for target` | 源文件名为 test.c 但内容是 C++，CMake 按 .c 扩展名判为 C，而 project 只声明 CXX | 源文件改名 test.cpp |
| 5 | conan2 `copy()` 复制不到文件（"No files in this package!"） | src/dst 传相对路径与 pattern 语义不符 | src/dst 用 `os.path.join(self.source_folder/self.package_folder, ...)` 绝对路径，pattern 用文件名 |
| 6 | 补丁未应用到包内头文件 | conandata.yml `patches: {}` 空、且 patch 应用写在 package() 内 | conandata.yml 声明 patch_file/patch_description/patch_type；`apply_conandata_patches` 移到 source() |
| 7 | github.com 直连下载超时（source() 阶段） | 网络抖动，github 30s connect timeout | conan-verify G2 自动 E017 镜像注入 ghfast.top；本地手动 create 临时改 URL 后恢复 |

## 源码修改

- `patches/0001-src-include-robin_hood.h.patch`：排除 clang 使用弃用的
  `__has_trivial_copy`（`#if defined(__GNUC__) && __GNUC__ < 5 && !defined(__clang__)`）。

## 依赖版本

- 零运行时依赖（header-only）。
- 测试程序仅用标准库 + doctest 2.4.6（上游 vendored）。

## 验证结果

```bash
# 上游测试（本机构建 rh 可执行）
./rh  →  test cases: 127 | 127 passed | 0 failed | 73 skipped
         assertions: 2164686 | 2164686 passed | 0 failed
# conan create + test_package（CI 同源）
conan create ... --build=missing  →  100% tests passed (test_robin-hood-hashing 1/1)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-only 配方（package_type=header-library，无编译） |
| conandata.yml | 官方源 + sha256 + patch 声明 |
| patches/0001-*.patch | clang 15 兼容补丁 |
| test_package/ | 真实调用 robin_hood.h API 的消费者测试 |

## 注意事项

- 本库为 header-only：`conan create` 无编译，`finish` W3 的 conan create 门禁即
  消费者编译 + test_package 运行；上游测试已在探索阶段完整运行（127/127）。
- 测试统计口径：上游 127 test cases 全部通过；73 skipped 为性能 bench/count
  类用例（doctest 默认跳过，不参与断言）。
---

**编译结束**: 2026-09-08 22:13
**最终状态**: built
