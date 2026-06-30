# aespipe

AES 加密/解密管道工具 — 从标准输入读取数据，使用 AES 算法加密或解密后输出到标准输出。

支持 AES-128、AES-192、AES-256 三种密钥长度，以及 SHA-256/384/512、RIPEMD-160 等密码哈希算法。

- **版本**: 2.4j
- **构建系统**: autotools
- **依赖**: 无（仅依赖 libc）
- **源码**: https://loop-aes.sourceforge.net/aespipe/

## OpenHarmony 适配说明

### HMDFS ACL 与 umask 077 冲突

HMDFS 文件系统强制目录组权限为 `rws`（setgid）。当 autotools 的 `configure` 脚本使用 `umask 077 && mktemp -d` 创建临时目录时，umask 077 剥夺组权限后，HMDFS ACL 机制阻止 owner 在子目录中写入文件，导致 config.status 报 Permission denied。

**修复**: 补丁 `0001-configure.patch` 去掉 configure 中创建临时目录时的 `umask 077`，使 HMDFS ACL 组权限保持完整。

此问题为 HMDFS 平台通用问题，所有使用 autotools 构建系统的软件都可能遇到。

### 架构检测

aespipe configure 检测到 `output architecture: unknown`，不会使用任何优化的汇编 AES 代码（armv4/armv8ce/armv8sca/x86/amd64），仅使用纯 C 实现。功能完全正常，性能不受关键影响。