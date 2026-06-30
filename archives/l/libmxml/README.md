# libmxml (Mini-XML)

**简介**: Mini-XML 是一个小型 XML 文件解析库，由 Michael R Sweet 开发。

- **主页**: https://github.com/michaelrsweet/mxml
- **许可证**: Apache License 2.0
- **语言**: C
- **构建系统**: autotools (configure/make)
- **依赖**: 无（仅依赖标准 C 库和 pthread）

## 已编译版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 4.0.4 | published | 2026-06-18 | HarmonyOS aarch64 预编译包 |

## 安装说明

```bash
# 通过 cmd-pkgs 公共安装脚本安装
curl -fsSL <install.sh> | sh -s -- libmxml 4.0.4
```

## 使用示例

```c
#include <mxml.h>

mxml_node_t *xml = mxmlNewXML("1.0");
mxml_node_t *root = mxmlNewElement(xml, "data");
mxmlElementSetAttr(root, "key", "value");
// ...
mxmlDelete(xml);
```

编译: `clang prog.c $(pkg-config --cflags --libs mxml4)`
