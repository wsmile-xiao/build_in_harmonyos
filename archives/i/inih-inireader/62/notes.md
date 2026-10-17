# inih-inireader 62 适配笔记

## 编译环境
- 构建系统: 上游 Meson；本仓库直接编译（custom）
- 编译日期: 2026-09-15
- 编译器: OHOS clang（Conan profile `ohos-aarch64`）
- 状态: built

## 版本与源码
- 任务版本 `62` 对应上游 git tag `r62`（上游用带 `r` 前缀的 tag）。
- 源码：`https://github.com/benhoyt/inih/archive/refs/tags/r62.tar.gz`
  sha256 `9c15fa751bb8093d042dae1b9f125eb45198c32c6704cd5481ccde460d4f8151`。
- 该版本同时提供 C 解析器（`ini.c`/`ini.h`）与 C++ `INIReader`（`cpp/`）。

## 编译步骤

上游用 Meson 生成 `libinih` 与 `libINIReader`。本机不引入 Meson，直接编译两个
翻译单元，产物与上游一致：

1. `clang -c -O2 ini.c -o ini.o`
2. `llvm-ar rcs libinih.a ini.o`
3. `clang++ -c -O2 -std=c++11 -I. -Icpp cpp/INIReader.cpp -o INIReader.o`
4. `llvm-ar rcs libINIReader.a INIReader.o`

`package()` 安装 `ini.h`、`INIReader.h` 到 `include/`，两个 `.a` 到 `lib/`，
`LICENSE.txt` 到 `licenses/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游是 Meson 工程，本机无 Meson | worker 未装 Meson | 直接编译两个源文件，安装头文件与静态库 |
| 2 | `INIReader.cpp` 以 `../ini.h` 引用 C 头 | 源码相对路径 | 编译时加 `-I <src> -I <src>/cpp`；`INIReader.h` 本身只含标准库头，可平铺安装 |
| 3 | 静态链接顺序 | `INIReader` 依赖 `inih` 的符号 | `cpp_info.libs = ["INIReader", "inih"]` |
| 4 | 消费者测试需同时用 C 与 C++ API | 两套头文件 | `test_inih_inireader.cpp` 同时 include `<ini.h>` 与 `<INIReader.h>`，链接两个库 |

## 源码修改

无补丁（`patches/` 为空）。上游代码在 OHOS/aarch64 上直接可编译。

## 依赖版本

无外部依赖。

## 验证结果

```bash
# 消费者测试（C + C++ API）
./test_inih_inireader
# -> inih-inireader consumer test PASS (13 checks)

# 上游官方测试
#   15 组 tests/unittest.sh 变体 -> 与 baseline_*.txt 逐字节一致
#   2 个 examples/INIReader*     -> 与 cpptest.txt / cpptesterrors.txt 一致
```

`conan create inih-inireader/62` 退出码 0。

## 注意事项

- 上游 tag 带 `r` 前缀（r62），Conan 版本按平台任务填 `62`。
- 本库同时是 C 与 C++ 接口，消费者按需链接；CMake 目标为
  `inih-inireader::inih-inireader`。
