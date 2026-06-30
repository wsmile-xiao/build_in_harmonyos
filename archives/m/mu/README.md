# mu

Mu is a tool for dealing with e-mail, stored in Maildir-format. It indexes mail using Xapian and provides tools for searching and viewing.

## 鸿蒙适配

- 构建系统: meson
- 编译器: clang / clang++
- 依赖: glib >= 2.80, gmime >= 3.2.7, xapian-core >= 1.4.22
- 编译选项: `meson setup builddir --prefix=$PREFIX && ninja -C builddir`

## 版本

| 版本 | 状态 | 补丁 | 产物 |
|------|------|------|------|
| 1.14.1 | built | 0 | mu-1.14.1-ohos-aarch64.tar.gz |