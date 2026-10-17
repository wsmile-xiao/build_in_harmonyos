# picoc (PicoC)

微型 C 语言解释器（PicoC），面向脚本/嵌入式/机器人等场景，由 Zik Saleeba 编写，
上游版本 v2.1（功能冻结），License: New BSD（BSD-3-Clause）。

## 特性
- 核心 C 源码约 3500 行，体积小，易于移植（x86/arm/powerpc/sparc/blackfin 等已验证）
- 内置常用 C 标准库（stdio/math/string/stdlib/time/errno/ctype/unistd 等）
- 交互式命令行（GNU readline 行编辑）

## OHOS 适配要点
1. **构建**：纯 Makefile（无 configure）。默认 `-DUNIX_HOST` 编译并链接
   `-lreadline -lm`。readline 为静态包（依赖 ncurses/6.6），链接期还需追加 `-lncursesw`。
2. **补丁 `patches/0001-cstdlib-stdio.c.patch`、`patches/0002-cstdlib-string.c.patch`、`patches/0003-cstdlib-unistd.c.patch`**（详见版本 manifest knowledge_gained）：
   - `sizeof(FILE)` 在 musl 下非法 → `PICOC_SYSTEM_FILE_SIZE` 常量；
   - `gethostid/getpass/ualarm` 为 glibc 专有 → `__GLIBC__` 守卫剔除；
   - `index/rindex` BSD 别名缺失 → `strchr/strrchr`。

## 测试
上游测试入口：`make test`（51 项 `.test` 用例，stdout 与 `.expect` diff 比对），
在 OHOS aarch64 本机全部通过。

## 参考
- 上游：https://gitlab.com/zsaleeba/picoc （原 http://picoc.googlecode.com）
- pkgsrc `lang/picoc`（DISTNAME=picoc-2.1）、FreeBSD ports `lang/picoc`（USES=readline）
