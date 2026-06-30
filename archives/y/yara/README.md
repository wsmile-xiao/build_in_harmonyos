# yara

YARA 是一个模式匹配工具，主要用于恶意软件的识别和分类。

## 功能概述

- 基于规则的模式匹配
- 恶意软件识别和分类
- 支持字符串、正则表达式和十六进制模式
- 支持文件、内存和进程扫描
- 支持多种文件格式
- 可扩展的规则语法
- 支持 C 和 Python API

## OHOS 适配要点

### 构建系统

YARA 使用标准的 autotools 构建系统：

```bash
autoreconf -i
./configure --prefix=/usr/local
make
make install
```

### 规则语法

YARA 规则的基本结构：

```yara
rule ExampleRule {
    strings:
        $string1 = "example"
        $hex1 = { E2 34 A1 C8 23 }
        $regex1 = /md5: [0-9a-fA-F]{32}/

    condition:
        any of them
}
```

### 使用场景

YARA 主要用于：

- 恶意软件识别
- 文件分类
-威胁狩猎
- 安全研究

## 依赖关系

### 编译依赖
- autoconf, automake, libtool
- flex, bison（可选，用于规则解析）

### 运行依赖
- 无特殊依赖

## 使用示例

```bash
# 扫描文件
yara -r rules.yar target_file

# 扫描目录
yara -r rules.yar /path/to/directory

# 显示匹配详情
yara -s -r rules.yar target_file

# 编译规则
yarac rules.yar compiled_rules.yarc
```

## 参考资料

- 官方仓库：https://github.com/VirusTotal/yara
- 官方文档：https://yara.readthedocs.io/
- GitHub Releases：https://github.com/VirusTotal/yara/releases
- VirusTotal：https://www.virustotal.com/