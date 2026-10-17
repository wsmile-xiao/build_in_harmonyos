# c-algorithms 1.2.0 适配笔记

## 编译环境
- 构建系统: autotools (configure + make, libtool)
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

1. `ohc-run.py init-build c-algorithms 1.2.0 --url=https://codeload.github.com/fragglet/c-algorithms/tar.gz/refs/tags/c-algorithms-1.2.0 --tar tar.gz`
2. `ohc-run.py lang-preflight c-algorithms 1.2.0 --src $BUILD_SRC_DIR` → 语言匹配 cpp ✅ (源文件 34 个, 主体 97%)
3. 因上游 tarball 为 git snapshot（无预生成 configure/autotools 内含旧 ltmain.sh 1.5.22），先用
   libtool 2.4.7 的 ltmain.sh 替换旧版，再 `autoreconf -i -f` 生成 configure + Makefile.in
4. 生成文件打 OHOS 补丁：config.guess 增加 HarmonyOS 分支；configure umask 077->022 (E129)
5. `./configure --prefix=... --disable-shared --enable-static` → make -j2 → 15/15 上游测试全过 → make install DESTDIR staging

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 在 HarmonyOS 上报 unable to guess system type (dummy.c permission denied) | 生成的 config.guess 无 ohos 识别，且 HMDFS 下 umask 077 临时目录不可写 | config.guess 增加 `*:HarmonyOS:*:*` 分支输出 `aarch64-unknown-linux-ohos`；configure 临时目录 umask 077->022 |
| 2 | libtool 编译报 `X--mode=compile: inaccessible or not found` | 上游捆绑 autotools/ltmain.sh 为 libtool 1.5.22，与 HarmonyOS mksh 不兼容 | 用系统 libtool 2.4.7 的 ltmain.sh 替换后重新 autoreconf + configure |
| 3 | 上游 tarball 无预生成 configure | git snapshot 仅含 configure.ac/Makefile.am | autoreconf bootstrap；conanfile.py 内置 generated-build 快照兜底（CI 无 automake 时用） |
| 4 | Release profile 下 test-queue 死循环风险 (R09) | test-queue.c 将 queue 操作放进 assert() 实参，-DNDEBUG 剥落后 while 空转 | test/Makefile.in 烘焙 `AM_CFLAGS += -UNDEBUG`（仅测试目标） |

## 源码修改

- patches/0001-config-guess-ohos.patch — config.guess 增加 HarmonyOS/ohos 平台识别
- patches/0002-configure-umask-022.patch — configure 临时目录 umask 077->022（E129）
- test/Makefile.in (generated-build 快照内) — VPATH 安全 `-I$(top_srcdir)/src` + `-UNDEBUG`

## 依赖版本

无第三方强制依赖（纯 libc 数据结构库）。

## 验证结果

```bash
make check  # 15/15 PASS (test-alloc-testing, arraylist, avl-tree, binary-heap,
            # binomial-heap, bloom-filter, cpp, list, slist, queue,
            # compare-functions, hash-functions, hash-table, set, trie)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Autotools 配方（R26 静态、generated-build 快照兜底、AUTOMAKE=true） |
| conandata.yml | 官方 codeload URL + sha256 + OHOS 补丁 |
| test_package/ | CMake consumer 测试 (queue/list/slist/arraylist/hashtable) |
| generated-build/ | 已打补丁的 configure/Makefile.in/autotools 快照 |

## 注意事项

- upstream 1.2.0 tag 为带注释 tag `c-algorithms-1.2.0`，peel 后 commit f91ea029ad0655dd7ec3e77ea7426c47608633ee
- conan create 在 CI（无 automake）下走 generated-build 快照路径，不触发 autoreconf
- config.sub (libtool 2.4.7) 已原生支持 ohos，无需单独补丁（1.0.0 需要是因为其快照较旧）
---

**编译结束**: 2026-09-22 21:12
**最终状态**: built
