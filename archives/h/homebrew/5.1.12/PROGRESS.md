# homebrew 5.1.12 编译进度

**日期**: 2026-05-20
**状态**: 🔄 编译中

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | 初始化完成 |
| Step 2 patches | ✅ | 修改 bin/brew: shebang + PATH |
| Step 3 configure | ⏭️ | 跳过（脚本类软件） |
| Step 4 make | ⏭️ | 跳过（脚本类软件） |
| Step 5 install | ✅ | 复制文件到 staging |
| Step 6 safety | ✅ | brew --version 验证通过 |
| Step 7 check | ⏳ | |
| Step 8 staging | ✅ | staging 验证通过 |
| Step 9 package | ⏳ | |
| Step 10 deploy | ⏳ | |
| Step 11 finish | ⏳ | |

## 发现与知识

### 平台适配问题

1. **bash 路径**: 鸿蒙系统 bash 位于 `/data/service/hnp/bin/bash`，不在 `/bin/bash`
   - 解决方案: 将 `#!/bin/bash` 改为 `#!/usr/bin/env bash`
   - 将 exec 中的 `/bin/bash` 改为 `/usr/bin/env bash`

2. **PATH 环境变量**: brew 脚本内部重置 PATH 为 `/usr/bin:/bin:/usr/sbin:/sbin`
   - 解决方案: 修改 PATH 添加 `/data/service/hnp/bin`

### 修改文件清单

- `bin/brew`: 修改 shebang 和 PATH 设置
