# DRAFT — aarch64/OHOS 上库生产源码 const char 查找表 -1 哨兵窄化编译失败（-Wc++11-narrowing）

> 状态: 草稿（基于 ifcplusplus 2.5 R01 真实证据，2026-09-18，pc4-25）。
> 配对: DRAFT-ifcplusplus-2.5-aarch64-char-mask-narrowing.kv

## 真实问题（场景）

ifcplusplus 2.5（ifcquery/ifcplusplus，IFC 模型 C++ 库）在 OHOS PC aarch64
（clang 15.0.4, aarch64-linux-ohos, C++17）编译时，库生产源码 `BuildingGuid.cpp`
失败：

```
BuildingGuid.cpp:51:36: error: constant expression evaluates to -1 which cannot be
narrowed to type 'char' [-Wc++11-narrowing]
static const char base16mask[] = { -1, -1, -1, -1, ... };
```

`base16mask[]`/`base64mask[]` 是 GUID 压缩/解压用的 128 项查找表，-1 是"非法字符"
哨兵。aarch64 ABI 使 plain char 默认为 **unsigned**，负值列表初始化在编译期即被
C++11 窄化规则拒绝（x86 上 char 有符号故上游从未触发）。

## 根因

aarch64 plain-char 无符号 → 生产源码 const char 查找表 -1 哨兵 → C++11 列表初始化
编译期窄化失败。与 E419（C 运行时 INT8 结果差异）和 hfsm2 草稿（C++ **测试源码**
窄化）是同一根因族（plain-char 符号性）的不同表现面。

## 与既有知识的差异（查重结论）

| 条目 | 覆盖 | 差异 |
|------|------|------|
| E419 | 部分 | C 运行时 INT8 结果差异（值差 256），修复位 toolchain `-fsigned-char`；本条目是**编译期**失败、**库生产源码**、修复位源码类型 |
| DRAFT-hfsm2-beta73-aarch64-char-narrowing | 部分 | 测试源码窄化 + header-only 测试构建标志；本条目是库生产源码 + 配方内源码补丁 |
| 本条目 | - | 新边界：库生产源码 const char 查找表 -1 哨兵；实证"显式 signed char 类型声明"为最小修复（不动 toolchain 全局符号语义） |

## 方案

**推荐（rec 1）**：源码补丁将语义有符号的 `const char 查找表` 显式声明为
`signed char`（类型语义不变、-1 哨兵保留、无 ABI 变更、不依赖全局编译标志）。
ifcplusplus 实证：`static const char base16mask[]` → `static const signed char
base16mask[]`（base64mask 同理）后 conan create G2 由 FAIL 转 PASS，鸿蒙专项
GUID 往返测试 6 组全部通过。

**回退（rec 2）**：库中大量 plain char 有符号语义且无法逐点改声明时，配方
toolchain 注入 `-fsigned-char`（E419 同法），但需全量复测消费者（全局 char 符号
语义变化）。

## 验证

- 补丁前：`conan create` G2 FAIL（BuildingGuid.cpp 10 处窄化错误）
- 补丁后：`conan create` G2 PASS；test_package 2/2（消费者解析/回写 + GUID 往返）
- 禁止：改哨兵值/测试内强转（掩盖语义）、`__OHOS__` 宏分叉、`-funsigned-char`

## 适用边界 / 反例

- 适用：aarch64/OHOS 编译、生产源码含负值 const char 查找表（协议解析、编码解码、
  字符映射类库）
- 反例：测试源码窄化（走 hfsm2 草稿方案：测试构建标志）；运行时 INT8 结果差异
  （走 E419：toolchain -fsigned-char）；库确有大量有符号 char 语义时优先全局
  -fsigned-char 而非逐点改类型
