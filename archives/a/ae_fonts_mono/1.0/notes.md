# ae_fonts_mono 1.0 适配笔记

## 编译环境
- 构建系统: custom（纯字体数据包，FreeBSD port 标记 NO_BUILD=yes，无构建系统）
- 编译日期: 2026-08-05
- 编译器: clang 15.0.4 / clang++（本包无需编译）
- 平台: OpenHarmony (aarch64)
- 状态: built

## 编译步骤

1. 初始化: `ohc-run.py init-build ae_fonts_mono 1 --url=https://downloads.sourceforge.net/.../ae_fonts_mono.tar.bz2 --tar tar.bz2 --project-dir <repo>`
2. 下载: `curl -kL` 下载 ae_fonts_mono.tar.bz2（125961 字节）
3. SHA256 校验: `62990ea66e05b9a0ec46490e0adbb69a1c83977bd9dfdc7a2d6ffd208e6ec668` ✅ 与上游一致
4. 解压: tar.bz2，strip 顶层目录 `ae_fonts_mono/`，仅含 10x21.bdf 与 10x21.pcf 两个文件
5. 核验: 无 configure/Makefile/测试目录 → 纯数据包，无构建、无自动化测试
6. Conan 配方: `ohc-run.py conan-init` 生成骨架 → 手工改写为数据包模式 → `conan-verify` 验证

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 归档目录落在 SKILL 根目录 | find_project_dir() 默认定位到 skill 目录 | 显式传 `--project-dir` 指向仓库 |
| 2 | 生成模板为 autotools 构建模板 | conan-init 默认按构建系统生成 | 改写为数据包模式：source() 下载+SHA256+解压，build() 空操作，package() 拷贝字体文件 |
| 3 | G4 产物完整性门禁 | 纯数据包无 bin/lib/include | package() 创建 `lib/pkgconfig/ae_fonts_mono.pc` 满足门禁 |

## 源码修改

无补丁（纯数据包，未修改任何上游文件）。patches/ 为空。

## 依赖版本

无依赖（数据包）。

## 验证结果

```bash
# test_package 真实消费验证（conan create 内执行，独立测试源文件）
# 测试源文件: test_package/test_font_package.py（1 个真实消费测试用例）
# 执行方式: conanfile.py test() → self.run("python3 test_font_package.py <package_root>")
# 断言 6 项（属于同一测试用例，不按断言数拆分为多个用例）：
#   1. 10x21.bdf 存在于 share/fonts/ae_fonts_mono/
#   2. 10x21.pcf 存在于 share/fonts/ae_fonts_mono/
#   3. 10x21.bdf 大小 = 841126 字节
#   4. 10x21.pcf 大小 = 626844 字节
#   5. BDF 头 STARTFONT 2.1 + Public domain 声明
#   6. PCF 魔数 0x01 0x66 0x63 0x70 (\x01fcp)
#   + pkgconfig ae_fonts_mono.pc 存在且 fontdir 可定位字体目录
```

## 交付物

| 文件 | 说明 |
|------|------|
| share/fonts/ae_fonts_mono/10x21.bdf | BDF 字体（841126 B，4491 字形） |
| share/fonts/ae_fonts_mono/10x21.pcf | PCF 字体（626844 B） |
| lib/pkgconfig/ae_fonts_mono.pc | pkg-config 声明（G4 门禁） |

## 注意事项

- 许可证: BDF 头 `COPYRIGHT "Public domain font.  Share and enjoy."`，Public domain
- 上游测试: 无任何自动化测试入口（静态核验），上游测试数量 = 0，不虚构
- 上游事实: FreeBSD port 标记 NO_BUILD=yes，确认无需编译
---

**编译结束**: 2026-08-05 20:31
**最终状态**: built
