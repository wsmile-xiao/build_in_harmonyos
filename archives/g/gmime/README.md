# gmime

GMime is a C/C++ library for parsing and creating MIME messages and RFC822/MIME message formats.

## 鸿蒙适配

- 构建系统: autotools（GitLab archive 无生成文件，配方内自举 aclocal→autoconf→libtoolize→automake）
- 编译器: clang 15 / musl / OHOS aarch64
- 依赖: glib2/2.88.0（conan 制品仓）+ zlib/1.3.1.1 + pcre2/10.45
- 3.0.6 版本: pan 0.165 前置依赖（开源鸿蒙PC专项积分赛；= 上游 3.0.5 + 配方修订）
- 上游测试: make check 8 个自动化测试，预期 8/8 通过（0001/0002 可移植性处理；未修复版 6 PASS / 2 FAIL，均平台限制）

## 版本

| 版本 | 状态 | 补丁 | 产物 |
|------|------|------|------|
| 3.0.5 | published | 0（仅 gtk-doc.m4 宏文件） | libgmime-3.0.a |
| 3.0.6 | built | 2（0001 iconv 可移植字符集、0002 autocrypt 可选 gpg）+ gtk-doc.m4 宏文件 | libgmime-3.0.a |
| 3.2.7 | built | 0 | gmime-3.2.7-ohos-aarch64.tar.gz |
