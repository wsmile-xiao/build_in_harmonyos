# XKeyboard Config 2.42 编译笔记

## 编译日期
2026-05-30

## 关键问题
xsltproc 运行失败，缺少 libxml 符号

## 解决方案
设置正确的 LD_LIBRARY_PATH：
```bash
export LD_LIBRARY_PATH="/data/service/hnp/libxslt.org/libxslt_1.1.39/lib:/data/service/hnp/libxml2.org/libxml2_2.11.9/lib:$LD_LIBRARY_PATH"
```

## 编译步骤
```bash
meson setup build --prefix=$PREFIX
ninja
ninja install
```

## 安装内容
- XKB rules 文件 (rules/base.xml, rules/evdev.xml)
- XKB symbols 文件
- XKB keycodes 文件
- XKB compat 文件

## 预编译包
- xkeyboard-config-2.42-ohos-aarch64.tar.gz (3.4M)
- 包含: share/X11/xkb/