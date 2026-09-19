# libremidi 5.4.3 适配笔记

## 编译环境

- 构建系统: CMake（≥3.22，实测 CMake 4.4.3）
- 编译日期: 2026-09-19
- 编译器: clang（profile clang 15 / harmonybrew SDK clang 23.1.1，target aarch64-unknown-linux-ohos）
- 依赖: catch2/3.16.0（仅测试用，`test_requires`，制品仓已发布）
- 状态: built

## 编译步骤

```sh
conan create archives/l/libremidi/5.4.3 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

配方等价的 CMake 参数：

```
-DLIBREMIDI_LIBRARY_MODE=LIBRARY -DLIBREMIDI_TESTS=ON -DLIBREMIDI_EXAMPLES=OFF
-DLIBREMIDI_NO_ALSA=ON -DLIBREMIDI_NO_UDEV=ON -DLIBREMIDI_NO_JACK=ON
-DLIBREMIDI_NO_PIPEWIRE=ON -DLIBREMIDI_NO_NETWORK=ON -DLIBREMIDI_NO_BOOST=ON
-DLIBREMIDI_NO_ANDROID=ON -DLIBREMIDI_CI=ON -DLIBREMIDI_NO_WARNINGS=ON
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `get()` 报 `BadZipFile: File is not a zip file` | codeload 的 URL 末段是 `refs/tags/v5.4.3`，Conan 按扩展名猜格式，猜成 zip | conandata 里加 `filename: "libremidi-5.4.3.tar.gz"`（仓库里 abbtr / accel-config 同做法） |
| 2 | 配置阶段尝试 `git clone https://github.com/catchorg/Catch2` | 上游 `cmake/libremidi.tests.cmake` 用 FetchContent 拉 Catch2 v3.4.0，真机 github.com 不可达 | 最小补丁把该段换成 `find_package(Catch2 CONFIG REQUIRED)`，配 `test_requires("catch2/3.16.0")`；不改任何测试源文件 |
| 3 | `LIBREMIDI_NO_PIPEWIRE=OFF` 时又要 FetchContent 拉 readerwriterqueue | `cmake/libremidi.deps.cmake`：`UNIX AND NOT APPLE AND NOT LIBREMIDI_NO_PIPEWIRE` 就需要它 | 显式 `-DLIBREMIDI_NO_PIPEWIRE=ON`（真机也没有 PipeWire） |
| 4 | `midiin_test`/`midiout_test` 红：`REQUIRE(in.get_current_api() == libremidi::API::KEYBOARD)` 拿到 65535 | 上游用例硬断言具体后端；真机既无 JACK 也无 ALSA，keyboard 后端又是纯 C++ | 保留 keyboard 后端（不传 `LIBREMIDI_NO_KEYBOARD`），并打开上游自带的 `LIBREMIDI_CI` 模式让缺设备的 creation 用例 SKIP；`LIBREMIDI_CI` 会附带 `-Werror`，故同时 `LIBREMIDI_NO_WARNINGS=ON` |
| 5 | test_package 配置失败：`Library 'remidi' not found in package` | 上游 CMake target 名就是 `libremidi`，Linux 产物是 `liblibremidi.a` | `cpp_info.libs = ["libremidi"]` |
| 6 | 消费者编译报 `unknown type name 'concept'` / `no template named 'span' in namespace 'std'` | 公开头文件（`configurations.hpp`、`message.hpp`）用了 C++20 的 `concept`/`requires`/`std::span`，而 profile 是 cppstd=17 | test_package 显式 `CXX_STANDARD 20`；PR 说明里写明消费方需 C++20 |
| 7 | 消费者 `midi_in::get_current_api()` 与头文件 `midi1::default_api()` 不相等 | `default_api()` 是头文件里按后端宏算出的编译期常量；配方删掉了上游导出的 cmake config，宏没传出去 | `cpp_info.defines = ["LIBREMIDI_KEYBOARD"]` 把后端宏作为接口信息导出；消费者断言改为「运行期 API 属于 `available_apis()`」 |
| 8 | 链接缺符号 | 需要 pthread/dl/m | `cpp_info.system_libs = ["pthread", "dl", "m"]`（OHOS 与 Linux 同分支） |

## 验证结果

```
conan create archives/l/libremidi/5.4.3 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
CREATE_EXIT:0

ctest --test-dir <build>/Release -N           → Total Tests: 7   （配方内 grep -q 硬校验）
ctest --test-dir <build>/Release --output-on-failure
  1/7 conversion_test .............. Passed   （4 用例 / 164 断言）
  2/7 error_test ................... Passed   （1 用例）
  3/7 midiin_test .................. Passed   （2 用例：1 passed + 1 skipped）
  4/7 midiout_test ................. Passed   （2 用例：1 passed + 1 skipped）
  5/7 midifile_read_test ........... Passed   （4 用例 / 1354 断言，读 33MB 语料）
  6/7 midifile_write_test .......... Passed   （8 用例 / 2 断言）
  7/7 midifile_write_tracks_test ... Passed   （2 用例 / 9 断言）
  100% tests passed out of 7

libremidi consumer checks: 10/10
```

上游 `TEST_CASE` 宏共 24 个；`midi_out.cpp` 的 "sending chunked messages" 整段在
`#if defined(LIBREMIDI_ALSA)` 内，OHOS 无 ALSA 故不注册（23 个注册），其中 2 个 creation
用例在上游 `LIBREMIDI_CI` 模式下 SKIP。全部实际注册的用例 0 失败。

产物：`lib/liblibremidi.a` + `include/libremidi/**` + `licenses/LICENSE.md`，无 `bin/`。
