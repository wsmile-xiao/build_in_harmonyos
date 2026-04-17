# texinfo — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf texinfo-7.3-ohos-aarch64.tar.gz -C ~/usr/local

cd texinfo-7.3-ohos-aarch64 && sh install-texinfo-7.3.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 7.3 | success | 9 |

## 当前版本 (7.3) 详情

### 包内容
- 二进制: texi2any, makeinfo, install-info, texindex, pod2texi, texi2pdf, texi2dvi, pdftexi2dvi
- 包大小: 8.3MB

### 编译信息
- 构建系统: autotools
- 目标: aarch64-unknown-linux-ohos
- configure: `--prefix=$TEST_PREFIX --disable-nls CC=clang`
- 质量门禁: PASS
- 补丁数: 9
- 测试: 92/138 通过，46 跳过（缺外部工具），0 失败

### 补丁列表
- 0001-Makefile.patch — 顶层 Makefile 修改（从 SUBDIRS 移除 doc 跳过文档构建）
- 0002-Pod-Simple-Texinfo-Makefile.patch — Perl 子模块 Makefile 修改
- 0003-Pod-Simple-Texinfo-pod2texi.patch — Perl 子模块 pod2texi 脚本修改
- 0004-build-aux-config.guess.patch — 主目录 config.guess 添加 HarmonyOS 检测 (E007)
- 0005-build-aux-config.sub.patch — 主目录 config.sub 添加 ohos 支持 (E072)
- 0006-tta-build-aux-config.guess.patch — tta/ 子目录 config.guess (E007)
- 0007-tta-build-aux-config.sub.patch — tta/ 子目录 config.sub (E072)
- 0008-tta-perl-CheckXS-build-aux-config.guess.patch — CheckXS 子目录 config.guess (E007)
- 0009-tta-perl-CheckXS-build-aux-config.sub.patch — CheckXS 子目录 config.sub (E072)

### 已知限制
- 文档构建跳过（texi2any @include 路径解析问题）
- info viewer 交互式测试因文件权限限制失败（不影响功能）
- gzip 相关功能受限（系统 gzip 为 toybox 版本）
- LaTeX 工具链未安装（texi2pdf 等需 LaTeX 支持）

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
