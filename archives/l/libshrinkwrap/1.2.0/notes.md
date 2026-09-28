# libshrinkwrap 1.2.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 INTERFACE target + BUILD_TESTS 测试目标）
- 适配日期: 2026-09-27
- 编译器: OHOS clang/clang++（aarch64-linux-ohos，DevEco Studio SDK llvm 15.0.4）
- 目标 profile: ci/conan/profiles/ohos-aarch64（os=OHOS, clang 15, libc++, cppstd=17）
- 状态: built（本机前置 + 真机 shadow CI 通过，2026-09-27）

## 上游信息（W0/W1）
- 上游仓库: https://github.com/jonathonl/shrinkwrap（Conan 包名 libshrinkwrap）
- tag: v1.2.0，源码归档 sha256 aa15583079c3dfccb118cf36fae9bc6353920b99d0204a9e349dad027b531286
- 许可证: MIT（Copyright (c) 2017 Jonathon LeFaive）
- 性质: header-only C++11。5 个头文件（gz/istream/stdio/xz/zstd.hpp，共 2128 行），
  src/ 仅含上游测试程序 test.cpp。CMake `add_library(shrinkwrap INTERFACE)`。
- 上游依赖（requirements.txt + find_library）: xz 5.2.3 / zstd v1.3.2 / zlib 1.2.11
  （上游 CI 用 cget 安装）；本适配改用制品仓 Conan 包（见下）。
- 上游测试: `cmake -DBUILD_TESTS=ON` → shrinkwrap-test，ctest 注册 11 个用例，
  每个按 2048/512/1024 三种块大小链式执行（33 条子链）。scratch 文件写在进程 cwd。

## W0 依赖结论
- 依赖数量: 3（xz、zlib、zstd；均为链接期依赖，header-only 库自身无编译）
- 已满足依赖:
  - xz/5.8.3.2（制品仓 status: built，2026-08-23）
  - zlib/1.3.2.1（制品仓 status: built，2026-09-24）
  - zstd/1.5.7.1（制品仓 status: built，2026-08-09）
- 缺失依赖: 无
- 是否需要拆分依赖适配: 否
- 阻塞点: 无（R36 由 CI L0i 复核）
- 下一步: 真机 shadow CI

## 编译步骤（配方设计，待真机执行）
1. conan create 按项目 CI 入口执行（build_and_test.sh 单包模式）。
2. source(): conandata.yml 官方 URL（R39 单值，走 CI 镜像改写 + 预下载重试）。
3. generate(): CMakeToolchain，注入
   - CMAKE_POLICY_VERSION_MINIMUM=3.5（上游 cmake_minimum_required(3.2)，CMake≥4 防御）
   - CMAKE_LIBRARY_PATH=<xz|zlib|zstd 包 lib 目录>（让上游裸 find_library 命中）
   - BUILD_TESTS=ON
