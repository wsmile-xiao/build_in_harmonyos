# libdbusmenu-gtk3 16.04.0 HarmonyOS adaptation notes

## Scope

- 任务: 智能任务平台 contrib-13120（认领人 Sy444，2026-09-29 认领）
- 分支: `feat/libdbusmenu-gtk3-16.04.0`（以平台显示为准）
- Package path: `archives/l/libdbusmenu-gtk3/16.04.0`
- 目标: 路径 B（【知识库扩展】）——上游测试体系强依赖 dbus-test-runner / Xvfb，
  属"测试框架未鸿蒙化 + 平台差异"两类问题，拟沉淀通用知识库草稿

## W0 dependency check

上游 configure.ac 直接依赖（`--with-gtk=3` 布局）：

| 上游要求 | Conan 依赖 | 制品仓状态 |
|---|---|---|
| glib-2.0 / gio-2.0 / gio-unix-2.0 >= 2.35.4 | glib/2.84.0.1 | published（gtk3 生态 pin 版本，依赖项 PR #6118 系） |
| gtk+-3.0 >= 2.91 | gtk/3.24.43 | published（broadway 后端，无 X11/Wayland） |
| json-glib-1.0 >= 0.13.4（仅 tests/） | json-glib/1.10.6 | published（其配方 pin glib/2.84.0.1，无版本冲突） |

- 16.04.0 的 libdbusmenu-glib 已使用 **GDBus (gio)**，`#include <gio/gio.h>`，
  不依赖 dbus-glib。
- **dbus/1.14.10.2 不进配方依赖图**：它绑 glib/2.88.3，与 gtk3 生态的
  glib/2.84.0.1 冲突（R36）；它以 tool 形态归档（bin/ 含 dbus-daemon、
  dbus-run-session），仅在测试期提供会话总线。
- W0b（相邻版本核验）：libdbusmenu 无历史归档；glib 构建工具（glib-mkenums）
  按 gtk/3.24.43 的 wrapper 模式处理（host glib 包 bin/ + python 绝对路径 wrapper）。
- intltool 0.51.0 在 archives/i/intltool 存在但状态仅 `built`（未发布制品仓），
  不能 tool_requires——改为补丁 0003 将 intltool/perl 检查降级为告警并去掉 po/。
- 查重：upstream archives 无任何 libdbusmenu*（git ls-tree + 本地扫描双查）；
  ohpcd 制品仓同版本查询需登录（Windows 无凭据），**留待真机阶段用
  `conan download libdbusmenu-gtk3/16.04.0 -r=ohpcd --only-recipe` 复核（L0j）**。

## Source and build-system analysis

- 源码: `https://launchpad.net/libdbusmenu/16.04/16.04.0/+download/libdbusmenu-16.04.0.tar.gz`
- sha256: `b9cc4a2acd74509435892823607d966d424bd9ad5d0b00938f27240a1bfa878a`
- 构建系统: autotools 发行 tarball（configure 已生成，2015 年代 config.guess/sub）
- 产物: libdbusmenu-glib.so（dbusmenu-glib-0.4.pc）+ libdbusmenu-gtk3.so（dbusmenu-gtk3-0.4.pc）
- 头文件安装布局: `include/libdbusmenu-glib-0.4/libdbusmenu-glib/`、
  `include/libdbusmenu-gtk3-0.4/libdbusmenu-gtk/`（gtk 库 VER=3 变体）

## 上游测试体系（路径 B 核心）

`tests/Makefile.am` 的 TESTS（automake 并行 harness，test-driver）：

- **glib 子集（8 个）**：test-glib-{objects-test,events,events-nogroup,layout,
  properties,proxy,simple-items,submenu}——均为"dbus-test-runner --task gtester
  --parameter …"包装脚本，需要 **D-Bus session bus**。
- **gtk 子集（5 个）**：test-gtk-{objects-test,label,shortcut,reorder,remove}
  ——额外经 `run-xvfb.sh` 需要 **X display**；OHOS 无 X server，gtk3 为
  broadway 后端，无 headless 通道。
- test-json：`if WANT_DBUSMENUDUMPER if HAVE_VALGRIND` 双重门控——dumper
  已禁用（gtk2+x11 不可用），valgrind 亦不在 OHOS 工具链，该测试上游即不实例化。
