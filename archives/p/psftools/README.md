# psftools

PSF (PC Screen Font) 格式字体工具集，用于操作固定宽度位图字体。

- **上游**: https://www.seasip.info/Unix/PSF/
- **许可证**: GPL-2.0-or-later
- **语言**: C
- **构建系统**: autotools

## 已编译版本

| 版本 | 状态 | 平台 | 日期 |
|------|------|------|------|
| 1.0.14 | published | aarch64-unknown-linux-ohos | 2026-06-26 |

## 工具列表 (34 个)

psftools 提供 34 个终端工具，用于在各种字体格式之间转换：

- **PSF 转出**: psf2txt, psf2raw, psf2bdf, psf2bsd, psf2fnt, psf2inc, psf2ams, psf2bbc, psf2wof, psf2wyse, psf2xbm, psf2zx, psf2pbms
- **PSF 转入**: txt2psf, raw2psf, ams2psf, bbc2psf, fnt2psf, mda2psf, wof2psf, wyse2psf, zx2psf, cpi2psf
- **PSF 操作**: psfjoin, psfmerge, psfxform, psfpages
- **CPI 工具**: cpicomp, cpidcomp, psfs2cpi, page2cp2
- **其他**: fon2fnts, fnts2fon, psfs2mda

## 库文件

- `libpsf.a`: PSF 格式处理静态库
- `psflib.h` / `psfutils.h`: 头文件
