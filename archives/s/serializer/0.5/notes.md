# serializer 0.5 适配笔记

## 编译环境
- 构建系统: 无（纯头文件库，header-only）
- 编译日期: 2026-09-19
- 目标环境: OpenHarmony PC aarch64
- 工具链: OHOS Clang 15.0.4、CMake 4.1.2、Conan 2.29.1
- 状态: built

## 编译步骤

本地使用官方 `v0.5` 源码归档（SHA-256
`e749ab8ea08623c69f451979ef0d0d8afad6e0652bc8249c9fb214ef7fc6fa5f`，来自官方
GitHub tag v0.5 归档），在 `feat/serializer-0.5` 分支完成配方与测试后按
`./SKILL.md` W3 门禁运行 `conan create` 验证。

```bash
cd /storage/Users/currentUser/zhuo/worktrees/serializer-0.5/archives/s/serializer/0.5
conan create . \
  -pr:h=/storage/Users/currentUser/zhuo/worktrees/serializer-0.5/ci/conan/profiles/ohos-aarch64 \
  -pr:b=/storage/Users/currentUser/zhuo/worktrees/serializer-0.5/ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

配方按 header-only 模板安装 `serializer.h` 与 LICENSE；consumer 测试
`test_package/test.cpp` 以 C++17 编译，覆盖 STL 容器、自定义类与多态往返，
构建和测试按 `-j1` 执行。

## 上游测试清点台账（R51 完整枚举）

官方 v0.5 源码归档完整文件清单（解压后仅 3 个源文件）：

| 文件 | 类型 | 是否测试入口 |
|------|------|-------------|
| serializer.h (89752 B) | 公共头文件（实现全部在内） | 否 |
| README.md | 文档（含代码示例） | 否 |
| LICENSE | MIT 许可 | 否 |

源码包无 tests/ 目录、无 CMakeLists.txt、无 configure / Makefile / meson /
ctest 注册清单 / 测试脚本。枚举命令：

```bash
find . -maxdepth 3 -type f | sort          # 仅上述 3 文件
find . -name "test*" -o -name "*test*"     # 无匹配
grep -rl "TEST\|main(" --include="*.cpp" . # 无 .cpp 文件
```

结论：`source_declared_total = 0`，`configured_executable_total = 0`，
`executed_passed_total = 0`，通过率 0/0 不适用；header-only 库无上游测试，
按 MANIFEST.yml 与上游确无测试证据申报（R51）。

## 消费者验证

`test_package/test.cpp` 通过已安装的公开头文件 `<serializer.h>` 调用公开 API：
- `zpp::serializer::memory_output_archive` / `memory_input_archive` 保存/加载
- STL 容器 `std::vector<int>` 往返
- 自定义类 `point`（`friend access` + 静态 `serialize()`）往返
- 多态 `std::unique_ptr<command>`（注册的派生类）往返与动态类型保持

19 项断言（消费者 test.cpp 5 项 + 鸿蒙专项 ohos_test.cpp 14 项）全部通过，两个程序退出码 0。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连超时 | 本机到 github.com 连接超时，ghfast.top 镜像可达 | 经 ghfast.top 镜像下载官方 tag v0.5 归档（内容与官方一致），核验 SHA-256 与上游一致 |
| 2 | lang-preflight 报 env_unsupported（other/none） | 检测器将 .h 视为中立头文件，纯 .h 库源码统计 total=0，误判为 other | 依据源码实质（`namespace zpp`、模板、C++ 标准头）判定为 cpp 头文件库继续适配，在最终回报中记录该误判证据 |

## 源码修改

无（未改动 serializer.h）。未生成补丁。

## 依赖版本

无 Conan 运行时依赖；仅 C++ 标准库。工具链：OHOS Clang 15.0.4、CMake 4.1.2、Conan 2.29.1。

## 知识路径决定（knowledge-reuse-governance）

完整候选台账、四范围查重与七轴查重见 `reports/knowledge-candidate-ledger.md`。

- 候选 A（lang-preflight 纯 .h 头文件库误判 other/none → env_unsupported）：未命中/部分覆盖
  （既有 DRAFT-debugbreak/emio/exr_image 均为 mixed 误判，无 .h 中立 → total=0 → other 条目），
  已验证、可跨库复用 → **new_draft**，草稿对
  `knowledge/drafts/DRAFT-serializer-0.5-langpreflight-headeronly-h-neutral.kv/.md`（同 stem 配对）。
- 候选 B（W3 junk_check full 模式命中基线垃圾）：与既有草稿
  `DRAFT-libfort-0.4.2-w3-baseline-junk-check-full-scan` 完整重复 → **reuse_existing**，
  本任务按该方案执行基线隔离并记录证据（reports/baseline-isolation-audit.md）。
- 候选 C（GitHub 直连超时→镜像）：E017 既有知识 → **reuse_existing**。
- 候选 D（header-only 配方 G1 方法完整性）：E257 覆盖同族 → **reuse_existing**。

决定：`reuse_existing`（B/C/D）+ `new_draft`（A）→ **路径 B（知识库扩展）**，草稿与
serializer 归档同 PR 交付。
---

**编译结束**: 2026-09-19 22:14
**最终状态**: built
