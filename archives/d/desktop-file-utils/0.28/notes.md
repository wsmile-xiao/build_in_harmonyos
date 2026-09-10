# desktop-file-utils 0.28 编译笔记（HarmonyOS PC · 标准 Conan meson）

## 定位
- .desktop 文件工具集：desktop-file-validate / desktop-file-install / update-desktop-database。
- 纯 CLI 工具（package_type: application），无 GUI 依赖。
- 本轮为【知识库扩展】任务（task_id desktop-file-utils-0.28-r01-pc1-2-20260909T170030Z），
  归档已于 5087db5925 合入 main，本轮在既有归档上完成门禁复验 + 鸿蒙专项测试补强 + 知识候选台账。

## 关键适配（沿用既有配方，本轮复验通过）
- **meson 构建**：meson.build 声明 `dependency('glib-2.0', >=2.26)` 与 `dependency('gio-2.0', >=2.26)`，
  均由 conan glib/2.84.0 配方的 PkgConfigDeps 提供。
- **gio-2.0.pc 转发生成**（generate() 中）：glib 配方的 PkgConfigDeps 只生成 glib-2.0.pc
  （cpp_info.libs 合并 glib/gobject/gio），meson 需 `dependency('gio-2.0')` 单独解析 → 生成
  转发型 gio-2.0.pc（Requires: glib-2.0，版本继承）。→ 知识库 E348 已完整覆盖（forwarding-pc-in-generate）。
- **libintl.h 注入**（generate() 中）：OHOS musl 无 gettext 隐式声明，glib 的 `_()` 宏展开报
  -Wint-conversion（20 处）→ 注入**最小 libintl.h 原型声明头**（gettext 家族 9 个函数原型 +
  `__attribute__((__format_arg__))`，写入 generators_folder，经 c_args -I 引入）。
  与既有 DRAFT-ohos-gi18n-gettext-identity-macro（-Dgettext(x)=(x) 恒等宏）触发同源、方案不同：
  原型声明保留真实 gettext 语义（可链接真实 libintl 导出），恒等宏则丢弃翻译。
- **ar/ranlib 注入**（`_inject_meson_archiver`）：OHOS 的 llvm-ar 不在默认 PATH →
  meson configure 报 "Unknown linker(s)"；把 ar/ranlib 全路径写入 conan_meson_native.ini
  的 [binaries] 段。→ 知识库 E296/E481 已覆盖。
- **wrap_mode=nodownload**：禁止 meson 偷偷下载 wrap 子项目，依赖一律走 conan。
- **代码签名**（`_sign_binaries`）：鸿蒙 PC XPM 要求被 exec 的可执行文件代码签名，
  binary-sign-tool 自签 bin/ 下 ELF。→ 知识库 E135/E481 已覆盖。

## 上游测试（完整枚举台账，R51）
| 入口 | 类型 | 是否独立用例 | 结论 |
|------|------|------------|------|
| meson.build | 构建文件 | 否 | 无任何 test() 声明，`ninja test` 为空 |
| src/*.c（install/validate/mimeutils/keyfileutils/update-desktop-database/validator） | 源码 | 否 | 工具实现，非测试 |
| man/ | 文档 | 否 | man 页 |
| misc/（desktop-entry-mode.el） | 杂项 | 否 | Emacs 模式文件 |
| .gitlab-ci.yml | CI 脚本 | 否 | 上游 CI 仅 `ninja -C _build test`（空测试） |
- **上游测试声明总数 = 0**（全量枚举：28 个文件，无 test/ 目录、无 test() 目标、无测试脚本）。
- 通过率口径：0/0 不适用；以 test_package 消费者 + 鸿蒙专项补强作为实际验证。

## 鸿蒙专项测试（本轮补强，真实执行）
- test_package/test.c 扩展为三段真实业务验证（fork+exec，无 shell 注入，临时文件写入 $TMPDIR 或当前目录）：
  - OK-A: `desktop-file-validate --version` → stdout 含 "0.28"
  - OK-B: 合法 .desktop 文件校验 → exit 0
  - OK-C: 非法 .desktop 文件（缺 [Desktop Entry] 组头）校验 → exit 1（非零）
- W3 conan create 复验：exit=0，OK-A/OK-B/OK-C 全部通过（见 w3-conan-create-r2.log）。
- 消费者硬门禁：test_package 通过已安装 bin/desktop-file-validate 的公开 CLI 调用公开功能，
  非空壳（真实校验业务语义 + 可观察退出码）。

## 依赖版本
- glib-2.0/gio-2.0: 2.84.0（conan glib/2.84.0 配方，registry 已发布，R35 用 conan download 实证）

## 知识候选台账（knowledge_candidate_ledger）
| 候选 | 现象/根因 | 修复 | 验证 | 四范围查重 | 决定 |
|------|----------|------|------|-----------|------|
| K1 gio-2.0.pc 转发 | meson dependency('gio-2.0') 找不到 .pc | generate() 生成转发型 .pc | conan create 通过 | E348 exact_duplicate | 复用 |
| K2 libintl.h 原型注入 | musl 无 gettext 原型，_() 宏 -Wint-conversion | 注入最小 libintl.h 声明头 | conan create 通过 | DRAFT-gi18n 触发同源/方案不同，新增差异 | 路径 B 草稿 |
| K3 ar/ranlib 注入 | llvm-ar 不在 PATH，meson Unknown linker | native.ini 注入全路径 | conan create 通过 | E296/E481 solution_overlap | 复用 |
| K4 ELF 签名 | XPM 要求可执行文件签名 | binary-sign-tool 自签 | conan create 运行通过 | E135/E481 solution_overlap | 复用 |

## 状态
built（CI conan create + test 通过，本轮复验 exit=0）
---

**编译结束**: 2026-09-10 01:27
**最终状态**: built
