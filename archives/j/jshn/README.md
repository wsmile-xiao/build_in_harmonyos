# jshn

## 简介

jshn（JSON Shell）是一个用于在shell脚本中解析和处理JSON数据的工具。它是OpenWrt libubox项目的组件，提供了高效的JSON处理能力。

## 功能特性

- **jshn可执行文件**: C语言编写的JSON解析工具，生成shell脚本代码
- **jshn.sh脚本**: Shell辅助脚本，提供便捷的JSON操作函数
- 支持JSON解析、查询、修改和生成
- 专为shell脚本环境优化，易于集成

## 版本

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|---------|--------|
| master | built | 2026-05-29 | 1 |

## 所属项目

jshn是**libubox**项目的组件：
- 源码位置：https://git.openwrt.org/project/libubox.git
- 组件路径：jshn.c
- 相关组件：libblobmsg_json.so、libubox.so

## 依赖

- **json-c**: JSON C库（预编译包）
- **libubox**: OpenWrt核心工具库
- **libblobmsg_json**: JSON blob消息处理库

## 使用方式

### 安装预编译包

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- jshn master
```

### 在shell脚本中使用jshn

```bash
# 加载jshn辅助脚本
source ~/usr/local/share/jshn/jshn.sh

# 解析JSON数据
json_init
json_load '{"name":"test","value":42}'
json_get_var name name
json_get_var value value
echo "name=$name, value=$value"

# 生成JSON数据
json_init
json_add_string "name" "example"
json_add_int "value" 100
json_dump
```

### 直接使用jshn命令

```bash
# 解析JSON消息
jshn -r '{"key":"value"}'

# 从文件读取JSON
jshn -R data.json

# 输出到文件
jshn -r '{"key":"value"}' -o output.sh

# 使用自定义前缀
jshn -r '{"key":"value"}' -p JSON_
```

## 包内容

预编译包包含以下文件：
- `bin/jshn`: JSON shell工具可执行文件（78KB）
- `lib/libblobmsg_json.so`: JSON blob消息库（78KB）
- `lib/libubox.so`: 核心工具库（94KB）
- `lib/external/libjson-c.so`: JSON C库（98KB）
- `share/jshn/jshn.sh`: Shell辅助脚本（7.3KB）

## 注意事项

1. **RPATH设置**: 预编译包已自动设置RPATH，无需手动设置LD_LIBRARY_PATH
2. **依赖完整**: lib/external目录包含所有外部依赖，包可独立运行
3. **Shell脚本**: 需要source jshn.sh才能使用便捷函数
4. **与libubox的关系**: jshn是libubox的一部分，也可安装完整libubox包

## 已知问题与解决方案

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| jshn.sh找不到 | 未source脚本 | source ~/usr/local/share/jshn/jshn.sh |
| 找不到依赖库 | RPATH未设置 | 预编译包已设置，无需处理 |
| JSON解析失败 | 格式错误 | 检查JSON格式是否正确 |

## 归档目录

- **软件级**: archives/j/jshn/
- **版本级**: archives/j/jshn/master/
- **源项目**: archives/l/libubox/

## 参考资料

- [OpenWrt libubox源码](https://git.openwrt.org/project/libubox.git)
- [OpenWrt jshn文档](https://openwrt.org/docs/guide-developer/jshn)
- [libubox归档](../l/libubox/)

---

**最后更新**: 2026-05-29