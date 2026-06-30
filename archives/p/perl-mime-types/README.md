# perl-mime-types

MIME::Types — 完整的 IANA MIME 类型数据库和查找模块。

## 功能

- 通过文件扩展名查找对应 MIME 类型（如 `png` → `image/png`）
- 通过文件名查找 MIME 类型（如 `photo.jpg` → `image/jpeg`）
- 获取 MIME::Type 对象，查询编码方式和关联扩展名
- 支持内容协商（Accept 头解析）
- 提供 Mojolicious 兼容层（MojoX::MIME::Types）

## 版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 2.29 | published | 2026-06-17 | 纯 Perl 模块，鸿蒙平台完全可用 |

## 依赖

- Perl 5.10+（当前平台 5.42.0）

## 安装

通过 cmd-pkgs 公共安装脚本部署：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-mime-types 2.29
```
