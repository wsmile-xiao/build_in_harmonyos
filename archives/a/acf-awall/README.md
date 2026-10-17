# acf-awall

Alpine Configuration Framework（ACF）的 awall 管理模块 —— 为 Alpine Wall (awall) 防火墙
提供基于 Web 的系统管理界面（后端控制器/模型 + HTML LSP 模板）。

- 上游仓库：https://gitlab.alpinelinux.org/acf/acf-awall
- 构建系统：纯 Makefile（noarch，无 C 编译，`make install` 仅 `cp -a awall* $(appdir)/awall`）
- 产物：`share/acf/app/awall/` 下的 Lua 控制器/模型、HTML 模板、菜单与角色文件

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.4.1 | built | 首次适配。纯 Lua/LSP 脚本包，conan-verify 通过，test_package 自增 8/8 |

## 依赖

- **无 conan requirements**（纯脚本包，同 acf-pingu 先例）
- 运行时宿主依赖：ACF 框架 `acf-core`（提供共享模板 filedetails-html.lsp/status-html.lsp，即
  本包 3 个悬空符号链接的目标）与 `awall` 防火墙工具，由框架宿主在运行时加载

## 适配要点

- 3 个 `.lsp` 符号链接（editpolicy/viewpolicy → `../filedetails-html.lsp`、status →
  `../status-html.lsp`）指向 acf-core 共享模板，为悬空符号链接；conan `package()` 用
  python 逐文件复制：普通文件 `copy2`、符号链接 `os.symlink` 重建（保持相对目标）
- 上游无测试套件（Alpine aports `options="!check"`），test_package 自增实质验证：
  文件齐全性（8 文件，含符号链接 `-L` 检查）+ `lua -p` 语法检查（解释器可用时）
