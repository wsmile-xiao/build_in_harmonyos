# nemo-image 6.6.0 适配笔记（HarmonyOS PC / arm64）

## 编译环境
- 构建系统: clang 直构（上游为 meson，因 libnemo-extension pkg-config 依赖不可满足而改为配方内直接驱动 clang，见下）
- 编译日期: 2026-09-09
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，native OHOS arm64）
- profile: ohos-aarch64（os=OHOS arch=armv8 compiler=clang-15 libc++ Release）
- 状态: built（本地 conan create + conan-verify 8 门禁全 PASS）

## 上游身份核验（rule4，全网穷尽检索）
- 任务名 nemo-image/6.6.0。全网（GitHub/GitLab/Codeberg/Gitee/Debian/Fedora/
  Arch/Alpine/NixOS/Homebrew/Launchpad/Flathub/repology/FreeBSD ports/Linux
  Mint 官方源）不存在名为 nemo-image 6.6.0 的独立项目。
- 唯一 6.6.0 匹配：linuxmint/nemo-extensions 6.6.0 tag（2025-11-25 全组件
  统一发版，debian/changelog 实证 nemo-image-converter (6.6.0) zena）中的
  nemo-image-converter 组件。任务清单惯用截断名/发行版名（ncdu2/minizign/
  ninja-build 先例），故认定上游 = nemo-image-converter。
- 描述勘误：该组件是 Nemo 文件管理器的【图像缩放/旋转上下文菜单扩展】，
  非独立图像查看器；构建产物为扩展模块 .so，由 Nemo 宿主 dlopen。

## 软件与产物
Nemo 扩展（C，GPL-2.0-or-later，1093 行源码，4 .c + 2 .ui）：
- `lib/nemo/extensions-3.0/libnemo-image-converter.so` — 扩展模块
  （nemo_module_initialize/list_types/shutdown 三入口 +
  NemoImageConverter GType，实现 NemoMenuProvider/NemoNameAndDescProvider
  接口，为图像文件追加 Resize Images / Rotate Images 右键菜单）
- `lib/libnemo-extension.so(.1)` — vendored Nemo 扩展 ABI 库精简子集
  （上游位于 nemo 主包源码树，独立 ABI 库 version 1.4.0，仅依赖 glib+gtk；
  5 个 .c 恰好覆盖本扩展调用的全部符号，45 个 T 符号）
- `include/libnemo-extension/*.h` — ABI 子集公共头（8 个）
- `share/nemo-image-converter/*.ui` — 上游 resize/rotate 对话框 GtkBuilder 定义

## 编译步骤（探索 + 配方固化）
依赖：`gtk/3.24.43`、`glib/2.84.0.1`（ohpcd 已发布预编译二进制；gtk 闭包
pin glib/2.84.0.1，顶层声明同版本避免冲突重建，pioneers 先例）。

```bash
# 探索（模式 B）关键命令（~/tmp/builds 与 TMPDIR/builds 双轨验证）
# 1) vendored libnemo-extension（从 nemo-6.6.0 tarball 提取精简子集）
for f in nemo-file-info.c nemo-menu.c nemo-menu-item.c \
         nemo-menu-provider.c nemo-name-and-desc-provider.c; do
  clang -c libnemo-extension/$f -Iinclude -Iinclude/libnemo-extension \
    -DHAVE_CONFIG_H $(pkg-config --cflags glib-2.0 gio-2.0 gobject-2.0 gtk+-3.0) \
    -fPIC -O2 -Wno-deprecated-declarations -o ext_${f%.c}.o
done
clang -shared -o libnemo-extension.so ext_*.o \
  $(pkg-config --libs glib-2.0 gobject-2.0 gio-2.0 gtk+-3.0) \
  -Wl,-soname,libnemo-extension.so.1 -lm
# 2) 扩展模块（nemo-extensions-6.6.0 tarball 的 nemo-image-converter/src）
clang -shared -o libnemo-image-converter.so conv_*.o \
  libnemo-extension.so <glib>/lib/libintl.so \
  $(pkg-config --libs gtk+-3.0 glib-2.0) \
  -Wl,-soname,libnemo-image-converter.so
```

