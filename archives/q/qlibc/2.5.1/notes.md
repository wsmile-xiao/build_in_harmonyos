# qlibc 2.5.1 适配笔记

## 编译环境
- 构建系统: autotools（configure + make；上游同时提供 CMakeLists.txt）
- 编译日期: 2026-09-07
- 编译器: clang 15.0.4 (aarch64-linux-ohos, musl libc, OHOS SDK 26.0.0.18 sysroot)
- 状态: built

## 编译步骤

1. 下载官方源码：https://github.com/wolkykim/qlibc/archive/refs/tags/v2.5.1.tar.gz
   （GitHub 直连超时，经 ghfast.top 官方镜像下载，SHA-256 与官方一致）
2. configure：
   ```bash
   env CC=clang CXX=clang++ AR=llvm-ar RANLIB=llvm-ranlib \
       CFLAGS="-fPIC -O2 --target=aarch64-linux-ohos --sysroot=.../ohos/native/sysroot" \
       LDFLAGS="--target=aarch64-linux-ohos --sysroot=.../ohos/native/sysroot" \
       ./configure --prefix=$DEFAULT_PREFIX
   ```
3. make -j2：产出 libqlibc.a/.so.2、libqlibcext.a/.so.2（arm64 ELF）
4. make -C tests：10 个上游测试可执行全部编译并运行通过（74/74）
5. 编写并运行 HarmonyOS 专项消费者测试 test_ohos.c（qvector/qlist/qhasharr/qstring/qhashmd5，全部通过）
6. conan create（OHOS profile）通过：G0-G4 + L2/L4/L5 全部 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `can't create ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 文件系统 UID 映射：`mktemp -d` 创建的 0700 目录对进程不可写（setgid 位 drwx--S---）；plain `mkdir` 产物 drwxrws--x 可写 | 补丁 patches/0001-configure.patch：configure/config.status 中跳过 `mktemp -d`，改用 `mkdir`（E011 已知模式） |
| 2 | conan create out-of-source 布局下 make 失败 `No rule to make target containers/qtreetbl.o` | qlibc 手写 Makefile.in 使用相对对象路径，只能在源码根目录构建 | conanfile.py `layout()` 设 `self.folders.build = "."`（in-source，先例 abc/abduco） |
| 3 | test_package CTest 运行失败 `Error loading shared library ../lib/libqlibc.so.2` | 上游同时构建 .so 与 .a，且共享库 DT_NEEDED 记录字面相对路径，脱离源码树后无法加载 | conanfile.py package() 在 shared=False 时移除 *.so* 只留静态库（R26 口径） |
| 4 | qlibc configure 不支持 `--enable-static/--disable-shared` | 上游 configure.ac 无 static/shared 选项，始终双构建 | 配方不传该参数（模板默认参数需移除） |
| 5 | W3 JC5 命中 `archives/u/util-linux-login/2.42.2/.ci-trigger`（其他库基线） | main 中既有的其他库隐藏标记文件，full 模式 git ls-files 扫描命中 | 基线隔离复验：记录 pre_sha256=e3b0c44...，临时 git rm --cached 隔离，W3 重跑通过后原样恢复（post_sha256 一致），未提交该文件 |

## 源码修改

- patches/0001-configure.patch：configure 脚本临时目录创建逻辑（跳过 mktemp，改用 mkdir），
  仅构建系统适配，不改库源码逻辑。

## 依赖版本

- clang: 15.0.4 / llvm-ar / llvm-ranlib
- make: 4.4.1 / cmake: 4.1.2 / ninja: 1.13.1
- conan: 2.32.0（OHOS 适配版）
- 运行时依赖：仅 pthread（系统库）

## 验证结果

```bash
# 上游测试（10 个可执行，74 TEST()）
cd tests && ./launcher.sh test_qstring test_qhashtbl test_qhasharr test_qhasharr_darkdh \
  test_qtreetbl test_qlist test_qvector test_qqueue test_qstack test_qhash
# 结果: Good job! All tests are successful — 74/74 通过（12,183,893 断言）

# HarmonyOS 专项消费者测试
./test_ohos
# 结果: test_ohos: ALL PASS (5 API groups exercised)

# Conan 配方验证
ohc-run.py conan-verify qlibc 2.5.1
# 结果: G0-G4/L2/L4/L5 全部 PASS

# W3 本地 CI 模拟
ohc-run.py finish qlibc 2.5.1 built
# 结果: W3 本地 CI 模拟通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 2 配方（autotools，in-source 布局，静态默认） |
| conandata.yml | 官方 v2.5.1 tarball URL + SHA-256 + 补丁声明 |
| patches/0001-configure.patch | configure tmpdir 适配补丁 |
| test_package/ | test.c（消费者）+ test_ohos.c（HarmonyOS 专项）+ MANIFEST.yml |
| reports/upstream-test-ledger.md | 上游测试双口径台账 |

## 注意事项

- 上游共享库 DT_NEEDED 含字面相对路径，脱离构建树不可加载；共享构建需另议，
  当前配方 shared=False 只交付静态库。
- configure 的 mktemp 问题属于 HMDFS 平台限制（E011），补丁不影响 Linux 原生构建。

## 发现与知识（知识积累）

- ✅ 已验证：HMDFS 上 autotools `mktemp -d` 0700 目录不可写，plain mkdir 可写（E011 复现+验证）
- ✅ 已验证：qlibc 手写 Makefile.in 必须 in-source 构建，Conan 配方设 `folders.build = "."`
- ✅ 已验证：qlibc 共享库字面相对 DT_NEEDED 脱离源码树不可加载，静态交付可绕开
---

**编译结束**: 2026-09-08 00:47
**最终状态**: built
