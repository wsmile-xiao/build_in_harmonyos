# hunspell 1.7.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译器: clang/clang++（OHOS SDK）
- 状态: built（conan 配方，待 CI 实跑）
- 系统: HarmonyOS (aarch64)

## 与 1.7.2 参考的差异（本版本从零写 conan 配方）

1.7.2 的 archives/h/hunspell/1.7.2 参考目录只含 manifest/notes/patches，无 conanfile
（旧 ohc-run 手工流程产物）。1.7.3 补齐 conan 配方并复用/再生补丁。

- 1.7.2 的三个补丁（config.guess/config.sub/configure）在 1.7.3 上**不能直接应用**
  —— 1.7.3 重新生成 configure，config.guess/config.sub 升级到 2024 版（结构重构）。
- 实测结论：
  - **config.guess**（2024）无 OHOS 分支 → 手工移植等价 HarmonyOS 识别分支，生成
    `0001-config.guess.patch`（git apply 验证干净）。
  - **config.sub**（2024）**原生支持** `linux-ohos*`（`./config.sub aarch64-unknown-linux-ohos`
    直接回显通过）→ 1.7.3 **不需要** config.sub 补丁。
  - **configure** 的临时目录 hunk 与 1.7.3 上下文基本一致（fuzz 干净应用），用 diff 重新
    生成 `0002-configure.patch`（git apply 验证干净）。

## 关键 configure 处理
- `AM_GNU_GETTEXT([external])`（configure.ac 第 49-50 行）→ 需外部 libintl/msgfmt；
  加 `--disable-nls` 跳过（po/*.gmo 语料已随源码预编译，库消费者不需要）。
- root SUBDIRS = po src man tests；man 页已预生成（EXTRA_DIST），tests 仅在 `make check`
  构建（默认 make 不触发）。
- src/hunspell 产 `libhunspell-1.7.so`（-version-info 1:0:1 → SONAME libhunspell-1.7.so.0），
  头文件装到 include/hunspell/；pkg-config 名 hunspell（hunspell.pc.in，Libs -lhunspell-1.7）。
- 无外部编译依赖（ncurses/readline 仅 --with-readline=no 默认关）。

## 坑与对策
- 包内 libtool 生成的 `.so` 符号链接链（libhunspell-1.7.so → .so.0 → .so.0.0.1）在 HMDFS
  上动态链接器无法解析 → package() 里把别名符号链接替换为真实文件副本（1.7.2 notes 同款）。
- configure 补丁后 conf 临时目录在 ${TMPDIR:-$HOME/tmp} → generate() 注入 TMPDIR 环境变量。
