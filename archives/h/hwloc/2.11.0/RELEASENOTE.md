# hwloc 2.11.0 — 预编译包发布说明

## 发布信息
- 版本: 2.11.0
- 平台: HarmonyOS/OpenHarmony (aarch64)
- 构建日期: 2026-04-28
- 状态: partial (功能验证通过)

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| hwloc-2.11.0-ohos-aarch64.tar.gz | 6.3MB | 主预编译包 |
| install-hwloc-2.11.0.sh | 1.4KB | 安装脚本 |

## 包含组件
- libhwloc.so.15.8.0 (350KB) - 硬件拓扑库
- lstopo-no-graphics - 拓扑查看工具
- hwloc-bind - CPU绑定工具
- hwloc-info - 信息查询工具
- hwloc-calc - 计算工具
- 其他 hwloc 命令行工具

## 已知问题
1. HMDFS 软链接不支持，已用 cp 替换符号链接
2. 需要 ELF 签名才能执行（已签名）

## 补丁
- 0001-configure-umask-fix.patch: 修复 configure umask 077 导致的临时文件创建问题

## 安装方法
```bash
curl -fsSL <URL>/install-hwloc-2.11.0.sh | sh
# 或解压后运行:
tar xzf hwloc-2.11.0-ohos-aarch64.tar.gz
cd pkg-hwloc-2.11.0
./install-hwloc-2.11.0.sh
```

## 验证
```bash
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
lstopo-no-graphics --version  # 应输出: lstopo-no-graphics 2.11.0
```