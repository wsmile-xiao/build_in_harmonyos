# alacarte 3.58.0 适配笔记

## 编译环境
- 构建系统: script（纯 Python 应用，无 C/C++ 编译；上游 autotools 仅拼接翻译/安装 .py）
- 编译日期: 2026-08-31
- 编译器: N/A（纯 Python 脚本，无需编译）
- 状态: built

## 适配背景与判定
- alacarte 是 GNOME 菜单编辑器（freedesktop.org 菜单规范），3.58.0 版 2025-09-22 发布。
- 源码为纯 Python 3 + GTK3（pygobject）应用：`Alacarte/*.py` 共 5 个源文件 + `alacarte.in` 启动脚本，**零 C/C++ 源码**。
- SKILL R47 语言预检判定 `mixed → env_unsupported`（manifest=autotools c/cpp 族 vs 源码 100% python）。经用户授权按项目 Python 先例（imgp/python-dateutil）进行适配。
- 运行时系统依赖 GTK3 / pygobject / libgnome-menu（pygobject 与 libgnome-menu 不在 ohpcd 制品仓，由目标镜像提供，非 conan 依赖）。

## 编译步骤
1. 官方源下载: `https://download.gnome.org/sources/alacarte/3.58/alacarte-3.58.0.tar.xz`（sha256 `3f4eb937...62d52`）
2. 不运行 configure/make（需 libgnome-menu-3.0 + pygobject-3.0 pkg-config，且无实际编译价值）
3. conanfile.py `package()` 直接打包：
   - `Alacarte/` Python 包 → `lib/python3.12/site-packages/Alacarte`（含由 `config.py.in` 生成的 `config.py`）
   - `alacarte` 启动脚本（由 `alacarte.in` 生成，env python3 shebang）→ `bin/alacarte`
   - 运行时 UI 资源（`data/*.ui` + icons）→ `share/alacarte/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 内部 urllib 下载 download.gnome.org 报 SSL CERTIFICATE_VERIFY_FAILED | 系统 CA 缺失 | 设置 `SSL_CERT_FILE=/data/service/hnp/python.org/python_3.12/lib/python3.12/site-packages/certifi/cacert.pem` |
| 2 | /tmp 只读（E002） | 平台限制 | 下载/日志改用 `$HOME/tmp` |
| 3 | 全部模块顶层 `import gi`（Gtk/GdkPixbuf/GMenu/GLib） | GUI 依赖 | 测试以 mock `gi`/`gi.repository` 注入后加载被测包 `Alacarte.util`，验证核心纯逻辑（唯一文件名/KeyFile 填充） |
| 4 | 上游无任何测试框架/用例 | 上游 CI 仅 `make distcheck` | test_package 补全 23 项断言（语法编译/mock-gi 逻辑测试/包结构断言） |

## 源码修改
- 无补丁（patches/ 为空）。纯 Python 打包，未修改上游源码。

## 依赖版本
- Python 3.12（系统预装，运行时）
- GTK3 / pygobject / libgnome-menu（目标镜像提供，非 conan 依赖）

## 验证结果
- 编译状态：通过（本机 CI 模拟 `build_and_test.sh` 全流程通过，exit=0）
- 上游测试用例通过率：N/A（上游无测试用例，已补全）
- 新增测试用例通过率：23/23（100%）
  - T1 语法编译（py_compile 全部交付 .py）
  - T2 唯一文件名生成逻辑（getUniqueRedoFile/getUniqueFileId/getUniqueUndoFile）
  - T3 KeyFile 填充类型分发（fillKeyFile）
  - T4 包结构断言（bin/alacarte 可执行 + 模块齐全 + config.py 版本）
  - T5 R34 负向防护（被测模块来自被测包）
- CI 门禁：L0=pass / L1=pass / L1e(R34 负向)=pass / L4=pass / L5=pass；L2(version/help)=skip 非阻塞（GUI 应用需图形环境，headless 下无法自检版本）

## 交付物
- 无打包产物（源码仓只收源码与配方，制品经 conan create 进缓存/制品仓）。

## 注意事项
- 软件级 `commands.json` 已声明（type=tool，R38）——产物含 `bin/alacarte` 可执行脚本。
- L2 冒烟（`alacarte --version/--help`）在 headless CI 不可用（GUI 应用），已按非阻塞 skip 处理。
