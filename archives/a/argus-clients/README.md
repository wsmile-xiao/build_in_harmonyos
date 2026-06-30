# argus-clients

Argus Clients - Network Flow Data Analysis Tools

## 软件描述

Argus 客户端程序套件，用于读取、分析和管理 Argus 网络流量数据。包括：

- **ra**: Argus 数据读取和分析主程序
- **rabins**: 流量分桶统计工具
- **racluster**: 流量聚类工具
- **racount**: 流量计数统计工具
- **radium**: Argus 数据流处理工具
- **radump**: 流量数据转储工具
- **ramanage**: 远程 Argus 管理工具
- 以及其他示例程序（raconvert, radns, ragrep 等）

## 官方网站

http://qosient.com/argus

## 版本历史

| 版本 | 状态 | 编译日期 | 补丁数 | 备注 |
|------|------|----------|--------|------|
| 5.0.3 | published | 2026-06-15 | 3 | 首次编译，需处理 HarmonyOS 平台适配 |

## 预编译包

- `argus-clients-5.0.3-ohos-aarch64.tar.gz` (27MB)

## 平台适配要点

1. **config.guess**: 需添加 HarmonyOS 系统识别
2. **configure**: 需修改临时目录创建逻辑（使用 $HOME/tmp）
3. **Makefile**: 需删除 PKG_CHECK_MODULES 占位符

## 依赖

- curl (8.19.0+)
- zlib (1.3.1+)

## 使用方法

```bash
# 解压预编译包
tar xzf argus-clients-5.0.3-ohos-aarch64.tar.gz -C /

# 验证安装
ra --version
```

---

*编译日期: 2026-06-15*