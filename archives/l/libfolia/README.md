# libfolia

FoLiA (Format for Linguistic Annotation) 是一个用于语言学标注的 XML 格式库。

## 软件信息

| 项目 | 内容 |
|------|------|
| 名称 | libfolia |
| 版本 | 2.21 |
| 源码 | https://download.savannah.nongnu.org/releases/libfolia/libfolia-2.21.tar.gz |
| 构建系统 | Autotools (需 autoreconf) |
| 许可证 | GPL-3.0 |

## 功能描述

libfolia 提供了处理 FoLiA 格式 XML 文档的 C++ 库，包括：
- FoLiA 文档的解析和生成
- 语言学标注的验证和查询
- 文本处理和结构化标注支持

## 主要组件

- `libfolia.so` - 核心库
- `folialint` - FoLiA 文档验证工具
- `foliadiff.sh` - FoLiA 文件比较脚本

## 依赖

- libxml2 >= 2.9.4
- ticcutils >= 0.34
- ICU (icu-uc, icu-io)
- libomp (OpenMP 运行时)

## 鸿蒙适配要点

### E011 HMDFS umask 问题

libfolia 需要 autoreconf 生成 configure 脚本。生成的 configure 中包含 `umask 077`，
在 HMDFS 文件系统上会导致临时目录权限问题。

**解决方案**：
```bash
autoreconf -fi
sed -i 's/umask 077/umask 022/g' configure
./configure --prefix=$DEFAULT_PREFIX
```

### config.guess/config.sub

autoreconf 会自动安装最新版本的 config.guess/config.sub，无需手动修改。

## 安装验证

```bash
# 安装依赖
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libomp 15.0.4

# 验证
folialint --version
# 输出: folialint version 0.5 based on [libfolia 2.21]
```

## 已编译版本

| 版本 | 状态 | 预编译包 |
|------|------|----------|
| 2.21 | published | libfolia-2.21-ohos-aarch64.tar.gz |

## 参考链接

- [FoLiA 官网](https://proycon.github.io/folia/)
- [E011 HMDFS umask 问题](../knowledge/doc/E011.md)