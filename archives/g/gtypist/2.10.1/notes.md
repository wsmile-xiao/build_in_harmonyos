# gtypist 2.10.1 适配笔记（GLM-28 起做，GLM-43 接手完成，2026-09-17）

## 编译环境

- 构建系统: autotools（configure + make，GNU Typist ncurses 打字练习工具）
- 编译器: clang（OHOS 15.0.4, aarch64）
- Conan 2.29.1（OHOS 适配版），profile ci/conan/profiles/ohos-aarch64
- 依赖: ncurses/6.6（ohpcd 制品仓，宽字符 ncursesw + formw/menuw/panelw）

## 编译步骤（固化为配方）

```bash
env -u CONFIG_SHELL SHELL=/bin/sh sh <src>/configure --prefix=<pkg> \
    --disable-nls ac_cv_header_libintl_h=no CPPFLAGS=-I<compat-include>
env -u CONFIG_SHELL SHELL=/bin/sh make -j1 MAKEINFO=true MAKEINFOHTML=true
env -u CONFIG_SHELL SHELL=/bin/sh make install MAKEINFO=true MAKEINFOHTML=true
```

## 踩坑与解决（时间线）

1. **CONFIG_SHELL getcwd 必挂（§12.38①，GLM-28 R43 止损根因）**：conan
   profile 的 SHELL/CONFIG_SHELL 指向 hnp bash，在 HMDFS 构建目录下
   autoconf re-exec 自身时 getcwd 失败（"working directory cannot be
   determined"）。toybox sh 同族 pwd 缺陷用绝对路径调用规避。
   修复：`env -u CONFIG_SHELL SHELL=/bin/sh` 显式路由 + 绝对路径。
2. **ncursesw 头检测失败**：conan ncurses 包头文件平铺（include/ncurses.h），
   上游 configure（非 BSD 分支）检测 ncursesw/ncurses.h 且源码
   #include <ncursesw/ncurses.h>。修复：generate() 把依赖头镜像到
   compat-include/（平铺 + ncursesw/ 双布局），configure 命令行
   CPPFLAGS=-I<compat>（build() 手动调 configure，不经 tc.configure_args）。
3. **getopt.c 的 _() 宏引入 gettext**：configure 探测到 libintl.h 头即定义
   HAVE_LIBINTL_H，但目标无 libintl 实现。修复：ac_cv_header_libintl_h=no
   强制 _() 走 (msgid) 透传分支（与 --disable-nls 语义一致）。
4. **doc 与 man 生成工具不可用**：makeinfo/HTML（HMDFS 执行限制 127）、
   help2man（perl，环境不存在）。修复：MAKEINFO/MAKEINFOHTML 占位 true
   （build 与 install 两阶段）+ 预创建 src/gtypist.1 空占位跳过 help2man。
   info/HTML/man 页非交付物核心（与 indent 0001/0002 同教训）。
5. **package() 缺 Autotools import**：GLM-28 原配方 package() 引用
   Autotools 但未 import（此前从未跑到该阶段）。

## 上游测试四维账本（与 manifest.yaml / PR 正文 / test_package/MANIFEST.yml 同源）

| 维度 | 数值 | 说明 |
|------|------|------|
| N_static（静态注册） | 0 | 上游无自动化测试套件：.typ 文件为课程数据非测试，无 TESTS/check_PROGRAMS |
| 通过 | 0 | 同上 |
| 失败/跳过 | 0 | 无 |
| N_consumer（新增消费者） | 1 | test_package/test.sh：包内 gtypist 二进制 3 断言（--version 含 2.10.1 / --help 退出 0 / 非法选项非零退出） |

## 路径 B 判断

判断不成立，按纯路径 A 申报。依据：CONFIG_SHELL 路由为已沉淀知识
（§12.38①），ncursesw 头兼容层为平台工程通用手法，无跨仓库新知识增量。

---

**编译结束**: 2026-09-17 04:2x
**最终状态**: built
