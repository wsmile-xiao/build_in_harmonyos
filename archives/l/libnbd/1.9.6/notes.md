# libnbd 1.9.6 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-16
- 编译器: clang/clang++ (OHOS SDK, aarch64)
- 状态: built

## 编译步骤

1. `conan create archives/l/libnbd/1.9.6 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ohos-aarch64`
2. build() 内先 `autoreconf -i`（git tag tarball 无 configure 脚本）
3. configure 传入 `--build/--host=aarch64-unknown-linux-ohos`（config.guess 无法识别
   HarmonyOS）+ 禁用全部可选特性（gnutls/libxml2/fuse/python/golang/bash-completion）
4. `make -j1` 内嵌 OCaml 生成器（tool_requires ocaml/4.14.1.1.4）产出
   lib/api.c、lib/states*.c、include/nbd.h
5. 通过 `make check` 上游测试与 test_package（2 项鸿蒙消费者测试）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 GitHub 超时 | github.com 直连不稳定 | 改用 codeload.github.com 官方 tarball，SHA-256 核验一致 |
| 2 | lang-preflight 误判 mixed(go) | golang/ 绑定子目录的 go.mod 被递归扫描当成 manifest | 核实顶层 autotools C 库主体（C 134 文件 vs go 25 文件仅限 golang/ 绑定），判定应为 C；记录为知识候选 |
| 3 | `tool_requires` 定义报错 | Conan 2 需用 `build_requirements()` | 改用 `build_requirements()` 声明 tool_requires |
| 4 | os.version 未定义 | profile 路径解析回退到 default | 用绝对路径 profile |
| 5 | config.status `subs1.awk Permission denied` | E114 HMDFS umask 077 临时目录不可写 | 修补 configure：去掉 `umask 077 &&` |
| 6 | ocamlc `Unbound module Stdlib` | ocaml 包二进制内嵌构建期缓存路径（.cache/conan2/...），移入本地缓存后失效 | 注入 `OCAMLLIB=<pkg>/lib/ocaml` + `CAML_LD_LIBRARY_PATH=<pkg>/lib/ocaml/stublibs` |
| 7 | generator 字节码 shebang 指向失效路径 | 同上 | 构建 generator 后就地改写 shebang 为当前 ocamlrun |
| 8 | ocamldoc manpages 构建失败 | ocamldoc 字节码 shebang 失效；且 OCaml 绑定本不需要 | configure 时 `OCAMLDOC=no`（HAVE_OCAMLDOC=false，生成器 HAVE_OCAMLC 不受影响） |
| 9 | `struct sockaddr_vm` 不完整类型 | OHOS 定义 AF_VSOCK 宏但无 linux/vm_sockets.h | patches/0001-vsock-header-guard.patch：vsock 分支改为依赖 HAVE_LINUX_VM_SOCKETS_H/HAVE_SYS_VSOCK_H |
| 10 | printenv "Argument list too long" | 把 OCAMLLIB 经 conan env 脚本注入导致环境脚本膨胀 | 改在 build() 内直接 os.environ 设置 |
| 11 | package() 中 self.copy 不存在 | Conan 2 API | 改用 `from conan.tools.files import copy` |

## 源码修改
- patches/0001-vsock-header-guard.patch（lib/connect.c 一处条件编译）

## 测试结论
- 上游 make check：tests/ 11 项（10 PASS + dlopen SKIP 静态无 .so.0）+ common/utils 2 PASS
- 全量声明 58 项（tests/Makefile.am TESTS），当前配置可执行 13 项，12 PASS 1 SKIP
- 详见 reports/upstream-test-ledger.md
---

**编译结束**: 2026-09-17 13:06
**最终状态**: built
