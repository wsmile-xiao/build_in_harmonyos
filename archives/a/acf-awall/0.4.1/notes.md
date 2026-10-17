# acf-awall 0.4.1 适配笔记

## 库性质
- **Alpine ACF (Alpine Configuration Framework) Web 管理模块**：为 awall 防火墙提供基于 Web 的系统管理界面
- 上游：https://gitlab.alpinelinux.org/acf/acf-awall（GPL-2.0-only，Maintainer Ted Trask）
- 纯 Lua/LSP 脚本包，**无编译**（noarch，Makefile 仅做拷贝安装：`mkdir -p $(appdir)/awall && cp -a awall* $(appdir)/awall`，appdir=share/acf/app）
- 本包与 ACF 框架宿主（acf-core）解耦：脚本由框架运行时加载
- 参考先例：acf-pingu 0.4.0（几乎同构的 ACF 模块）

## 上游测试情况
- **上游无测试套件**：release tarball（acf-awall-v0.4.1.tar.gz）仅 2 个 .lua + 4 个 .lsp + roles/menu/README，无 test/spec/check 目录
- `make check` 实测：`make: *** No rule to make target 'check'. Stop.`（Alpine aports 亦声明 `options="!check"` # no test suite）
- 模块行为由 acf-core 框架宿主在运行时验证，不在本 archive 内

## 编译环境
- 构建系统: makefile（无 configure，直接 make install）
- 编译日期: 2026-08-10
- 状态: built

## 编译步骤
```bash
cd $BUILD_SRC_DIR
make DESTDIR=$TEST_PREFIX install   # 纯复制：mkdir -p $(appdir)/awall && cp -a awall*
# 安装产物: $TEST_PREFIX/usr/share/acf/app/awall/{awall-controller.lua, awall-model.lua,
#           awall-{editpolicy,listpolicies,status,viewpolicy}-html.lsp, awall.menu, awall.roles}
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 418 | GitLab 归档 URL 对无 UA 请求返回 HTTP 418（I'm a teapot） | 使用本地已下载 tarball（sha256=5f94fd...），复制为 $HOME/tmp/builds/acf-awall-0.4.1.tar.gz（init-build 期望无 v 前缀文件名），并手动用 `shutil.copytree(symlinks=True)` 创建 .work（os.link 硬链接被文件系统拒绝 EPERM、copy2 对悬空符号链接失败） |
| 2 | tarball 文件名前缀 | init-build 期望 `acf-awall-0.4.1.tar.gz`，本地文件是 `acf-awall-v0.4.1.tar.gz` | 复制时去掉 v 前缀 |
| 3 | 3 个 .lsp 悬空符号链接 | editpolicy/viewpolicy → `../filedetails-html.lsp`、status → `../status-html.lsp`，目标由 acf-core 运行时提供，conan `copy()` 默认跳过符号链接 | package() 用 python 逐文件复制：普通文件 `shutil.copy2`、符号链接 `os.symlink` 重建（保持相对目标），同 acf-pingu；test_package 用 `-L`/`lexists` 检查 |

## 依赖版本
- **无 conan requirements**（纯脚本包，同 acf-pingu 先例；运行时依赖宿主 ACF 框架 acf-core 0.24.1 与 awall 1.14.0，但均不在本包声明，由框架宿主加载）
- 环境性依赖：lua（语法检查用，test_package 检测可用性，可选）

## 验证结果
- 探索阶段 `make DESTDIR install`：8 个文件全部复制成功（含 3 个符号链接）
- test_package 自增测试（L1 smoke，8/8 通过）：`test_awall.sh` 验证 share/acf/app/awall 下 8 个文件齐全（含 3 个悬空符号链接用 -L 验证）；lua -p 语法检查（解释器可用时）
- conan-verify 8 道门禁待验证

## 注意事项
- R32：settings.os 校验 ("Linux", "OHOS")
- R38：acf-awall 无可执行二进制（都是 .lua/.lsp 脚本模块），**不需要 commands.json**（R38 仅命令行工具需要，参照 acf-pingu 无 commands.json）
- 无编译依赖、无 patches、无第三方依赖
---

**编译结束**: 2026-08-10 18:25
**最终状态**: built
