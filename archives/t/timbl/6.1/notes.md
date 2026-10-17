# timbl 6.1 适配笔记

## 编译环境
- 构建系统: custom (manual build bypassing autotools, since automake is not available on OHOS)
- 编译日期: 2026-09-05
- 编译器: clang/clang++
- 状态: built

## 编译步骤

由于 OHOS 平台没有 automake/autoreconf，无法运行标准的 `./configure` 流程。采用手动编译方式：

1. 生成 config.h（模拟 configure 的输出，定义必要的宏）
2. 使用 clang++ 直接编译 26 个 C++ 源文件（lib_sources）
3. 使用 llvm-ar 创建静态库 libTimbl.a
4. 编译 Timbl 和 TimblClient 可执行文件，链接 libTimbl.a

关键编译参数：
- 从 conanbuild.conf 读取 CXX/CXXFLAGS/LDFLAGS/AR
- 附加 `-include sys/time.h -include iomanip` 解决 timeval 和 setw/setfill 的头文件依赖

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 失败 (exit 127) | automake/autoreconf 在 OHOS 上不可用 | 手动生成 config.h，绕过 autotools |
| 2 | timeval 类型未定义 | OHOS 头文件依赖关系不同 | cxxflags 追加 `-include sys/time.h` |
| 3 | setw/setfill 未定义 | iomanip 未被自动包含 | cxxflags 追加 `-include iomanip` |

## 源码修改

无补丁。所有适配通过 conanfile.py 的 build() 方法中的编译参数解决。

## 依赖版本

无外部 conan 依赖。仅链接系统库 pthread。

## 验证结果

```bash
conan create archives/t/timbl/6.1 -pr=ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# → PASS: 26 C++ source files compiled, libTimbl.a created, Timbl/TimblClient binaries created
# → test_package: TimblAPI object created successfully
```

## 交付物

| 文件 | 说明 |
|------|------|
| libTimbl.a | 静态库 |
| Timbl | 命令行工具 |
| TimblClient | 客户端工具 |

## 注意事项

- conanfile.py 使用 AutotoolsToolchain 生成编译器配置，但 build() 方法手动调用 clang++ 编译
- config.h 由 _generate_config_h() 方法生成，模拟 autotools configure 的输出
- OHOS 平台需要额外包含 sys/time.h 和 iomanip 头文件

---

**编译结束**: 2026-09-05 08:16
**最终状态**: built
