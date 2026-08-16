# cmus 2.12.0 适配笔记

## 编译环境

- 构建系统：cmus 自定义 `configure + GNU Make`
- 目标平台：HarmonyOS PC aarch64
- 编译器：clang/clang++
- 状态：built

## 适配范围

最小可移植配置构建 `cmus`、`cmus-remote`、WAV 输入插件和 CUE 输入插件。音频输出及依赖外部编解码库的可选插件未启用，避免把未验证的硬件或服务接口声明为可用。

## 依赖

- `ncurses/6.5`：宽字符终端界面，静态制品

cmus 的配置检测确认 HarmonyOS libc 已提供可工作的 `iconv`，因此不声明未参与链接的外部 libiconv 依赖。

## 测试

上游 2.12.0 源码没有测试套件，因此上游测试数据实记录为 0。`test_package` 运行实际打包的 `cmus` 和 `cmus-remote`，并要求 `cmus --plugins` 成功加载包内 WAV/CUE 插件，共执行 7 项断言。

```text
upstream: 0 tests
consumer: 7/7 PASS
```

## 知识查重与路径 B

首次查重把相近条目误判为同义覆盖；逐条语义复审后确认，现有 E095 仅处理目标 CXX 被自定义 configure 忽略，E097 是普通自定义 Make 安装，E077/E312 分别处理签名和 Groonga 测试链，均未覆盖“构建时原生生成器与目标产物需要两个编译器上下文”。

cmus 的 `Doc/ttman` 由 `HOSTCC/HOSTLD` 编译并在构建阶段立即运行。配方现将原生构建映射到 `$CC`；真正异构交叉构建仅接受 build profile 或构建工具显式提供的 `CC_FOR_BUILD`，缺失时失败关闭，禁止静默使用目标编译器。通用方案记录为 `knowledge/drafts/E327-draft-912A.{kv,md}`，关联知识库扩展 Issue #2225 和适配 PR #5467。

## 注意事项

`cmus` 使用运行时加载的输入/输出插件。HarmonyOS 包不仅要签名两个可执行文件，还必须签名 `ip/wav.so` 和 `ip/cue.so`，否则插件存在于目录中也不代表能够加载。
---

**编译结束**: 2026-08-16 04:39
**最终状态**: built
