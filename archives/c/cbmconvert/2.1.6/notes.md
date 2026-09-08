# cbmconvert 2.1.6 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt，无 configure）
- 编译日期: 2026-09-06
- 编译器: clang 15.0.4（OHOS aarch64 原生）
- 状态: built

## 编译步骤

```bash
# as-is 探索（设备，源码包 SHA256 见 conandata.yml）
cmake -B b -DCMAKE_BUILD_TYPE=Release
cmake --build b -j2
ctest --test-dir b                 # 官方 6 用例套件
```

配方内 generate() 设 `CMAKE_SYSTEM_NAME=Linux`、`CMAKE_SYSTEM_PROCESSOR=aarch64`
（CMake 无 OHOS 平台模块，参照已合入的 abcmidi 配方模式），`BUILD_TESTING=True`
并在 build() 中执行 cmake.test()，使上游官方套件在 CI 同样实跑。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 无法识别 OHOS 平台 | CMake 官方无 OHOS 模块 | 工具链设 CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64（可移植 C，无平台专属 API） |

## 源码修改

无补丁。

## 依赖版本

无依赖（纯 C + libc）。

## 验证结果

```bash
$ ctest --test-dir b              # 官方套件，设备实测 2026-09-06
100% tests passed, 0 tests failed out of 6
# rc=0；含 3 个 WILL_FAIL usage 用例与 3 个真实转换管线用例
# (empty_files / small_files / file_names)
```

- 上游静态用例总数：6（CMakeLists.txt 中 6 个 ADD_TEST，静态逐个计数）
- 实际执行：6；通过：6；失败：0；跳过：0
- 消费者测试（test_package/test.sh）：4 组断言（usage 横幅+非零退出、
  -D4 真实创建 D64 并断言 174848 字节、-L 回转 Lynx 归档非空、
  disk2zip/zip2disk 存在且 usage 退出非零），4/4 通过

## 注意事项

- 产物为三个命令行工具（cbmconvert / zip2disk / disk2zip），软件级
  `commands.json` 按 R38 声明，主名称 cbmconvert。
- 上游 usage 用例为 WILL_FAIL（期望非零退出），语义与 OHOS 行为一致，
  消费者测试中按同口径断言非零退出。
---

**编译结束**: 2026-09-06 02:50
**最终状态**: built
