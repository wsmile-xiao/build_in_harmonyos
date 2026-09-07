# DRAFT-postgresql-18.3-make-args-shell-quote

> 草稿知识项 — conan make args 的 shell 引号剥离与 Makefile.global 改写方案
> 来源：postgresql 18.3 Conan 配方化（feat/postgresql-18.3，2026-09-03）
> 同 stem 配对：`knowledge/drafts/DRAFT-postgresql-18.3-make-args-shell-quote.kv`

## 问题（现象 / error_signature）

- 目标：给所有可执行文件加可重定位 rpath `$ORIGIN/../lib`
  （DESTDIR 打包后 configure 期绝对 prefix 的 rpath 失效为 `//lib`，
  psql 等 21 个链接 libpq.so.5 的工具运行时加载失败）。
- 首选尝试（失败）：`autotools.make(args=["-j8",
  "LDFLAGS_EX=-Wl,-rpath,'$$ORIGIN/../lib'"])`
  → readelf 显示 `RUNPATH=[//lib:/../lib]`（$ORIGIN 变空串）。

## 根因（root_cause）

1. conan `Autotools.make()` 把 args **纯拼接**进命令行，
   `self.run()` 以 `sh -c`（shell=True）执行。
2. 外层 shell 按词法把参数中的单引号**剥离**（`'...'` 内字面通过但引号不进 make）。
3. make 收到无引号保护的 `$$ORIGIN/../lib`，recipe 展开 `$$`→`$` 后，
   子 shell 把 `$ORIGIN` 当作未定义 shell 变量展开为**空串**。
4. 链接器收到 `/../lib`——四层传递（conan→sh→make→recipe shell）中
   "字面量进入产物"的需求被逐层破坏。

## 可复用方案（rec_approach: rewrite-makefile-global-after-configure）

1. **configure 之后直接改写 build 树的 Makefile 全局文件**（纯文本，不经 shell）：
   ```python
   autotools.configure()
   replace_in_file(
       self,
       os.path.join(self.build_folder, "src", "Makefile.global"),
       "LDFLAGS_EX = \n",
       "LDFLAGS_EX = -Wl,-rpath,'$$ORIGIN/../lib'\n",
   )
   autotools.make(args=["-j8"])
   ```
   - make 展开 `$$`→`$`；配方 shell 的单引号在（此时已是 Makefile 文本的一部分）
   保留字面量；链接器正确记录 `$ORIGIN/../lib`。
2. make 命令行只传普通参数（`-j8`），不传含 `$`/引号的变量。
3. 可重定位性验收：把 `bin/psql` + `lib/libpq.so.5` 复制到任意目录结构，
   清空 `LD_LIBRARY_PATH` 后直接运行。

## 适用条件

- 需要向 make 传递含 `$`、引号、空格等特殊字符的变量；
- 需要 `$ORIGIN` 相对 rpath 的 DESTDIR 打包（conan Autotools 默认
  `--prefix=/` + `DESTDIR=package_folder` 使 configure 期 rpath 失效）；
- PostgreSQL（`LDFLAGS_EX` 无 configure 入口，仅 make 层变量）及其他类似项目。

## 反例（不适用场景）

- 变量值不含特殊字符时（如 `-j8`），args 直传没有问题，无需改写；
- CMake 项目（set_target_properties/BUILD_RPATH 语义不同）；
- conan 未来的版本若改变 run() 的 shell 语义，需重新实测四层传递行为。

## 验证证据（真实命令 + 结果）

- 失败复现：make 命令行传参 → `readelf -d psql` 显示
  `RUNPATH=[//lib:/../lib]`，W3 L2 二跑仍 21/35 失败；
- 修复后：`readelf -d psql` 显示
  `RUNPATH=[<prefix>/lib:$ORIGIN/../lib]`（$ORIGIN 字面保留）；
  psql+libpq.so.5 复制到任意 bin/lib 结构，无 LD_LIBRARY_PATH
  运行成功（`psql (PostgreSQL) 18.3`）；
- W3 三跑 L2 **35/35 全 OK**，Build Summary 100%。

## 限制与恢复条件

- 改写目标 `src/Makefile.global` 的路径绑定 PG 布局；
  其他项目应定位其等价的全局 Makefile；
- `replace_in_file` 的匹配串（`"LDFLAGS_EX = \n"`）绑定 configure
  生成的精确文本，PG 升版本若改变该行格式需同步调整；
- 恢复条件：conan 修复 args 的 shell 转义（或 run 不再 shell=True）后
  可回归 args 直传，但 Makefile 改写方案本身依旧稳健无副作用。
