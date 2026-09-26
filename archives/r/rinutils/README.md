# rinutils

C11 / gnu11 头文件工具库（Shlomi Fish）：sizeof 感知的 `malloc`/`realloc` 包装、
`COUNT()`/`LAST()`、`DLLEXPORT`、`likely()`/`unlikely()`、`long long` 格式化宏、
`min()`/`max()`、`portable_time.h` 跨平台时间、字符串工具、`typeof_wrap.h`、
`GCC_UNUSED`、`rin_cmocka.h`（cmocka 样板）。

- 上游：https://github.com/shlomif/rinutils
- 许可：MIT
- 构建系统：CMake（header-only，无编译产物）
- 适配版本：0.10.3（HarmonyOS PC / aarch64，OHOS SDK clang 15）

## 安装内容

| 路径 | 说明 |
|------|------|
| `include/rinutils/*.h` | 14 个头文件 |
| `lib/pkgconfig/librinutils.pc` | pkg-config 元数据（上游文件名为 `librinutils.pc`；Conan 消费者的 pc 名为 `rinutils`） |
| `lib/cmake/Rinutils/` | CMake 包配置（`RinutilsConfig.cmake`） |
| `licenses/LICENSE` | MIT 许可证原文 |

## 适配说明

- **离线可复现**：上游 configure 期会从 GitHub `FILE(DOWNLOAD)`
  `cmake/Shlomif_Common.cmake` 并强制要求 perl。适配内置该模块的裁剪副本
  （仅保留 CMakeLists 用到的宏，保留 MIT 版权），并把下载分支改为
  `FATAL_ERROR`（补丁 0001/0002）。
- **上游测试**：cmocka C 用例 `t/bit-reader-and-writer-test.c` 在 `conan create`
  的 `build()` 中真实编译执行（cmocka 为 `test_requires`）；其余 7 个 Perl
  用例依赖 CPAN 工具链（其中 4 个使用 `Inline::C` 现场编译），OHOS 上不可运行，逐项技术原因见版本目录
  `notes.md` 与 `reports/test-report.md`。
- **鸿蒙消费者测试**：`test_package/` 内置 36 项运行时断言（含负向用例），
  覆盖 13 个头文件的 API 行为。

## 使用（Conan 2）

```bash
conan install --requires=rinutils/0.10.3 -r=ohpcd --build=missing
```

CMake 消费者：

```cmake
find_package(Rinutils REQUIRED)
target_link_libraries(app PRIVATE Rinutils::Rinutils)
```

pkg-config 消费者（上游安装的 pc 文件）：

```bash
pkg-config --cflags --libs librinutils
```
