# autotools tag 归档（无预生成 configure）的 conan 配方自举

## 问题

libuninameslist 20250714 为 autotools 库，但 GitHub tag 归档
（codeload `tar.gz/refs/tags/20250714`）只含版本控制文件，无预生成
`configure`/`aclocal.m4`/`Makefile.in`。`conan create`（ohos-aarch64 profile 干净构建）
首跑在 build() 阶段报 `configure: inaccessible or not found`（Error 127）。

## 根因

1. tag 归档 = git archive，不含 autoreconf 产物
2. conan create 干净沙箱（USER=100）看不到 `$HOME/.local` 手工安装的 automake
3. `/data/service/hnp/bin` 只有 autoconf 家族（777），无 automake/libtool

## 方案

配方内自举：
- `build_requirements()`：`self.tool_requires("automake/1.18")` +
  `self.tool_requires("libtool/2.5.4")`（制品仓已发布；tool_requires 按 build profile 解析，
  conan create 需同时传 `-pr:h` 与 `-pr:b`）
- `build()`：先 `self.run("autoreconf -i", cwd=self.source_folder, env="conanbuild")`
  生成 configure，再 patch config.guess/config.sub（OHOS，E007/E122）、chmod +x 辅助脚本
  （E490），最后 `Autotools.configure()/make()`
- config.guess/config.sub 的 OHOS 补丁在配方内**纯 Python 内联**实现——conan 构建环境
  PATH 无 perl，`subprocess.run(["perl", ...])` 实测 `FileNotFoundError`

## 验证

修复后 conan-verify 8 道门禁全部 PASS（G1/G0/G2 conan create + test_package
/consume + G3/G4/L2/L4/L5），OHOS 专项测试 7/7 断言 PASS。本机环境同样验证
（同一配方既在本地又在 CI-profile 下可复现）。

## 适用边界

- 适用：上游只发 tag/源码归档、无 release dist tarball 的 autotools 库；
  CI 沙箱不可见用户手工工具的构建环境。
- 反例：上游 release 提供带 configure 的 dist tarball 时应优先用 dist
  （E058/E059 use-stable-release），无需自举；非 autotools 构建系统不适用。

## 查重差异

| 既有条目 | 覆盖部分 | 本条新增 |
|---|---|---|
| E058/E059 | tag 缺 configure → 建议用稳定 release dist | tag 无 dist 时配方内 tool_requires + autoreconf 自举的完整模式 |
| E041/E071 | automake 版本不匹配/环境绕过 | 干净沙箱装配 automake/libtool 的 conan 机制（tool_requires + conanbuild env） |
| E116 | perl @INC 缺失导致 automake 不可运行 | 配方内不得调外部 perl 打 config.guess 补丁（纯 Python 内联） |
| E007/E122/E490 | config.guess/config.sub/脚本权限 | 与自举配合的修复顺序（patch + chmod 在 autoreconf 之后） |

## 关系

- similar_to: E058、E059、E041
- caused_by: 无
- prerequisite_of: 无
- conflicts_with: 无