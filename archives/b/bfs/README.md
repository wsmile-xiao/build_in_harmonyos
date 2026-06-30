# bfs

广度优先版本的 UNIX find 命令，以广度优先顺序遍历文件系统。

## 功能特性

- 广度优先遍历（而非深度优先）
- 兼容 find 命令的语法和选项
- 更适合交互式使用（先显示当前目录文件）
- 支持丰富的过滤和动作选项

## 版本列表

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| [4.1](./4.1/) | built | 2026-06-15 | 运行时兼容性问题已修复 |

## HarmonyOS 适配说明

### 关键问题

1. **statx syscall 兼容性**: HarmonyOS 对 stdout/stderr 等特殊文件描述符的 statx syscall 支持不完善，导致 bfs_ctx_dedup() 错误
2. **解决方案**: 禁用 statx syscall（BFS_HAS_STATX_SYSCALL=false），使用传统 fstat/fstatat

### 编译注意事项

- configure 脚本会创建符号链接支持 out-of-tree 构建
- 使用 `INSTALL=ginstall` 而非默认的 `install` 命令
- 禁用 statx syscall 补丁必须应用

## 来源

- GitHub: https://github.com/tavianator/bfs