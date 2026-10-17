# libregf

访问 Windows NT Registry File（REGF）格式的 C 库。

## 简介

libregf 解析 Windows 注册表配置单元文件（SYSTEM、SOFTWARE、NTUSER.DAT 等），提供键/值枚举、数据类型读取与导出能力。随包构建终端工具：

- **regfinfo**：显示 REGF 文件版本、键值统计等信息
- **regfexport**：导出注册表键值数据
- **regfmount**：将注册表键值挂载为目录与文件（需 FUSE/Dokan，OHOS 上按需提供）

## 官网

https://github.com/libyal/libregf

## 许可证

LGPL-3.0-or-later

## 编译信息

| 版本 | 状态 | 编译日期 | 构建系统 | 补丁数 |
|------|------|----------|----------|--------|
| 20240421 | building | 2026-09-18 | autotools | 0 |

### 平台适配要点

| 问题编号 | 说明 | 解决方案 |
|----------|------|----------|
| E007 | GNU config.guess 不识别 HarmonyOS | conanfile.py 内联补丁 config.guess/config.sub |
| E011 | HMDFS 下 umask 077 导致临时目录不可写 | configure/config.status 内 umask 077 改 022 |

## 依赖

无外部依赖。内部捆绑 libyal 系列子库（libcerror、libcdata、libbfio 等）随包编译；测试阶段需 pkgconf 与 bash（tool_requires，仅构建期）。
