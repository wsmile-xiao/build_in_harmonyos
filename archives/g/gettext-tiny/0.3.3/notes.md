# gettext-tiny 0.3.3 适配笔记

## 软件概况
- 上游：https://github.com/sabotage-linux/gettext-tiny（tag v0.3.3）
- 归档：codeload tar.gz，SHA-256 = daff8b4a7863745710ec0b02657fd20bda2d90398f54945751259bb94d6ebffd
- 类型：轻量 gettext 替代 —— 4 个 CLI 工具（msgfmt/msgmerge/xgettext/autopoint）+ 静态 libintl.a
- 构建系统：纯 Makefile（无 configure 脚本），R26 仅静态

## 构建
- `make -j1 CC=clang AR=llvm-ar RANLIB=llvm-ranlib`：rc=0
  - libintl.a（1322B）+ msgfmt/msgmerge（35200B）+ xgettext（脚本）+ autopoint
- `make install DESTDIR=<TEST_PREFIX>`：rc=0，产物入 lib/ include/ bin/ share/gettext-tiny/{m4,data}

## 测试
- 上游：无独立测试入口（无 tests/、无 check 目标、无框架/样例/基准/fixture/脚本），0 用例
- test_package 消费者 test.c：调用 libintl 公开 API（gettext/dgettext/textdomain/bindtextdomain），
  编译链接运行 PASSED rc=0
- 鸿蒙专项 harmonyos_specific_test.c：OHOS(aarch64) 上 libintl API 运行 + msgfmt .po->.mo
  编译产物验证，PASSED rc=0（.mo 102B）

## 关键适配点
1. conanfile.py 不能用 Autotools（无 configure），直接 make（参考 7zip 配方）
2. cpp_info.libs = ["intl"]（libintl.a），package_type=application（含 CLI）
3. libintl.h 默认宏展开 gettext()，真实函数测试需 -DLIBINTL_NO_MACROS=1
4. 无外部依赖；iconv 探测由 Makefile LDLIBS 运行时完成
5. commands.json：type=tool，versions 0.3.3 ref gettext-tiny/0.3.3 binary=true
---

**编译结束**: 2026-09-27 03:30
**最终状态**: published
