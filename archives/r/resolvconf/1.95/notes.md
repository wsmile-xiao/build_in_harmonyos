# resolvconf build notes

## Build System
resolvconf is a pure shell-script network configuration tool from Debian.
No compilation is required — scripts and configuration files are copied to the package directory.

## Configuration
- Uses Conan package manager
- No build steps needed (build() is pass)
- Main executable copied to bin/
- Helper scripts (list-records, normalize-resolvconf) copied to lib/resolvconf/
- Configuration files copied to share/resolvconf/etc/
- Manpages copied to share/man/

## Platforms
- aarch64 (OHOS)
- Architecture-independent (shell scripts)

## Upstream Tests
- debian/test-normalization: 22 assertions testing normalize-resolvconf sed script
- debian/test-correct-interface-order: 1 assertion testing interface-order consistency
- Total: 23 upstream test assertions
- Note: Upstream tests not run in CI due to cross-compilation; test_package replicates key normalize-resolvconf assertions

## Notes
- normalize-resolvconf is a sed script (#!/bin/sed -f), invoked as `sed -f normalize-resolvconf`
- resolvconf --help and --version work without system dependencies
- No patches needed for basic packaging

## R40 适配完整性声明（基础适配 / 路径 A）

resolvconf 主脚本内部硬编码了以下系统路径，不读取 `RESOLVCONF_LIB` 等环境变量：

- `/usr/lib/resolvconf/` — helper 脚本（list-records、normalize-resolvconf）查找路径
- `/etc/resolvconf/` — 配置文件目录
- `/run/resolvconf/` — 运行时状态目录

Conan 配方将 helper 脚本安装到 `<package_folder>/lib/resolvconf/`，并导出 `RESOLVCONF_LIB` 环境变量，但主脚本不读取该变量，直接使用编译期写死的系统路径。

### 功能限制范围

| 操作 | Conan 包环境可用性 | 原因 |
|------|-------------------|------|
| `resolvconf --help` | ✅ 可用 | 不依赖 helper 脚本 |
| `resolvconf --version` | ✅ 可用 | 不依赖 helper 脚本 |
| `normalize-resolvconf`（直接 `sed -f` 调用） | ✅ 可用 | 绕过主脚本，直接调用 sed 脚本 |
| `resolvconf -a IFACE` | ❌ 不可用 | 主脚本在 `/usr/lib/resolvconf/` 查找 helper，Conan 包路径不匹配 |
| `resolvconf -d IFACE` | ❌ 不可用 | 同上 |
| `resolvconf -u` | ❌ 不可用 | 同上 |

### 适配策略说明

本包为**基础适配（路径 A）**，Conan 包作为分发载体，提供文件供系统安装阶段部署到标准路径（`/usr/lib/resolvconf/`、`/etc/resolvconf/` 等）。部署完成后，resolvconf 的全部功能（包括 `-a`/`-d`/`-u`）在真实 OHOS 系统上正常工作。

未采用深度适配（打 patch 替换硬编码路径为环境变量查找）的原因：
1. resolvconf 是系统管理工具，硬编码路径是其设计约定，部署到系统后应使用标准路径
2. 让路径可重定位会与工具的系统级用途矛盾
3. `resolvconf -a` 等操作需要 root 权限并修改 `/etc/resolv.conf`，不适合在 CI 中测试

### 测试覆盖说明

test_package 的 8 个断言覆盖了 Conan 包环境下可验证的全部功能：
- 二进制存在性（断言 1）
- `--help` 输出正确性（断言 2）
- `normalize-resolvconf` sed 逻辑（断言 3-6，复刻上游 debian/test-normalization 关键用例）
- helper 脚本和配置文件安装完整性（断言 7-8）

`-a`/`-d`/`-u` 等核心操作因依赖系统路径和 root 权限，未纳入 CI 测试，需在真机部署后验证。
