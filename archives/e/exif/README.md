# exif

## 简介

exif 是一个命令行工具，用于读取、写入、修改和显示数码照片中的 EXIF（Exchangeable Image File Format）元数据。它基于 libexif 库，支持查看相机型号、拍摄时间、曝光参数、GPS 坐标等信息。

## OHOS 适配

- 使用 autotools 构建系统（configure + make）
- 需要更新 config.guess 和 config.sub 以识别 HarmonyOS 平台（aarch64-unknown-harmonyos）
- configure 临时文件创建受 uid/目录属主权限限制，需修改临时目录路径为 ${HOME}/tmp 并设置 umask 002（E002）
- 编译为命令行工具（package_type=application），产物为 bin/exif
- 依赖 libexif/0.6.26.1 和 popt/1.16（均已在制品仓发布）
- make check 通过：12 PASS, 0 FAIL

## 版本

| 版本 | 说明 |
|------|------|
| 0.6.22 | 首次适配上游 0.6.22 |
| 0.6.22.1 | 适配修复版本（R37 版本递增，conandata.yml URL 变动） |

## 依赖

- libexif/0.6.26.1（conan 制品仓已发布）
- popt/1.16（conan 制品仓已发布）