配方（conanfile.py）固化：source() 双 get（abletonlink/asio conandata
自定义键先例：主源 nemo-extensions tag + nemo_extension_sources 键 nemo
tag）→ generate() PkgConfigDeps+VirtualRunEnv+CC 注入（R33）→ build()
生成 OHOS 适配 config.h + 展开 clang 命令序列 → package() 按
extensiondir 布局收集。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 依赖 libnemo-extension pkg-config 不存在 | 制品仓无 nemo/libnemo-extension 包（nemo 主包未适配，且其主程序依赖 cinnamon-desktop/xapp/tracker 深链） | 不走 meson；vendored libnemo-extension 精简源码（上游子目录本身仅依赖 glib+gtk，可独立编译）+ clang 直构 |
| 2 | g_libintl_bindtextdomain 未定义符号 | image-converter.c 无条件调 bindtextdomain；glib 包的 proxy libintl 把它映射为 g_libintl_*（glib-2.0.pc 不携带） | 链接 <glib>/lib/libintl.so（pioneers/avahi-ui-tools 先例） |
| 3 | G_TYPE_INSTANCE_GET_PRIVATE deprecated 警告 | 上游用旧式 GObject 私有数据宏 | -Wno-deprecated-declarations（不改上游源码） |
| 4 | NLS 工具链缺失 | OHOS 无 gettext/intltool | 适配 config.h 不定义 ENABLE_NLS，nemo-extension-i18n.h 退化为 no-op |
| 5 | GNOMELOCALEDIR/DATADIR 未定义 | 原 meson configure_file 生成 config.h 提供这些宏 | 配方内生成等价 config.h（GETTEXT_PACKAGE/PACKAGE/GNOMELOCALEDIR/NEMO_VERSION_* 全套） |
| 6 | g_module_open 报 libc++_shared.so 缺失 | gtk OHOS 闭包 NEEDED 系统 libc++_shared.so（/system/lib64） | test 运行时 LD_LIBRARY_PATH 追加 /system/lib64 |
| 7 | HMFS shell 环境 source 丢失/循环不稳 | HMFS bash getcwd 故障 + 子进程环境不稳 | build() 内写 ohos_build.sh（显式 cd + 绝对路径 source generators 下 env 文件）后 sh 执行；命令序列展开不用 for 循环 |
| 8 | worktree 出现他人脏文件 | 主仓库多会话共享 + HMDFS stat 异常 | 提交严格限定 `git add archives/n/nemo-image/`（多会话纪律） |

源码修改：**无归档补丁**（patches/ 为空）。所有 OHOS 适配均为 conanfile.py
build() 内确定性动作（config.h 生成 + clang 命令），随 conan create 可复现。

## 依赖版本

| 包 | 版本 | 说明 |
|----|------|------|
| gtk | 3.24.43 | 已发布 shared 二进制；闭包 pin glib/2.84.0.1 |
| glib | 2.84.0.1 | gtk 闭包对齐；proxy libintl 由本包链接 |
| gdk-pixbuf/cairo/pango/atk/... | 传递 | gtk requires 自动拉取（制品仓预编译） |

## 验证结果

```bash
conan create archives/n/nemo-image/6.6.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
#   → EXIT 0；HMBS_TEST_PACKAGE_RESULT {"discovered":10,"passed":10}
conan-verify nemo-image 6.6.0   # G0-G4/L2/L4/L5 全 PASS
```

### 测试用例（积分赛补全口径，上游 N=0 → 适配后 10 条实断言）

| 分类 | 条数 | 内容 |
|------|------|------|
| 契约冒烟（GModule 真实加载） | 4 | g_module_open 扩展模块（验证 libnemo-extension.so.1→proxy libintl→gtk3 DT_NEEDED 链）；nemo_module 三入口符号解析；nemo_module_list_types() 实调用返回 1 个 GType；vendored libnemo-extension.so 独立加载 |
| ABI 符号 | 6 | 扩展实际调用的 6 个 libnemo-extension 符号逐一 g_module_symbol 验证（file_info_get_mime_type/get_uri_scheme/list_copy、menu_item_new、两 provider get_type） |

加载测试走的是 GModule —— 与 Nemo 宿主加载扩展的机制完全一致，是真实
代码路径而非仅 nm 符号检查。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | shared-library 配方（R32/R33/R34；双源 get；clang 直构） |
| conandata.yml | 双官方源 + sha256（R39） |
| test_package/ | test_module.c + conanfile.py + MANIFEST.yml（R51 上游 0 测试申报） |
| manifest.yaml | 版本元数据 |
| notes.md | 本笔记 |
| reports/conan-verify-report.md | 8 道门禁报告 |

## 注意事项
- 扩展模块设计上由 Nemo 文件管理器 dlopen；Nemo 主包未适配 OHOS（平台亦
  无该任务），本包交付的是扩展模块本身 + 其链接的 vendored ABI 库。任何
  GModule 宿主均可加载测试（test_package 即如此）。
- libnemo-extension.so 为 vendored 精简子集（5.c/45 符号），非完整上游库
  （缺 column/property-page/info-provider 等本扩展不用的组件）；如未来其他
  nemo 扩展需要更多 ABI，可扩子集或另立 libnemo-extension 独立包。
- GUI 对话框（resize/rotate）需图形会话；无显示环境仅能验证模块加载契约
  （GOption 之外 GtkBuilder ui 文件随包交付未实例化）。
- 探索目录 ~/tmp/nemo-smoke 与 $TMPDIR/builds/nemo-image-6.6.0.{orig,work}
  为本地分析副本，未入 git。
- 2026-09-10 AI 检视二轮（P3 闭环）：测试 3b 新增宿主驱动注册断言——
  自建最小 GTypeModule 子类传入 nemo_module_initialize()（与 Nemo 宿主
  同机制），class_ref 强制加载后 g_type_is_a() 断言注册类型同时实现
  NemoMenuProvider 与 NemoNameAndDescProvider 双接口（接口 GType 从
  vendored ABI 库 dlsym 解析，测试不直接链接）。类型名字符串断言不可行：
  平台 glib（ohos-aarch64）公开头文件裁掉了 g_type_get_name()，已在
  测试注释中说明缺口并以双接口断言钉住身份。test 链接新增 -lgobject-2.0
  （GTypeModule/GObject API 所需）。契约检查 10→11 条全过。
---

**编译结束**: 2026-09-09 22:40
**最终状态**: built
