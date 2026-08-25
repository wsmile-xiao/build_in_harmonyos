# ex-vi 050325 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-08-24
- 编译器: clang/clang++
- 状态: built

## 编译步骤

ex-vi 是纯 Makefile 项目，无 `./configure` 脚本。编译流程：

```bash
source .build-context-ex-vi-050325
cd $BUILD_SRC_DIR

# 1. 修改 Makefile（由 0001-Makefile.patch 完成）：
#    - INSTALL=/usr/ucb/install → install
#    - 删除 'size ex' 行
#    - STRIP=-s → 空
#    - 移除交互式 install 检测 (echo q | ex)
#    - 符号链接用 rm -f && ln -s

# 2. 修改 C 源码（由 0002-ex.c.patch, 0003-ex_subr.c.patch 完成）：
#    - sbrk() → mmap()（musl sbrk(>0) 返回 ENOMEM）
#    - 添加 --version / --help 识别

# 3. 修改子目录 Makefile（由 0004, 0005 补丁完成）：
#    - override CFLAGS += 保留 -D 定义和 -I. 路径

# 4. 编译
make CC=clang CFLAGS='-fPIC -O2' PREFIX=/usr/local -j1

# 5. 安装到 DESTDIR
make install DESTDIR=$TEST_PREFIX PREFIX=/usr/local
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make` 编译失败：sub-make CFLAGS 被覆盖 | 顶层 `make CFLAGS=...` 通过环境变量传播到 libterm/Makefile 和 libuxre/Makefile，覆盖了子 Makefile 中的 `-D` 定义和 `-I.` 路径 | 在 libterm/Makefile 和 libuxre/Makefile 中使用 `override CFLAGS +=` 保留原有定义 |
| 2 | `make install` 失败：`/usr/ucb/install: No such file` | OHOS 没有 /usr/ucb/install 路径 | Makefile 中 INSTALL 改为 `install`（PATH 中的标准 install） |
| 3 | `make install` 失败：`size: command not found` | OHOS 没有 `size` 命令 | 删除 Makefile 中的 `size ex` 行 |
| 4 | `make install` 挂起：交互式检测 `echo q \| ex` | Makefile install 目标中有交互式 ex 功能检测，交叉编译环境无法运行 | 移除交互式检测步骤 |
| 5 | `ex` 打开任何文件报 "Out of memory - too many lines in file" | musl libc 的 `sbrk(incr>0)` 返回 ENOMEM（OHOS 不支持 brk 系统调用扩展堆），ex-vi 用 sbrk 分配行缓冲区 | 将 ex.c 和 ex_subr.c 中的 sbrk() 无条件替换为 mmap()（R8: 禁止平台条件编译） |
| 6 | conan test_package `ex --version` 返回非零退出码 | ex-vi 不识别 `--version`/`--help` 参数，当作文件名处理导致错误 | 在 ex.c 中添加 GNU 风格 `--version`/`--help` 识别 |
| 7 | HMDFS 文件系统不支持 make jobserver fifos | `mkfifo: Operation not permitted` | 使用 `-j1` 代替 `-j2` |
| 8 | conan package() 中二进制装到错误路径 | DESTDIR 和 PREFIX 都设为 self.package_folder，导致 `$(DESTDIR)$(PREFIX)` = `package_folder/package_folder/bin/` | DESTDIR 设为空，只用 PREFIX=self.package_folder |
| 9 | finish Step 1 refresh_patch 丢失 C 代码修改 | 子任务把 C 修改写进补丁文件但未应用到 work_dir 源码，refresh_patch 通过 diff orig vs work 重建补丁时只检测到 Makefile 变更 | 手动将 0002/0003 补丁应用到 work_dir 源码后重跑 refresh_patch |

## 源码修改

| 补丁 | 修改文件 | 修改内容 |
|------|----------|----------|
| 0001-Makefile.patch | Makefile | INSTALL 路径修复、删除 size 行、清空 STRIP、移除交互检测、修复符号链接 |
| 0002-ex.c.patch | ex.c | sbrk()→mmap() 行缓冲区分配；添加 --version/--help 识别 |
| 0003-ex_subr.c.patch | ex_subr.c | morelines() 使用 mmap arena 代替 sbrk() |
| 0004-libterm-Makefile.patch | libterm/Makefile | override CFLAGS += 保留 -D 定义 |
| 0005-libuxre-Makefile.patch | libuxre/Makefile | override CFLAGS += 保留 -I. 和 RPMCFLAGS |

## 依赖版本

无外部依赖。ex-vi 自带：
- libterm/ — BSD termcap 库
- libuxre/ — Caldera UNIX regex 库
- mapmalloc — mmap-based malloc

## 验证结果

```
conan-verify: ALL PASS (G0-G4, L2/L4/L5)
  G0: Pre-build risk assessment     ✅
  G1: Recipe completeness           ✅
  G2: conan create (clean build)    ✅
  G3: System library isolation      ✅
  G4: Artifact completeness         ✅
  L2: Platform smoke test           ✅
  L4: checksec security scan        ✅
  L5: Artifact baseline comparison  ✅

Smoke tests:
  ex --version                      ✅ exit 0
  ex --help                         ✅ exit 0
  basic edit (echo "test" | ex)     ✅ exit 0
  file read (ex -s file -c 'p')     ✅ exit 0
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（Makefile 构建类型） |
| conandata.yml | 源码 URL + 5 个补丁引用 |
| patches/0001-0005 | 5 个 OHOS 适配补丁 |
| test_package/ | Conan 测试包（smoke test） |
| commands.json | CLI 工具注册（R38） |
| reports/test-report.md | 测试报告 |
| reports/conan-verify-report.md | Conan 验证报告 |
| reports/upstream-test-check.md | 上游测试用例检查（无上游测试套件） |
| reports/smoke-test-report.md | 自建 smoke test 报告（22 项全 PASS） |

## 注意事项

- sbrk→mmap 改造和 --version/--help 识别均为无条件编译（R8 合规），无需任何 -D 宏开关
- conanfile.py 的 package() 中 DESTDIR 必须为空（不能等于 PREFIX），否则安装路径双重拼接
- HMDFS 不支持 mkfifo，必须用 `-j1` 编译
- refresh_patch 通过 diff orig_dir vs work_dir 生成补丁，所有源码修改必须实际应用到 work_dir（不能只写在补丁文件中）
---

**编译结束**: 2026-08-24 10:16
**最终状态**: published