- PYTHON_TESTS（GI）上游注释明确只在系统安装副本上有效，上游本身不跑。

**适配策略**（glib 子集）：
1. dbus-test-runner 未鸿蒙化且制品仓无——build() 生成 shim
   `.dbus-test-runner-shim/dbus-test-runner`，把
   `--task gtester --task-name test --parameter …` 翻译为
   `dbus-run-session -- gtester …`（单任务形式，全部 libdbusmenu 测试符合；
   参数不含空格——本仓路径满足）。
2. dbus-run-session 来自 dbus/1.14.10.2 tool 包 bin/：真机执行前需
   `conan install --requires dbus/1.14.10.2 …` 并把其 bin/ 放进 PATH
   （配方对缺失输出明确 warning 并跳过，不伪造通过）。
3. gtester 来自 glib 包 bin/（真机核验项）。
4. 运行 `make -j1 check TESTS='<8 个 glib 测试>'`。

**gtk 子集（5 个）**：无法在 OHOS 运行（无 X display）——平台差异，
进路径 B 测试报告；不修改测试、不伪造结果。

## Patches

| # | 文件 | 内容 |
|---|---|---|
| 0001 | config.guess | 增加 `*:HarmonyOS:*` 分支输出 `aarch64-unknown-linux-ohos`（2015 年代格式） |
| 0002 | config.sub | maybe_os 拆分表与 OS 校验表接受 `linux-ohos` |
| 0003 | configure + Makefile.am | intltool-update / perl 检查 as_fn_error→WARNING；ac_config_files 去 po/Makefile.in；SUBDIRS 去 po |
| 0004 | tests/Makefile.am + .in | 20 处 wrapper 生成 `#!/bin/bash`→`#!/system/bin/sh`；DBUS_RUNNER 后加 `LOG_COMPILER = $(SHELL)`（直接 shebang 执行被拒）；测试 CFLAGS 去 -Werror（2016 老代码对 glib 2.84 废弃 API 告警） |

全部补丁已对 pristine tarball 通过 `git apply --check`。

## test_package（消费者用例）

`test_libdbusmenu.c`：14 断言，真实链接 dbusmenu-glib，调用公开 API——
建树（new_with_id/child_append/get_children/get_parent）、属性读写
（property_set/get/get_bool，含缺失键默认值 NULL）、按 id 查找
（find_id/child_find）。纯 GObject 数据结构操作，不需要 session bus。

## 留给 MateBook（真机）的验证项

1. `conan download libdbusmenu-gtk3/16.04.0 -r=ohpcd --only-recipe` → 预期 404（L0j 查重②）
2. `conan create`（按仓库现行 SKILL.md 与 ohos-aarch64 profile）
   - 关注：glib-mkenums wrapper 是否被 AC_PATH_PROG 命中；
   - intltool 降级告警后 configure 是否还有其余硬失败；
   - json-glib 链接是否只进 tests（不污染库依赖）。
3. dbus/1.14.10.2 tool 的 bin/ 入 PATH 后跑 glib 测试子集；
   记录 dbus-run-session 下 8 个测试的实际通过情况（gtester 位置：glib 包 bin/）
4. test_package 消费者测试（conan test）
5. finish → `.ci-result.json` → W4 审计（pre_pr_audit.py，P0/P1 清零）
6. 路径 B 知识库草稿（真机复现后写）：拟两条候选
   - "Launchpad dbus-test-runner 测试体系 → dbus-run-session 等价替换"
     （通用类：libdbusmenu、indicator-*、ayatana 生态同构）
   - "Xvfb/display 依赖的 GTK 测试在无 X server 目标上的处理口径"
   - 草稿提交 `knowledge/drafts/`（kv+md 成对），经复审入库

## 风险与未定项

- gtester 是否在 glib/2.84.0.1 包 bin/：未在本机核验（真机项 3）
- broadway 后端下 gtk 测试即使给 display 也不等效（Xvfb 替代不存在），
  报告里如实写"无法运行"而非"跳过"
- dbus-run-session 的 -- 参数形式 shim 未在真机实测（真机项 3）
- 上游 16.04.0 是 2016 年代码，glib 2.84 下废弃 API 告警可能触发 -Werror？
  configure 无 -Werror（W0 已确认未设置），若真机出现再处理

