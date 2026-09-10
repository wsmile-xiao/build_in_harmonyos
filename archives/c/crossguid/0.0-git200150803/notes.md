# crossguid 0.0-git200150803 适配笔记

## 编译环境

- **类型**：C++11 静态库（无 CMake，2015 快照，直接编译）
- **编译日期**：2026-09-10
- **编译器**：clang / clang++ 15（HarmonyOS PC，aarch64）
- **平台**：arm64-ohos（OpenHarmony PC）
- **状态**：built（待真机预检回填实测证据）
- **依赖**：uuid/2.40.1（已发布，transitive_headers/libs）

## 版本与源码说明

- 任务版本 `0.0-git200150803` 对应 Debian 系 `0.0+git200150803` 快照口径（`150803` = 2015-08-03）。
- 取上游官方提交 `8f399e8bd4252be9952f3dfa8199924cc8487ca4`（2015-08-03T15:35:46Z，Montellese win32 合并），为该日期当日上游 master 头。
- 源码包：`https://codeload.github.com/graeme-hill/crossguid/tar.gz/8f399e8...`，sha256 `022c9f02...abd99`（46KB，已本地下载验算）。
- 该快照尚无 CMakeLists.txt（CMake 构建系 2018 年 gabyx 重构才引入），官方构建方式即 `linux.sh`：`g++ -DGUID_LIBUUID guid.cpp + -luuid`。配方据此做等价直接编译，不虚构 CMake 开关。

## 编译步骤（conan create 全流程）

```bash
conan create archives/c/crossguid/0.0-git200150803 --build=missing
```

1. **source()**：`get()` 下载上述 codeload 包，`strip_root=True`。
2. **build()**：
   - 取编译器绝对路径（`tools.build:compiler_executables`，回退 `/data/service/hnp/bin/clang++`）。
   - `clang++ -c guid.cpp -std=c++11 -fPIC -DGUID_LIBUUID -I<uuid include>` 得 `guid.o`。
   - 静态 `llvm-ar rcs libcrossguid.a guid.o`（shared=true 时则链出 `.so`）。
   - 上游测试：同 flags 编译 `test.cpp + testmain.cpp + guid.cpp` 链 `libuuid.a` 得 `crossguid_upstream_test` 并执行，断言输出含 `All tests passed!`，打印 `HMBS_UPSTREAM_TEST_RESULT`。
3. **package()**：拷贝 `guid.h → include/`、`libcrossguid.a(.so) → lib/`、`LICENSE → licenses/`。

## 上游测试清点（R51 申报）

- 目录：源码根 `test.cpp` / `test.h` / `testmain.cpp`（`linux.sh` 最后两行即 `./test`）。
- 用例：单可执行文件，内含 6 个断言——3 个随机 guid 互异、s1≠s2、s1=s4、3 组字符串往返（s1/s2/s3）。
- 框架：custom（无 gtest/ctest，前 CMake 时代手写 harness，exit code + `All tests passed!` 判定）。
- 真机执行命令：`<build>/crossguid_upstream_test`（build() 内编译运行）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 快照无 CMakeLists，能否用 conan-center 0.2.2 的 CMake 配方照搬 | 2015 快照比 CMake 重构（2018）早 3 年，无 `CMakeLists.txt` | 改用 custom 直接编译，与 `linux.sh` 语义对齐 |
| 2 | Linux 分支需 `uuid/uuid.h` 与 `-luuid`，OHOS 有无该库 | `guid.cpp` 仅在 `GUID_LIBUUID` 分支调用 `uuid_generate` | `requires uuid/2.40.1`（仓库已 built），直传其 include/lib，不过 SYS_PREFIX，符合 R49 |
| 3 | R33 裸 `CC`/`CXX` 在 CI worker 为空 | release worker 不透传 shell 编译器变量 | 全部经 `self.conf tools.build:compiler_executables` 获取，fallback 真机绝对路径 |

## 依赖版本

- uuid/2.40.1（transitive_headers + transitive_libs）
- 无其他依赖；工具链 clang 15 / libc++（profile `ci/conan/profiles/ohos-aarch64`）

## 验证结果（待真机预检回填）

- 上游测试：`crossguid_upstream_test`，6 断言，待 HMBS 真机 evidence 轮摘录 `HMBS_UPSTREAM_TEST_RESULT`。
- test_package：`test_crossguid.py` 编译运行真实 `Guid`/`GuidGenerator` 调用（字符串往返 + newGuid 互异），2 用例，待摘录 `HMBS_TEST_PACKAGE_RESULT`。
- 证伪计划：确认测试输出非空且含 `All tests passed!`；必要时以 `exit 1` 桩替换被测库确认 harness 能抓失败；区分通过与静默跳过。

## 注意事项

- 本库非系统同名库，不触发 R26 静态强制；默认 `shared=False`，保留 `shared=True` 的 `.so` 路径。
- 纯用户态 GUID 库，无图形/多媒体/外设语义，不触发 R40 深度适配。
- patches/ 为空；未引入 `__OHOS__` 平台宏。
