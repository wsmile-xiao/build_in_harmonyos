# libeconf — Enhanced Config File Parser

libeconf 是 openSUSE 开发的增强型配置文件解析库，能够从 `/usr/etc`、`/run`、`etc` 等多个目录合并配置文件片段，形成统一的配置视图。支持 INI 格式配置文件的读取、写入和合并操作。

## 核心功能

- **多目录合并**: 自动从 vendor（`/usr/etc`）、runtime（`/run`）、admin（`/etc`）目录读取并合并同名配置片段
- **类型转换**: 支持字符串、整数、布尔、浮点数、64 位整数等多种类型的键值读取
- **配置编辑**: 提供 `econftool` 命令行工具，支持 `show`、`cat`、`syntax`、`edit` 操作
- **文件写入**: 支持创建新配置文件并写入磁盘
- **合并覆盖**: `econf_mergeFiles` 支持两个配置对象的合并，后者覆盖前者同名键值

## API 概览

| 函数 | 说明 |
|------|------|
| `econf_readConfig` | 按 OpenSUSE 目录约定读取合并配置 |
| `econf_readFile` | 读取单个配置文件 |
| `econf_newKeyFile` | 创建空配置对象 |
| `econf_getStringValue` | 获取字符串值 |
| `econf_getIntValue` | 获取 32 位整数 |
| `econf_getBoolValue` | 获取布尔值 |
| `econf_getDoubleValue` | 获取双精度浮点值 |
| `econf_setStringValue` | 设置字符串值 |
| `econf_writeFile` | 写入配置文件到磁盘 |
| `econf_mergeFiles` | 合并两个配置对象 |
| `econf_free` | 释放配置对象 |

## 鸿蒙适配说明

- **构建系统**: cmake
- **依赖**: 无外部依赖（仅需 libc + libm）
- **补丁**: `0001-util-econftool.c.patch` — 替换硬编码 `/tmp` 为 `getenv("TMPDIR")` 回退 `/data/local/tmp`（E002: HMDFS /tmp 只读）
- **共享库**: libeconf.so.0.8.3（带 SOVERSION 符号链接）
- **命令行工具**: econftool

## 安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libeconf 0.8.3
```

## 使用示例

```c
#include <libeconf.h>

econf_file *key_file = NULL;
econf_err error = econf_readFile(&key_file, "/path/to/config.conf", "=", "#");
if (error == ECONF_SUCCESS) {
    char *value = NULL;
    econf_getStringValue(key_file, "section", "key", &value);
    printf("value = %s\n", value);
    free(value);
    econf_free(key_file);
}
```