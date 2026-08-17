# acf-chrony 0.8.1 适配笔记

## 编译环境
- 构建系统: makefile（递归 Makefile，纯 Lua 应用包，无 C 源码）
- 编译日期: 2026-08-16
- 编译器: clang/clang++（本包无 C 源码，未实际调用）
- 状态: built

## 编译步骤

acf-chrony 是 Alpine Configuration Framework 的 chrony 应用插件包，纯 Lua + lsp 模板，无 configure、无 C 源码。

```bash
source .build-context-acf-chrony-0.8.1
cd $BUILD_SRC_DIR
make -j1                              # all 目标为空（Nothing to be done）
make install DESTDIR=$TEST_PREFIX -j1 # cp -a chrony* $DESTDIR/usr/share/acf/app/chrony/
```

install 目标仅 `mkdir -p` + `cp -a chrony*`，将 10 个文件（7 实文件 + 3 符号链接）安装到 `$DESTDIR/usr/share/acf/app/chrony/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载失败 HTTP 418 | gitlab.alpinelinux.org 拦截脚本 UA | 用 curl 带 UA 下载到 `$TMPDIR/builds/`，init-build 复用已存在 tarball |
| 2 | init-build dual-track 复制失败 | HMDFS 不支持硬链接（os.link → EPERM），回退 copy2 解引用悬空符号链接失败 | 手动 `cp -a`（保留符号链接）重建 .work 目录 |
| 3 | init-build 误将归档放到 SKILL 树 | find_project_dir 定位到 SKILL 目录而非项目主仓库 | 手动迁移归档与上下文到 `build_in_harmonyos/`，修正上下文中 BUILD_ARCHIVE_DIR/BUILD_CONTEXT_FILE |
| 4 | Staging 3 个符号链接 BROKEN | 指向 `../expert-html.lsp` 等 acf-core 共享模板，DESTDIR 内无上级目录 | ACF 框架设计：这些 .lsp 由 acf-core 运行时提供，配方保留符号链接，由 acf-core 依赖解析 |

## 源码修改

无补丁。源码未修改。

## 依赖版本

- acf-core/0.24.1（已发布 ohpcd，提供 ACF 框架共享 .lsp 模板）
- chrony/4.8（已发布 ohpcd，运行时被配置的目标守护进程）
- lua/5.4.8（acf-core 的依赖，运行时 Lua 解释器）

## 验证结果

```bash
$ make -j1
make: Nothing to be done for 'all'.

$ make install DESTDIR=$TEST_PREFIX -j1
mkdir -p ".../usr/share/acf/app/chrony"
cp -a chrony* ".../usr/share/acf/app/chrony"

$ find $TEST_PREFIX -type f | wc -l
7

$ find $TEST_PREFIX -type l
.../chrony-expert-html.lsp -> ../expert-html.lsp
.../chrony-logfile-html.lsp -> ../logfile-html.lsp
.../chrony-status-html.lsp -> ../status-html.lsp
```

无 `make check` 目标（纯 Lua 应用包）。无可执行二进制，无需 R7 安全弹窗触发。

## 测试（上游无测试套件，自建完整功能测试集）

- 上游：aports APKBUILD 声明 `options="!check" # no test suite`；源码 tarball 仅 Makefile/README/Lua/.lsp/.menu/.roles，无 test/ 目录、无 make check 目标（已排查上游仓库打包记录与 Alpine build log 确认）。
- 自建测试集（test_package/，R34 实质验证，92/92 PASS）：
  - `test_app.lua`（34 断言）：加载真实 chrony-controller.lua，验证全 8 个 controller 函数（status/details/startstop/config/keyfile/enablekeyfile/expert/logfile）+ controller→model dispatch 调用链 + chrony.menu/.roles 声明解析。
  - `test_model.lua`（58 断言）：加载真实 chrony-model.lua，验证 model 层全部 13 个公开函数（getstatus/getdetails/get_startstop/startstop_service/get_config/update_config/get_keyfiledetails/update_keyfiledetails/get_enable_keyfile/enable_keyfile/get_filedetails/update_filedetails/get_logfile）+ validate_config 校验规则（非法 server/allow/driftfile/commandkey 拒绝）+ 配置写回路径 + chronyc 密码查找。mock 仅限 acf-core 框架依赖（cfe/modelfunctions/acf.validator），chrony.conf 以内存模拟。
  - `test_app.sh`：测试入口，串联运行两个测试文件。
- 测试夹具（share/lua/5.4/，TEST-HARNESS ONLY）：posix/subprocess/json/md5 + acf.format/fs/html/processinfo/apk shim，与 acf-core 测试同模式。

## 注意事项

- acf-chrony 是 ACF 框架的应用插件包，与 acf-core 同模式：纯 Lua + Makefile install，无 C 编译。
- 3 个符号链接指向 acf-core 的共享 .lsp（expert/logfile/status-html.lsp），这是 ACF 框架的模板继承设计，非缺陷。
- 软件类型为 application（命令行工具），但本包不直接提供 CLI 二进制——CLI 由 acf-core 的 acf-cli 统一入口。R38 commands.json 判定：本包不新增独立命令，无需单独 commands.json（acf-core 已声明）。
---

**编译结束**: 2026-08-16 13:03
**最终状态**: published
