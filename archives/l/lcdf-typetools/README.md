# LCDF Typetools

LCDF Typetools 是一组用于操作 PostScript Type 1、Multiple Master、OpenType 和 TrueType 字体的命令行工具。

## 软件信息

- **版本**: 2.110
- **许可证**: GPL
- **官方网站**: https://www.lcdf.org/type/
- **源码**: https://github.com/kohler/lcdf-typetools

## 包含工具

本软件包包含以下工具：

1. **cfftot1** - 将 CFF/OpenType 字体转换为 Type 1 格式
2. **mmafm** - 为 Multiple Master 字体创建 AFM 文件
3. **mmpfb** - 为 Multiple Master 字体创建单实例字体
4. **otfinfo** - 报告 OpenType/TrueType 字体信息
5. **otftotfm** - 为 OpenType/TrueType 字体创建 TeX 字体度量（需要 kpathsea）
6. **t1dotlessj** - 创建包含 dotless j 的 Type 1 字体
7. **t1lint** - 检查 Type 1 字体的正确性
8. **t1rawafm** - 从 Type 1 字体生成原始 AFM
9. **t1reencode** - 替换字体的内部编码
10. **t1testpage** - 创建 Type 1 字体的测试页面
11. **ttftotype42** - 为 TrueType 字体生成 Type 42 包装器

## OpenHarmony 编译说明

### 编译选项

- `--without-kpathsea`: 禁用 kpathsea 支持（otftotfm 功能受限，其他工具正常）
- `--prefix`: 标准安装路径（~usr/local）

### 平台适配要点

1. **TMPDIR**: 必须设置 `TMPDIR=/data/storage/el2/base/cache`
2. **编译目录**: 建议在 ~/tmp 目录编译，避免 HMDFS 文件系统限制
3. **config.status**: autotools 生成的 config.status 在 HMDFS 上需要修改临时文件路径

### 编译命令

```bash
export TMPDIR=/data/storage/el2/base/cache
./configure --prefix=~/usr/local --without-kpathsea
make -j1
make install DESTDIR=~/test-install-lcdf-typetools-2.110
make install
```

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 2.110 | built | 2026-06-09 | 首次编译成功 |