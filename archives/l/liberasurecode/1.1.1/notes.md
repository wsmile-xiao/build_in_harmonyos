# liberasurecode 1.1.1 适配笔记

## 编译环境
- 构建系统: autotools（tag tarball 无生成 configure，需 autogen.sh bootstrap）
- 编译日期: 2026-09-22
- 编译器: SDK clang 15 (llvm)，aarch64-linux-ohos
- 状态: built

## 编译步骤

1. `init-build liberasurecode 1.1.1 --url=https://github.com/openstack/liberasurecode/archive/refs/tags/v1.1.1.tar.gz`
   （官方 tag v1.1.1=29f4e69dd5b8211b34cd4ecc87f739bc9f05b8a5；tarball sha256=0646172b…d904）
2. `lang-preflight`：detected=c，通过
3. 探索性编译：`sh autogen.sh`（autoreconf 生成 configure）→ `./configure --prefix=$DEFAULT_PREFIX` → `make -j1` → `make check` → `make install DESTDIR=$TEST_PREFIX`
4. `conan-init` → 修 conandata.yml sha256 → 重写 conanfile.py（bootstrap + OHOS 适配）→ `conan-verify` G1-G4 全 PASS
5. `finish liberasurecode 1.1.1 built`：W2 结构 / R36 依赖 / W3 本地 CI 全部通过（.ci-result.json exit_code=0）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess: unable to guess system type (uname -s = HarmonyOS) | GNU config.guess 无 HarmonyOS 分支；HMDFS 下其 mktemp 临时目录亦不可写 | E007/E160 等价命中：patch-autotools-ohos.pl 补 config.guess/config.sub；conan 配方内显式 `--build/--host=aarch64-unknown-linux-gnu` 绕过猜测 |
| 2 | config.status: could not setup config files machinery (./confiXXXXXX/subs1.awk: Permission denied) | HMDFS 上 `umask 077 && mktemp -d "./confXXXXXX"` 生成 drwx--S--- 不可写临时目录 | E114 等价命中：4ti2 范式在配方 build() 内将 configure 的 mktemp -d 替换为 mkdir 方案 |
| 3 | -Werror,-Wunused-but-set-variable / -Wunused-variable（liberasurecode_test.c 等） | 上游 -Wall -Werror 将 test harness 未使用局部变量升级为硬错误 | E063 等价命中：配方内 werror_flag 追加 `-Wno-error=unused-but-set-variable -Wno-error=unused-variable`（仅 OHOS） |
| 4 | 上游源码含大量无原型声明 `foo()` | C2x/clang15 -Wstrict-prototypes -Wdeprecated-non-prototype | 12 个补丁将 `()` 改为 `(void)`（含 typedef 函数指针与 main），refresh-patch --auto 生成 |
| 5 | tag tarball 无 configure，conan create 直接调 configure 失败 | GitHub tag 归档不含生成脚本 | E460 bootstrap 范式：配方 build_requirements 声明 tool_requires automake/1.18+libtool/2.5.4，build() 内 `bash -e autogen.sh` 后 chmod 辅助脚本 |
| 6 | test/Makefile 以 `$(top_srcdir)/src/liberasurecode.la` 链接，out-of-source 构建找不到 | 上游 Makefile.am 直接引用源码树 .la | 配方 layout 用 `basic_layout(src_folder=".", build_folder=".")` 改 in-source 构建（kismet 范式） |
| 7 | CMakeDeps 消费者报 "Library 'liberasurecode' not found" | 上游库名无 lib 前缀（liberasurecode.a） | package() 重命名为 libliberasurecode.a；libs 声明完整内部归档集 ["liberasurecode","Xorcode","nullcode","liberasurecode_rs_vand"] |
| 8 | 运行时 -204 EBACKENDNOTAVAIL：dlopen(libnullcode.so.1) 失败 | 插件式后端运行时 dlopen 共享库，静态构建缺 .so | 配方同时 --enable-static --enable-shared，runenv_info 注入 LD_LIBRARY_PATH=包 lib 目录 |

## 源码修改

12 个补丁（0001-0012），全部为 C 原型规范化 `()` → `(void)`：
- include/erasurecode/alg_sig.h、include/rs_vand/rs_galois.h、include/rs_vand/liberasurecode_rs_vand.h
- src/builtin/rs_vand/rs_galois.c、src/utils/chksum/alg_sig.c、src/backends/rs_vand/liberasurecode_rs_vand.c
- test/ 下 7 个测试源文件（main() 与 static 函数）

## 依赖版本

- 无运行时依赖（自包含 erasure 库）；构建工具：automake/1.18、libtool/2.5.4（tool_requires）

## 验证结果

```bash
# 上游测试（本地实测，全部 EXIT 0）
./rs_galois_test && ./test_xor_hd_code && ./alg_sig_test \
  && ./liberasurecode_rs_vand_test && ./liberasurecode_test (258 ok) && ./libec_slap
# Conan 门禁
python3 scripts/ohc-run.py conan-verify liberasurecode 1.1.1   # G1-G4 + L2/L4/L5 PASS
# finish（含 W2/W3）
python3 scripts/ohc-run.py finish liberasurecode 1.1.1 built    # .ci-result.json exit_code=0
```

## 知识路径判定（executor_local_required）

- 判定：`knowledge_decision: reuse_existing`（路径 A）
- 等价命中条目（逐字段验证）：E160/E007（config.guess HarmonyOS）、E114（config.status 临时目录 HMDFS）、E063（-Werror 特定类别降级）、E460（tag 源码 bootstrap 工具链）
- 无等价命中候选：in-source .la 链接（E519 为 EXTRA_DIST 场景，不完全等价）、无前缀静态库 CMakeDeps 命名——均为既有方案工程组合，无新增跨库知识价值 → `path_a_no_knowledge`，不创建 DRAFT 草稿
- 快照：knowledge-snapshot-liberasurecode-1.1.1-r01-pc1-9-20260922T072553Z（HEAD=48d9cee684，只读）

## 交付物

PR 文件范围：`archives/l/liberasurecode/1.1.1/**`（conanfile.py/conandata.yml/manifest.yaml/notes.md/patches/0001-0012/test_package/）

## 注意事项

- W3 本地 CI 的 junk_check 在分支无 commit 时回退 full 模式会误扫 main 上其他库历史隐藏标记（cloog/kics 的 .build-closed/.staging-verified）；按 CI 真实语义用 pr.diff（JUNK_PR_DIFF）限定本 PR 文件范围复验通过，未改动任何基线文件
- test_package/test.c 已改为实质 API 调用（R34）：创建/销毁 NULL 后端实例
---

**编译结束**: 2026-09-22 17:57
**最终状态**: built
