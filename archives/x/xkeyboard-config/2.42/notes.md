# XKeyboard Config 2.42 编译笔记

## 编译日期
2026-08-09 (Conan 配方适配)

## 构建系统
Meson + Ninja

## 关键问题
1. xsltproc 运行需要 libxslt 和 libxml2 共享库
   - 解决方案：设置 LD_LIBRARY_PATH 包含 HNP 安装的库路径
   ```bash
   export LD_LIBRARY_PATH="/data/service/hnp/libxslt.org/libxslt_1.1.39/lib:/data/service/hnp/libxml2.org/libxml2_2.11.9/lib:$LD_LIBRARY_PATH"
   ```

2. verify-group-names 测试失败（平台限制）
   - OHOS 平台不支持符号链接，tarball 中的符号链接被解压为普通文件
   - 导致测试发现额外的组名（japan, korean, esperanto 等）
   - 构建产物中这些文件已被 meson 的 install_subdir(exclude_files) 排除
   - 不影响构建产物的正确性

## 编译步骤
```bash
meson setup build --prefix=$PREFIX --datadir=share -Dxkb-base=share/X11/xkb
ninja -C build
meson install -C build
```

## 安装内容
- XKB rules 文件 (rules/base.xml, rules/evdev.xml, rules/base.lst, rules/evdev.lst)
- XKB symbols 文件 (symbols/*)
- XKB keycodes 文件 (keycodes/*)
- XKB compat 文件 (compat/*)
- XKB types 文件 (types/*)
- XKB geometry 文件 (geometry/*)
- man page (man/man7/xkeyboard-config.7)
- pkg-config 文件 (pkgconfig/xkeyboard-config.pc)
- 国际化翻译 (locale/*/LC_MESSAGES/xkeyboard-config.mo)

## Conan 配方
- package_type: application (数据包，无库无可执行文件)
- 构建系统: Meson (MesonToolchain + Meson helper)
- 依赖: 无 Conan 依赖 (xsltproc 为系统工具)
- 测试: test_package.py 验证 XKB 数据完整性
---

**编译结束**: 2026-08-09 01:54
**最终状态**: built
