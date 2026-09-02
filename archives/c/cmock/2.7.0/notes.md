# cmock 2.7.0 适配笔记

## 编译环境

- 构建系统：Meson 1.12.0
- 编译器：HarmonyOS clang/clang++ 15.0.4
- 目标：HarmonyOS PC arm64（Conan `os=OHOS`）
- 状态：built

## 源码与依赖

- 官方源码：`https://github.com/ThrowTheSwitch/CMock/archive/refs/tags/v2.7.0.tar.gz`
- CMock SHA256：`d96282cf0286682f7628afc31cf2e3ed6ecb66944d63e098824d98196904f04c`
- Unity 源码：`https://github.com/ThrowTheSwitch/Unity/archive/refs/tags/v2.7.0.tar.gz`
- Unity SHA256：`e84eb301ca7967831e68b1728f911e87fa2d345d8ddb64f897bc2f2ee24a321c`
- CMock 2.7.0 的发布压缩包不包含 Unity 子模块内容；配方在 `source()` 中下载并固定 Unity 2.7.0 到 `vendor/unity`，因此不依赖未发布的外部 Conan Unity 包。

## 关键适配

- 通过 Meson 构建 CMock runtime 和 Unity runtime 两个静态库，关闭网络 subproject 下载：`default_library=static`、`wrap_mode=nodownload`。
- OHOS SDK 的 `llvm-ar` 按 Meson 生成的 `csrDT` 参数会产生 thin archive。此类归档引用构建目录中的对象文件，安装到 Conan 包后无法被链接器读取；配方在构建完成后用同一对象文件重建普通 LLVM 静态归档，再进行打包。
- 未修改上游源码，未生成补丁。

## 验证结果

上游完整测试使用：

```text
rake -f test/rakefile config[clang_ohos.yml] test:all
```

- Ruby 单元测试：352/352，通过 592 个断言。
- C runtime 测试：15/15。
- system interaction 测试：446/446。
- system compilation 测试：5/5。
- 上游合计：818/818，失败 0。
- Conan `test_package`：CMake 配置、编译、CTest 和消费者程序均通过；消费者实际调用 CMock runtime 的分配、读取、释放和复位 API。

配方门禁命令：

```text
python3 scripts/ohc-run.py conan-verify cmock 2.7.0
```

结果：G1、G2、G3、产物完整性、L2、L4、L5 全部通过。

## 注意事项

- Conan 包同时提供 `libcmock.a` 和 `libunity.a`，CMake target 为 `cmock::cmock`。
- 包含目录提供 CMock 头文件以及 `include/unity/` 下的 Unity 头文件；许可证包含 CMock 和 Unity 两份文本。
---

**编译结束**: 2026-09-02 14:18
**最终状态**: built
