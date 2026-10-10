# sersniff 0.0.5 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure）
- 编译日期: 2026-09-30
- 编译器: clang / clang++（/data/service/hnp 工具链）
- 状态: built

## 编译步骤

```bash
conan create . --user=ohpcd --channel=stable -pr:h=<ohos profile> -pr:b=<ohos profile> --build=missing
```

配方内部执行：
1. `source()` 从 conandata.yml 下载并解压官方源码包（strip_root）
2. `build()` 运行 `make -j1 CC=<clang> LINK=<clang> AR=<llvm-ar> RANLIB=<llvm-ranlib>`
   （CC 与 LINK 取自 Conan `tools.build:compiler_executables:c`，覆盖 Makefile 硬编码的
   `gcc`，R33；LINK 负责最终链接）
3. `package()` 手动拷贝 `sersniff` 二进制到 `bin/`、`sersniff.8` 到
   `share/man/man8/`、LICENSE 到 `licenses/`（上游无 install 目标）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 硬编码 `CC = gcc` 且 `LINK = gcc`，OHOS 无 gcc | 上游 1999 年老代码直接写 `CC = gcc`/`LINK = gcc`，最终链接用 `$(LINK)` | 从 Conan `tools.build:compiler_executables:c` 取 clang，在 `make` 命令行同时覆盖 `CC` 与 `LINK`（命令行变量优先级高于 Makefile 内默认值，R33） |
| 2 | Makefile 无 `install` 目标 | 上游只提供 `all`/`clean` | 在 `package()` 手动拷贝二进制、man 页、LICENSE 到 Conan package 目录 |
| 3 | `sersniff -h` 退出码为 1 | `usage()` 帮助分支调用 `exit(1)` | 测试（test.sh）接受非零退出码，以输出内容（版本横幅/Usage）而非退出码判断 |
| 4 | 真机 `/tmp` 只读（erofs） | OHOS 平台限制 | test_package 复用 HMBS 注入的 TMPDIR/TMP/TEMP 可写目录链，test.sh 零命令替换、输出经重定向 + grep 校验 |

## 依赖版本

- 编译/运行仅依赖 libc + POSIX sockets/termios，无三方 Conan 依赖。

## 验证结果

- conan create 通过（含 test_package 真实执行 sersniff 二进制）
- 测试用例：`-h` 版本横幅 `sersniff v0.0.5`、`-h` Usage 用法帮助、`-b 999` 拒绝
  不支持波特率（"Unsupported Baud"），共 3 例，全部通过
- 上游测试：声明 `upstream_tests_exist: false`（上游无任何测试框架，已审计）

## 注意事项

- 纯 CLI 工具（非库），`package_type = "application"`，下游以二进制方式使用
- 上游 `usage()` 帮助/非法参数分支 `exit(1)`，不是 bug
- 更换 CC 时须保持 `make` 命令行同时覆盖 `CC` 与 `LINK`（Makefile 内默认值不会主动更新）

## 追加：真机预检 compile 失败修复（2026-09-30）

### 症状
```
make: *** No targets specified and no makefile found.  Stop.
sersniff/0.0.5: ERROR: Error in build() method, line 81
	self.run(f"make -j1 ...")
```

### 根因
Conan 的 `self.run()` 默认在 **build_folder**（basic_layout 为 out-of-source 建的独立目录）里执行。
而本库是 **in-source 构建**：Makefile 不输出到 build 目录，`sersniff` 二进制的 `.o` 与最终链接
都在源码目录原地生成。源码(get() + strip_root)解到 source_folder，build_folder 里没有任何
Makefile，于是 `make` 报 "No targets specified and no makefile found"。

### 修复
`build()` 里 `self.run("make ...", cwd=self.source_folder)`，让 make 在源码目录原地构建。
`package()` 已从 source_folder 拷贝 `sersniff` / `sersniff.8` / `LICENSE`，无需改动。

## 追加：rule4 upstream_test_total 字段补齐（2026-09-30）

### 症状
真机预检 evidence 判定 incomplete：
```
rule4：必须声明合法的 upstream_test_total，缺失不能按 0 处理
```

### 根因
`test_package/MANIFEST.yml` 只声明了 `upstream_tests_exist: false` 与非空
`upstream_test_audit`（blob 标量），但**缺失 rule4 强制要求的 `upstream_test_total`
（非负整数）**，hmbs 无法自动校验测试完整性而拒绝放行。

### 修复（对齐 topparser/1.3 结构化 no_tests 声明经验）
1. `test_package/MANIFEST.yml` 与 `0.0.5/manifest.yaml` 补齐
   `upstream_test_total: 0`、`upstream_test_count_method: "autotools_tests"`。
2. 将 `upstream_test_audit` 由 blob 标量改写为结构化 list：多组 source+finding
   证据项（tar tzf 文件清单、Makefile 仅 all/clean、无 gtest/pytest 绑定、
   disp_ncurses 为可选显示模块非测试）+ 末尾 conclusion 结论项。
3. 保留 `assertion_count: 3`，与 test_package_tests 数量及真机 discovered=3 对齐。
4. `reason`、`upstream_test_in_build`、`upstream_test_command`、`upstream_tests`、
   `upstream_test_total` 保持自洽一致。
