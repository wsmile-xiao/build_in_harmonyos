# chkrootkit

<!-- 软件级 README.md -->

chkrootkit 是一款用于本地检查 rootkit 迦象的安全检测工具。 它由一个主 shell 脚本和多个 C 语言编写的辅助工具组成，检测系统日志和进程信息中的异常，帮助识别可能被篡改的系统二进制文件.

 ## 当前版本

- 0.59（已编译发布）

## 构建系统

自定义 Makefile（无 configure 脀本， 无 install 目标）

## 安装布局

| 文件 | 说明 |
|------|------|
| `bin/chkrootkit` | Wrapper 脚本， 通过 cd 到 libexec 目录后调用主检测脚本 |
| `libexec/chkrootkit/chkrootkit` | 主检测 shell 脚本（约 96KB） |
| `libexec/chkrootkit/chklastlog` | lastlog 删除记录检查工具 |
| `libexec/chkrootkit/chkwtmp` | wtmp 删除记录检查工具 |
| `libexec/chkrootkit/chkproc` | 隐藏进程检查工具 |
| `libexec/chkrootkit/chkdirs` | 隐藏目录检查工具 |
| `libexec/chkrootkit/check_wtmpx` | wtmpx 检查工具（Solaris 专用） |
| `libexec/chkrootkit/strings-static` | 自定义 strings 工具 |
| `libexec/chkrootkit/chkutmp` | utmp 删除记录检查工具 |

## 平台适配说明

- **ifpromisc 未编译**: 需要 `/usr/include/linux/if.h`，OpenHarmony 上无此头文件，chkrootkit 运行时会报告 ifpromisc "not tested"
- **静态链接已禁用**: Makefile 默认 `-static` 在 OpenHarmony/musl 上不兼容，`strings-static` 名称虽含 "static" 但实际是动态链接
- **wrapper 脚本**: chkrootkit 主脚本使用 `./` 引用工具，wrapper 通过 cd 到 libexec 目录解决此路径问题

## 功能验证

已通过本地安装验证：
- `chkrootkit -V` → 输出 `chkrootkit version 0.59`
- `chkrootkit -l` → 列出所有检测模块
- 各 C 工具均可独立执行（平台限制导致部分输出不符预期，属正常行为）

## 注意事项

1. chkrootkit 需要读取 `/var/adm/lastlog`、`/var/adm/wtmp` 等系统日志文件，OpenHarmony 上这些文件路径不同或不存在，属于平台差异
2. chkproc 依赖 `ps auxw` 格式，OpenHarmony 的 `ps` 不支持此参数格式
3. chkrootkit 完整检测需要 root 权限