### 对话 #1（真机验证，2026-09-30）

- configure 参数：--with-gtk=3 --disable-dumper --disable-gtk-doc
  --disable-introspection --disable-vala（vala default=auto 会因 introspection
  关闭而报错）
- 耗时：单次完整 conan create 约 12–14 分钟（configure ~2min，make -j1 ~6min，
  glib 子集测试 ~4min，test_package ~1min）
- 编译结果：glib+gtk3 双库编译链接通过；上游测试 8/8 PASS；消费者测试 14/14；
  W3 门禁 100%
- 遇到的问题：见"真机验证记录"的「真机修复（回写内容）」条（上游 child_find 缺陷，补丁 0005 修复）

## 真机验证记录（MateBook，2026-09-30）

- conan create（conan 2.29.1，profile ci/conan/profiles/ohos-aarch64）：**RC=0**
- glib 子集 8/8 全部 PASS（test-glib-objects-test / events / events-nogroup /
  layout / properties / proxy / simple-items / submenu），gtester XML status=0。
  会话总线由 dbus/1.14.10.2 工具包 dbus-run-session + 匿名 TCP 会话配置提供
  （OHOS 无 passwd 数据库，EXTERNAL 认证不可用；该工具包不进依赖图）。
- gtk 子集 5 个无法运行：无 X server，gtk/3.24.43 为 broadway 后端，
  gtk_init 无法初始化 —— 平台差异，按路径 B 口径记录，非失败项。
- 消费者测试 test_libdbusmenu：14/14 断言 PASS（conan create test() RC=0，
  conan test RC=0）。
- 真机修复（回写内容）：新增补丁 0005 —— 上游 dbusmenu_menuitem_child_find
  循环条件写反（childs == NULL 应为 != NULL），非空子列表恒返回 NULL，
  消费者测试 child_find 断言暴露，patch_ng(fuzz=False) 对 pristine 验证通过。
- W3 本地 CI 模拟（finish Step5）：PASS，1/1 包，通过率 100%，
  .ci-result.json 由工具写入（W3_local_ci, exit 0）。
### 对话 #2（CI 第 1 轮，2026-09-30）

- CI #65574/#65633：worker fork-OOM 基础设施故障（git-clone 前即死，配方未执行），
  与提交内容无关；#65661 worker 恢复后首跑
- #65661：L0 全门禁通过（含 L0j 权威确认 version not in registry yet, first publish）、
  KC/JC 通过、补丁 5/5 应用、依赖图 22 包全部解析下载；configure 首个真实错误：
  `XML::Parser perl module is required for intltool`——CI worker hnp perl 5.42.0
  无 XML::Parser 模块；MateBook 的 perl 带该模块故真机未复现（CI/真机环境差异）
- 修复：0003 扩充——XML::Parser 检查降级为 WARNING（与 intltool-update/perl 降级
  同族逻辑：NLS 不在范围，po/ 已移除故 intltool-merge 不会运行）；
  全序列已对 pristine tarball 通过 git apply 校验

### 配方修复轮（2026-09-30，CI 前置预警）

- 第 3 轮真机复验（549ed14de）全绿，但绿跑依赖机器级
  PKG_CONFIG_PATH=~/tmp/mtest/stub-pc（手工 gio-unix-2.0.pc 聚合 shim），
  配方不提供该环境 → CI 修完 XML::Parser 后将在 DBUSMENUTESTS 探针
  撞 `No package 'gio-unix-2.0' found`（configure 硬错误，要求
  json-glib-1.0 >= 0.13.4 与 gio-unix-2.0 >= 2.24）
- 修复：conanfile build() 新增 _stage_gio_unix_pc_shim()——生成
  Requires: gio-2.0 的聚合 pc shim 并前置 PKG_CONFIG_PATH；glib 包与
  conan 合成 pc 集均无 gio-unix-2.0.pc（仅 glib-2.0/gio-2.0/gobject-2.0）；
  gio-unix 头与 gio 同一 include 树，无桩头文件/桩库引入
---

**编译结束**: 2026-10-03 20:51
**最终状态**: built
