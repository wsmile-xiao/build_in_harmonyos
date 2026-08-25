# texlive

## 简介
TeX Live 是 TeX 排版系统的完整发行版，包含 tex、pdftex、xetex、luatex、metapost、mf、dvisvgm、dvipdfmx、bibtex、synctex 等 438+ 个可执行文件和完整的宏包、字体支持。

## OHOS 适配
- HMDFS E046: configure 测试程序无法执行 (SELinux 限制)，在 conanfile.py 中 patch 所有 configure 跳过 `AC_TRY_RUN` 测试
- E007: config.guess 不识别 HarmonyOS，映射 `uname -s` 返回值到 Linux
- E165: shebang `#!/bin/bash` 在 HarmonyOS 不存在，修复为 `/data/service/hnp/bin/bash`
- umask 077 导致 HMDFS 创建的文件权限过严，改为 umask 002
- rpath + LD_LIBRARY_PATH: 构建工具 (如 GMP gen-bases) 链接了 conan 共享库，需要运行时路径
- getpass() 在 HarmonyOS libc 中不可用，为 dvipdfm-x 添加 `#ifdef __OHOS__` 实现
- xetex 链接需要 -lexpat (系统 fontconfig.a 使用 expat 而非 libxml2)

## 依赖
- fontconfig (Conan 包，用于 xetex)

## 功能验证
```bash
tex --version       # TeX 3.141592653 (TeX Live 2026/HarmonyOS)
pdftex --version    # pdfTeX 3.141592653-2.6-1.40.29 (TeX Live 2026/HarmonyOS)
xetex --version     # XeTeX 3.141592653-2.6-0.999998 (TeX Live 2026/HarmonyOS)
luatex --version    # LuaTeX 1.24.0 (TeX Live 2026/HarmonyOS)
mpost --version     # MetaPost 3.00 (TeX Live 2026/HarmonyOS)
mf --version        # Metafont 2.71828182 (TeX Live 2026/HarmonyOS)
dvisvgm --version   # dvisvgm 3.6
synctex --version   # SyncTeX 1.5
```

## 参考
- 官网: https://www.tug.org/texlive/
- 源码: https://mirrors.ctan.org/systems/texlive/Source/texlive-20260301-source.tar.xz
- 构建文档: https://tug.org/texlive/build.html