4. build(): configure → build → ctest --output-on-failure（L1 上游官方测试）。
5. package(): include/shrinkwrap/*.hpp + LICENSE。不跑上游 cmake install
   （install(EXPORT) 烧录构建机绝对路径，消费端不可用；接口由 cpp_info 提供）。
6. test_package(): CMake 消费者程序链接 shrinkwrap::shrinkwrap，23 条断言。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 find_library 找不到 Conan 依赖 | 依赖装在各自包目录而非系统路径 | generate() 注入 CMAKE_LIBRARY_PATH（x/z/zstd 的 cpp_info.libdirs），不改上游文件 |
| 2 | 上游 cmake_minimum_required(3.2) | CMake >= 4 拒绝 <3.5 | 钉 CMAKE_POLICY_VERSION_MINIMUM=3.5（lazperf 先例） |
| 3 | install(EXPORT) 烧录绝对路径 | 上游导出 find_library 结果 | package() 只装头文件+LICENSE，消费接口走 cpp_info/CMakeDeps |
| 4 | worktree 检出 gama 目录报 Invalid argument | origin/main 上有文件名含 \r\r 的文件，Windows 无法创建 | 本地 sparse-checkout 排除 /archives/g/gama/（仅本机检出问题，不影响提交内容） |
| 5 | g++ 13（libstdc++）编译上游 TU 失败：'uint8_t' is not a member of 'std' | 上游 5 个头文件用 std::uint8_t/std::uint64_t 却不 include <cstdint>；libc++（OHOS）经其他头传递引入所以能过，libstdc++ 无传递包含 | OHOS 无需补丁（交叉编译实测通过）；本机 libstdc++ 验证用 -include cstdint 绕过；根治可上游（各头文件加 #include <cstdint>）。已沉淀 knowledge/drafts/DRAFT-libshrinkwrap-1.2.0-headers-rely-on-transitive-cstdint-libcxx |
| 6 | 消费者测试 zstd seekg(0, beg) 断言失败 | zstd::ibuf::seekoff 只支持 (0, cur)（tellg），方向定位返回 -1 | 绝对定位改用 seekg(0)（走 seekpos，上游 block_seek 同款用法）；修正后 23/23 通过 |

## 源码修改

无补丁（patches_applied: []）。上游源码零修改：
- E002（只读根文件系统）不触发——上游测试 scratch 写在 cwd（Conan build 目录）
- 无 configure 期网络下载（gtest 类依赖不存在）
- 无 musl/glibc 差异点——仅用 lzma/zlib/zstd 公开 API + ISO C++11 + stdio

## 依赖版本

- xz/5.8.3.2（上游 lzma API；本机交叉编译冒烟用 xz-5.8.3 官方头文件，sha256 与
  仓库 conandata 一致：fff1ffcf2b0da84d308a14de513a1aa23d4e9aa3464d17e64b9714bfdd0bbfb6）
- zlib/1.3.2.1（OHOS sysroot 自带 zlib.h 用于冒烟；真机走 Conan 包）
- zstd/1.5.7.1（上游 v1.5.7；冒烟用官方 zstd-1.5.7 头文件，sha256
  eb33e51f49a15e023950cd7825ca74a4a2b43db8354825ac24fc1b7ee09e6fa3，与仓库 conandata 一致）

## 验证结果（W4 本机前置，2026-09-27）

```text
1. 配方静态检查
   - python -m py_compile conanfile.py / test_package/conanfile.py        → 通过
   - PyYAML 解析 conandata.yml / manifest.yaml / MANIFEST.yml             → 通过
   - conanfile.py 无 UTF-8 BOM（CI L0i 教训自查）                          → 通过
   - CI L0 门禁逐项自查（L0a~L0i）                                        → 通过
     （test_package 结构齐全；test() 含 self.run()；MANIFEST.yml 存在；
      无硬编码 remote、无裸 ${CC} 类环境变量依赖；requires 为 AST 可提取的
      字面量——已用 CI 同款 AST 脚本实测提取出 3 个依赖；三个依赖均已发布）
   - git diff --check                                                     → 通过
2. 源码归档 SHA256 复核
   - 实测下载 sha256 aa155830...31286 == conandata 声明值                  → 一致
3. aarch64-linux-ohos 交叉编译冒烟（DevEco SDK clang 15.0.4 + libc++ sysroot）
   - 上游官方测试 TU（src/test.cpp + 5 个头文件）                          → 编译通过
   - 消费者测试 TU（test_package/test_libshrinkwrap.cpp）                  → 编译通过
   - llvm-readelf 确认产物 ELF64 / AArch64                                 → 确认
4. x86_64 Linux 原生实跑（Docker ubuntu:24.04，g++ 13，apt 版 zlib/lzma/zstd）
   - 上游官方测试：cmake -DBUILD_TESTS=ON → ctest  11/11 全部通过
     （33 条子链，seek 链每条含 128 次随机定位读；需 -include cstdint，
      见问题 #5）
   - 消费者测试（g++ 直接链接 -llzma -lz -lzstd）：23/23 断言全部通过
5. 本机未执行项（如实申报）
   - conan create / test_package 的 Conan 全流程实跑：本机无 conan → 待 CI/真机
   - OHOS aarch64 上的上游测试与消费者测试运行：待真机 shadow CI
```

## 注意事项

- 上游 README 的 "XZ input stream" 示例把 ostream 误写成 istream（`shrinkwrap::xz::ostream is(...)`），
  以 src/test.cpp 实际 API 为准（`shrinkwrap::xz::istream/ostream` 等均存在）。
- generic `shrinkwrap::istream` 把 \x1F 魔数全部交给 bgzf::ibuf（兼容普通 gzip），
  不支持拼接 xz 流（README 明示）——消费者据此选型。
- zstd seek 为压缩块边界语义，且 seekoff 只支持 (0, cur)：`seekg(0, beg)` 会失败，
  要用 `seekg(pos)` 绝对定位；消费方做精确 seek 请用 bgzf（虚拟偏移）或 xz（lzma index）。
- 制品仓如遇 R37 同版本冲突（libshrinkwrap/1.2.0 已存在），按流程递增为 1.2.0.1 并同步
  目录/配方/manifest/test_package/分支名。

## 真机 shadow CI 记录（W5，2026-09-27）

隔离 job：`libshrinkwrap-1.2.0-20260927`（--repo-source 方式，设备无 git 远端 clone）。
传输校验：tar.gz SHA256 每轮与本机一致。

### 迭代记录表（附A 口径）

| 项 | r1 | r2 | r3（最终） |
|---|---|---|---|
| run 目录 | …-conan-20260927-152915 / -153304 | …-conan-20260927-154543 | …-conan-20260927-154804 |
| 排队等待秒数 | 0 | 0 | 0 |
| exit code | 1 | 1 | **0** |
| L0 | 未到 | pass | **pass: all checks passed** |
| L1 | 未到 | fail: conan create failed | **pass: upstream tests + test_package executed** |
| L2 | 未到 | skip: not run | **skip: no bin/ dir（纯库正常）** |
| L4 | 未到 | skip: not run | **pass: no patches** |
| L5 | 未到 | skip: not run | **warn: no bin/lib artifacts（header-only 仅 include/，预期）** |
| 上游测试 | 未执行 | 编译失败（lzma.h not found） | **11/11 Passed（100%，0.27s）** |
| test_package | 未执行 | 未执行 | **ctest 1/1 + 二进制直跑 23/23 断言** |
| 本轮报错原文 | `build_and_test.sh:164: permission denied: git` | `Package type is 'library', but no 'shared' option declared` → 重试后 `fatal error: 'lzma.h' file not found` | 无 |
| 根因 | HMDFS 分区 git shim 无执行权（G0e 调 git） | ① Conan 2 强制 library 类型声明 shared；② 上游测试 TU 无依赖 include 路径 | — |
| 解法 | job env.sh 加 `/data/service/hnp/bin` 到 PATH（真 git 2.45.2，非 HMDFS） | ① package_type 改 header-library（ref: E283 shared 契约）；② generate() 经 extra_cxxflags 注入三个依赖包 include 目录 | — |

### 真机最终结果（r3）

```text
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
  L1a test_package executed / L1b 测试证据 / L1c 上游 ctest 均确认
L2_RESULT=skip: no bin/ dir        （header-only 正常，未伪造 bin 测试）
L4_RESULT=pass: no patches         （零补丁）
L5_RESULT=warn: no bin/lib artifacts（header-only 产物=include/+licenses/，预期）
L1e 破坏性反验证：[sabotage] include/ moved away → test 如期失败
                  → "test genuinely depends on libshrinkwrap"
上游 ctest：100% tests passed, 0 failed out of 11（33 条子链）
test_package：ctest 1/1 Passed + 消费者二进制 23/23 checks passed
package()：Packaged 5 '.hpp' files + LICENSE
制品仓依赖二进制：xz/5.8.3.2、zlib/1.3.2.1、zstd/1.5.7.1 经 ohpcd 正常解析
conandata.yml 由 CI 预下载改写并已自动还原官方 URL（JC 无残留）
```

## 下一步（W6）

- 网站侧提交与 PR：`python3 scripts/ohc-run.py submit libshrinkwrap 1.2.0`（含门禁 + push + 建 PR）
- PR 描述按 rule1/rule4/rule12 模板字段填写（上游 11/11、鸿蒙特有测试 23 断言）
