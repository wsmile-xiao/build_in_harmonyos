# DRAFT-adwaita-icon-theme-50.0.1-meson-resource-alias-materialization - Meson 数据型资源包的 public alias 实体化

- 贡献者: Codex / OpenHarmonyPCDeveloper 适配线程
- 状态: draft，仅作为路径 B / B 类难度候选材料提交评审
- 来源事件: adwaita-icon-theme 50.0.1 由旧 PR 的 CI 反馈触发版本递增后，在 HarmonyOS PC 真机与 CI 规则复查时发现 Meson 仍会跳过资源别名 symlink
- 关联 PR: https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/9128（feat/adwaita-icon-theme-50.0.1）

## 知识类型与提升边界

本草稿属于“数据型包资源布局 + HarmonyOS/HMDFS symlink 能力差异”的组合型经验，面向路径 B / B 类候选沉淀。它不是正式知识图谱条目，不分配正式 E 编号，也不声明已经获得 B 类认定；最终是否提升为正式知识、是否计入 B 类难度，以维护者和赛事评审结论为准。

## 适用场景

- 上游使用 Meson `install_symlink()` 发布公开资源别名，而包本身主要交付 icons、themes、schemas、templates 等数据文件。
- HarmonyOS PC 真机、HMDFS 工作区、Windows destdir 或其他不可靠 symlink 环境中，安装日志出现 `Symlink creation does not work on this platform` / `Skipping all symlinking`。
- 消费者不是链接库，而是按公开文件名查找资源；例如 icon theme 会查找 `folder-open.svg`、XCursor 会查找 `left_ptr`、`hand2`、`xterm`、`watch` 等别名。
- 包已经通过基础文件存在性检查，但仍可能因为 alias 名缺失，在真实桌面/主题消费者中表现为资源回退或样式缺失。

## 问题模型

adwaita-icon-theme 50.0.1 仍是 Meson data-only 项目，本身没有 C/C++ 编译目标。上游安装流程会复制真实资源文件，并额外用 `install_symlink()` 创建若干公开别名：

- `scalable/status/folder-open.svg` 指向 `scalable/places/folder.svg`。
- cursor theme 中 `left_ptr`、`hand2`、`xterm`、`watch` 等公开名称分别指向 `default`、`pointer`、`text`、`wait`。

在 HarmonyOS PC 真机上，Meson 安装阶段会报告 symlink 创建不可用并跳过后续 symlink。若配方只检查 `meson.install()` 退出码或只验证目录存在，包会看起来成功，但公开 alias 名并不完整。Windows 本机 destdir 路径还可能走 win32 cursor 分支，使扩展名为空的 XCursor 源文件没有进入包内，进一步放大资源缺口。

## 推荐处理

1. 保留上游 Meson 安装流程，不在 patch 里硬改全部平台行为。
2. 在 Conan `package()` 的 `meson.install()` 之后执行包内补齐：
   - 对源树中扩展名为空的 cursor 文件，复制到 `share/icons/Adwaita/cursors/`。
   - 对上游公开 symlink alias，若目标名缺失，则把对应源资源复制成普通文件。
   - 对 SVG alias 也执行同样策略，例如把 `folder.svg` 实体化为 `folder-open.svg`。
3. `test_package` 不能只做存在性检查：
   - symlink 存在时校验指向 basename。
   - 普通文件 fallback 存在时校验与源资源字节一致。
   - 用 `PKG_CONFIG_PATH` 验证 dataonly `.pc` 文件仍可被消费端发现。

## 与已有知识的差异

- E050 是通用 “HMDFS symlink 用普通文件替代” 经验，主要描述链接器/库查找失败。本草稿强调 data-only 资源包，消费入口是公开资源文件名而不是 `-l` 或动态加载器。
- E331 面向 CMake VERSION/SOVERSION 共享库 symlink 链，本草稿面向 Meson `install_symlink()` 的 icon/cursor 资源 alias。
- E362 面向依赖包拥有的资源实体化，本草稿中的源资源属于同一个上游 data package，关键校验是 public alias 名与源资源内容一致。

## 禁止做法

- 只忽略 Meson 的 symlink warning，然后把 `conan create` 成功当作交付完成。
- 在 OHOS/HMDFS 上重新 `ln -s` 或 `os.symlink()`，让失败从 Meson 安装阶段转移到配方阶段。
- 只检查 `share/icons/Adwaita` 目录存在，不检查 `folder-open.svg`、`left_ptr` 等公开 alias。
- 只复制任意同名文件，不做源/alias 字节一致校验；这会掩盖错配资源。

## 已验证样例

- 库: `adwaita-icon-theme/50.0.1`
- 分支: `feat/adwaita-icon-theme-50.0.1`
- 适配动作:
  - `conanfile.py` 在 `package()` 阶段将缺失 cursor 源文件、cursor alias、`folder-open.svg` 实体化为普通文件。
  - `test_package.py` 扩展为 20 项消费者断言，覆盖 index、目录、SVG、SVG alias、PNG、cursor 源/alias、pkg-config、license。
- 真机环境:
  - `currentUser@10.62.220.52:2222`
  - HarmonyOS aarch64
  - Conan 2.29.1、Meson 1.11.1、Ninja 1.13.1

## 证据来源

- 本地配方改动: `archives/a/adwaita-icon-theme/50.0/conanfile.py`
- 消费测试: `archives/a/adwaita-icon-theme/50.0/test_package/test_package.py`
- 真机验证记录: `archives/a/adwaita-icon-theme/50.0/notes.md`
