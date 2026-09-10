# btyacc 3.0 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile 工程，无 configure 脚本）
- 编译日期: 2026-09-05
- 编译器: clang/clang++（toolchain: /data/service/hnp/bin/clang）
- 状态: built

## 编译步骤

1. `make CC=clang LINKER=clang -j1` — 编译生成 btyacc 可执行文件
   - 上游 Makefile 硬编码 `CC=gcc`、`LINKER=gcc`、`LDFLAGS=-static`
   - 本环境无 gcc，用 clang 覆盖编译与链接；`-static` 链接成功（arm64 静态 ELF）
   - `skeleton.c` 由 `awk -f skel2c btyaccpa.ske` 自动生成
2. 上游测试：`test/*.y` 共 7 个语法文件全部解析通过（生成 y_tab.c/y_tab.h）
3. `make install` 目标不可用（`cp btyacc.exe /bin`，硬编码且文件名错误），
   改为在 conanfile.py package() 中手动 copy 二进制到 bin/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接阶段 gcc: No such file or directory | 上游 Makefile 硬编码 LINKER=gcc，环境只有 clang | make 时传 `LINKER=clang`（配方 build() 中从工具链 conf 取编译器，R33） |
| 2 | 上游源码下载失败 | GitHub 直连超时（网络不可达），ghfast.top 镜像可达 | 经 ghfast.top 镜像下载官方 v3.0 tag tarball，SHA-256 校验一致后置入 TMPDIR/builds 再 init-build |
| 3 | Makefile install 目标不可用 | `cp $(PROGRAM).exe /bin` 硬编码且文件名错误，不支持 DESTDIR | 配方 package() 手动 `copy(self, "btyacc", ...)` 到 package bin/ |
| 4 | R01 版本号 "3" 被 Conan 2.29.1 拒绝 | Conan 版本校验正则 `^[a-z0-9_][a-z0-9_+.-]{1,100}\Z` 要求 ≥2 字符 | R02 任务版本号改为 "3.0"（与上游 v3.0 一致），conan-verify 通过 |

## 源码修改

无源码修改、无补丁。仅配方层处理（编译器覆盖 + 手动打包）。

## 依赖版本

无外部依赖。仅 C 标准库，静态链接。

## 验证结果

```bash
$ btyacc -V
usage: btyacc [-dlrtv] [-b file_prefix] [-S skeleton file] filename   # 可执行
$ for y in test/*.y; do btyacc -d "$y"; done   # 7/7 PASS，均生成 y_tab.c
```

test_package smoke test：btyacc 解析最小语法并生成 C 解析器输出。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 纯 Makefile 工具型配方（application，R38 tool 声明 commands.json） |
| conandata.yml | 官方 GitHub v3.0 tarball + SHA-256 |
| test_package/ | test.sh 消费者冒烟测试（R34 实质执行被测工具） |
| commands.json | 软件级 tool 声明 |

## 注意事项

- R38：产物为可执行文件 btyacc，软件级 commands.json 已声明
- 上游 v3.0 为 2012 年最后发布版本，工程老旧但可干净编译
---

**编译结束**: 2026-09-05 16:44
**最终状态**: published
