# cloud-utils 0.33 适配笔记

## 编译环境
- 构建系统: Makefile (simple install scripts)
- 编译日期: 2026-08-06
- 状态: published (conan recipe verified)

## 源码
- 上游: https://github.com/canonical/cloud-utils
- 版本: 0.33
- 类型: Shell/Python脚本工具集，无需编译

## 适配修改

### 1. Makefile — install 命令兼容性修复
- **问题**: HarmonyOS 的 `install` 命令不支持 `--mode=0644` 选项
- **修复**: 改用 `-m 0644` 短选项格式
- **补丁**: 0001-Makefile.patch

### 2. Shebang 修复 (5个脚本)
- **问题**: 脚本使用硬编码的 `#!/bin/bash` 和 `#!/usr/bin/python3`，HarmonyOS 上这些路径不存在
- **修复**: 改为 `#!/usr/bin/env bash` 和 `#!/usr/bin/env python3`
- **受影响文件**:
  - bin/cloud-localds (#!/bin/bash → #!/usr/bin/env bash)
  - bin/ec2metadata (#!/usr/bin/python3 → #!/usr/bin/env python3)
  - bin/mount-image-callback (#!/bin/bash → #!/usr/bin/env bash)
  - bin/vcs-run (#!/bin/bash → #!/usr/bin/env bash)
  - bin/write-mime-multipart (#!/usr/bin/python3 → #!/usr/bin/env python3)
- **补丁**: 0002-0006

## 构建步骤
1. 下载源码: `get(self, **self.conan_data["sources"], strip_root=True)`
2. 应用补丁: `apply_conandata_patches(self)`
3. 安装: `make install BINDIR=$PKG/bin MANDIR=$PKG/share/man/man1`

## 交付物
| 命令 | 类型 | 说明 |
|------|------|------|
| growpart | sh | 分区扩容工具 |
| cloud-localds | bash | 创建cloud-init本地数据源 |
| ec2metadata | python3 | EC2元数据查询 |
| mount-image-callback | bash | 挂载镜像回调工具 |
| resize-part-image | sh | 调整分区镜像大小 |
| ubuntu-cloudimg-query | sh | Ubuntu云镜像查询 |
| vcs-run | bash | 版本控制系统运行器 |
| write-mime-multipart | python3 | MIME多部分写入工具 |

## Conan 配方
- package_type: application
- settings: os, arch (no compiler needed)
- bindirs: ["bin"]
- 无外部依赖
---

**编译结束**: 2026-08-06 03:43
**最终状态**: published
