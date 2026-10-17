# argyll-cms

## 简介

ArgyllCMS（Argyll Color Management System）是 Graeme W. Gill 开发的 ICC 兼容色彩管理系统，
以**命令行工具集**形式发布（无 GUI shell）：显示器/投影仪校准与剖析、扫描仪与相机输入
剖析、RGB/CMYK 打印机剖析、Device Link 与 3DLUT 生成、色域计算与色彩转换引擎。

本仓库适配版本：**3.5.0**（上游 2026-02-04 发布，V3.4.1 的 bug fix 更新）。

## OHOS 适配

- **构建系统**：上游使用 Perforce **Jam**（`jam -fJambase`）；发布包只带 `Jambase`/`Jamfile`/`Jamtop`，
  不带 jam 本体，因此以 `tool_requires jam/ajam-2.5.2-1.3.4`（FT-Jam 2.5.2 + ArgyllCMS V1.3.3 Jambase）消费。
- **X11 路径**：`Jamtop` 只在 `/usr/X11R6`、`/usr/include`、`/usr/lib64` 等 FHS 固定路径 GLOB 查找 X11
  头/库，找不到就 `EXIT`。补丁 `0001-Jamtop.patch` 让它接受 `X11HDRDIR`/`X11LIBDIR` 两个 jam 变量，
  配方用上游自带的 `JamExtra` 钩子注入 Conan 依赖路径。
- **内置三方库**：zlib / jpeg / png / tiff 用 Argyll 自带源码树编译（`BUILTIN_*=true`），
  不引入外部依赖；其 2008/2011 年代的 `config.guess`/`config.sub`/`configure` 由补丁 0002~0007
  补上 HarmonyOS 三元组并把私有临时目录的 `umask 077` 放宽到 022（E007/E011）。
- **宿主工具链环境变量**：OHOS 设备导出 `AR=llvm-ar` 等通用工具链变量，会被 Jam 当作同名 jam 变量
  导入，顶掉 `AR ?= ar rusc` 导致全部归档失败；配方 `build()` 先净化这些变量，再用 `JamExtra`
  显式赋值（知识草稿 `DRAFT-argyll-cms-jam-host-toolchain-env-shadowing`）。
- **USB 仪器**：不需要额外库，Linux 后端 `spectro/usbio_lx.c` 直接使用 `<linux/usbdevice_fs.h>`。

## 依赖

| 依赖 | 用途 |
|------|------|
| libx11/6.4.0、libxext/6.4.0、libxxf86vm/1.1.5、libxinerama/1.1.6、libxrandr/1.5.5.1、libxscrnsaver/1.2.5、libxau/1.0.11、libxdmcp/1.1.5 | Jamtop `GUILINKFLAGS` 链接的 X11 运行库（dispwin/dispcal/viewgam 等 GUI 工具） |
| jam/ajam-2.5.2-1.3.4 | 构建工具（tool_requires） |

## 产物

- `bin/`：48 个命令行工具（dispcal、dispwin、dispread、colprof、colverify、targen、chartread、
  cctiff、iccdump、icclu、iccgamut、collink、viewgam、printtarg …）
- `ref/`：96 个上游参考数据文件（ICC 示例 profile、测试图表、色域数据等）

## 功能验证

```bash
iccdump  <pkg>/ref/sRGB.icm                       # ICC profile 解析
echo "0.2 0.4 0.6" | icclu -ff -ir -pl <pkg>/ref/sRGB.icm   # 色彩转换引擎
iccgamut <copy of sRGB.icm>                       # 生成 CGATS .gam 色域
targen -d2 -n16 chart                             # 生成 .ti1 测试图表
```

## 参考

- 官网：https://www.argyllcms.com/
- 源码：https://www.argyllcms.com/downloadsrc.html
- 适配笔记与测试报告：`3.5.0/notes.md`、`3.5.0/reports/test-report.md`
