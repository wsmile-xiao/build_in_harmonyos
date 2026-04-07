# pkg-config 0.29.2 for HarmonyOS (aarch64)

## Quick Start
\`\`\`bash
tar xzf pkg-config-0.29.2-ohos-aarch64.tar.gz -C ~/usr/
find pkg-config-0.29.2/ -type f -exec chmod +x {} \;
. ~/usr/pkg-config-0.29.2/activate.sh
pkg-config --version
\`\`\`

> ⚠️ **解压后必须 chmod +x**（HarmonyOS 签名机制导致 tar 包内丢失执行权限）

## 验证
\`\`\`bash
pkg-config --list-all   # 查询所有已安装库
pkg-config --modversion zlib  # 查询特定库版本
\`\`\`

## 文件清单
| 文件 | 说明 |
|------|------|
| bin/pkg-config | 主程序 |
| bin/aarch64-unknown-linux-ohos-pkg-config | 三元组别名 |
| share/aclocal/pkg.m4 | autoconf m4 宏 |
| share/man/man1/pkg-config.1 | 手册页 |

## 编译信息
- **编译器**: clang 15.0.4 (LLVM, HarmonyOS SDK)
- **构建系统**: Autotools (内嵌 glib 2.38.2)
- **配置选项**: `--prefix=... --with-internal-glib` (P0 最简)
- **依赖**: 仅 musl libc (静态链接 glib)
