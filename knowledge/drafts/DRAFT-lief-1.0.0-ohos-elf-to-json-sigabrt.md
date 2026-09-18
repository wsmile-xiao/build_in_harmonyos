# DRAFT-lief-1.0.0-ohos-elf-to-json-sigabrt — LIEF to_json() 在 OHOS 静态构建 SIGABRT

## 错误特征

鸿蒙专项测试/消费者调用 LIEF C++ JSON 序列化 API：

```text
$ ./dbg_json small-ohos-elf
before to_json
Signal 6 (core dumped)        # exit 134 (SIGABRT)
```

最小 64 字节 ELF 头、官方 sample（544ca203...elf）与 OHOS SDK 真实二进制（FileCheck，681KB）
均稳定复现。库核心解析 API 不受影响：

```text
$ ./dbg_min small-ohos-elf
step1 read ok 681792 bytes
step2 parse done: ok
step3 class=2 machine=183          # ELF64, AARCH64
step4 sections=29
step5 dynsym=105
step6 exported=2
ALL OK
```

## 触发条件

- 构建系统: CMake，静态库（libLIEF.a），Release
- 平台: OpenHarmony PC aarch64（clang 15，aarch64-unknown-linux-ohos，musl）
- 关键前提: `LIEF_DISABLE_EXCEPTIONS=ON`（LIEF 上游默认，LIEFOptions.cmake:19）——
  异常禁用时 JSON 序列化内部错误处理走 abort 而非抛异常
- API: `LIEF::ELF::to_json(const Object&)`（src/ELF/json_api.cpp），
  经 `JsonVisitor::get()` 到 nlohmann::json 序列化路径

## 根因分析

`src/ELF/json_api.cpp` 在 `LIEF_JSON_SUPPORT`（本构建 config.h 实测 =1）时：

```cpp
std::string to_json(const Object& v) {
  JsonVisitor visitor;
  visitor(v);
  return visitor.get();   // ← 此处 SIGABRT
}
```

`JsonVisitor`（src/ELF/json.cpp）遍历 Binary 各子对象并序列化为 nlohmann::json，
该序列化/内部错误路径在 OHOS aarch64 静态构建（clang15 + 异常禁用）下触发
`abort()`（Signal 6）。与输入样例无关——最短 64 字节 ELF 头即复现，故不是
ELF 解析边界问题，而是 JSON 序列化与平台/构建配置的交互问题。

## 修复/规避

无需源码补丁（核心 API 完全可用）：

1. 消费者/测试仅使用核心解析 API：`Parser::parse`、`header()`、
   `sections()`、`dynamic_symbols()`、`symtab_symbols()` —— 实测全部正常
2. 必须用 to_json 时，以 `LIEF_DISABLE_EXCEPTIONS=OFF` 重建 libLIEF 后再验证

## 验证

- 复现：`dbg_json`/`dbg_json2`（to_json）→ Signal 6 稳定复现（exit 134）
- 对照：`dbg_min`（核心 API）→ 六步全过（exit 0）
- 鸿蒙专项测试：`ohos_specific_test small-ohos-elf` → PASS（不依赖 JSON）
- test_package：conan create 端到端 1/1 通过

## 适用边界

- 适用：OHOS aarch64 + LIEF 1.0.0（1.x 系列待验证）+ 静态库 + 默认异常禁用
- 反例：LIEF 核心解析 API 正常；Linux/其他平台未复现（上游 CI 未报告此问题）

## 查重差异

- 未命中既有条目（index.tsv 无 to_json/JSON-abort 条目）
- 与 E338（getpwuid NULL SIGSEGV）、E246（seccomp SIGSYS）、
  E249（invalid free SIGSEGV）、E365/E409（MPI abort）根因不同，仅 core dumped 关键词面
- similar_to: E338；caused_by/prerequisite_of/conflicts_with: 无

## 来源

- 库: lief/1.0.0（LIEF-1.0.0.tar.gz, sha256 2cf412695ff739d82e129db441e5c2025f3bb4873a3d3a1d3dd4cf300b682abd）
- 任务: lief-1.0.0-r01-pc4-21-20260916T132436Z
- 证据: archives/l/lief/1.0.0/reports/ohos-test-consumer.md、reports/knowledge-candidate-ledger.md