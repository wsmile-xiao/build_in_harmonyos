# libgsf 1.14.58.1 适配笔记（abiword-plugin-sdw 编译协作者验证归档）

> 本任务为**复用**：配方由 abiword-plugin-bmp 任务完整适配并验证，本任务将配方
> 复制到 sdw 分支归档并重新本地验证（conan create + conan-verify 八道门禁）。

## 编译环境
- 构建系统: autotools（GitLab release 归档无 configure → build() 内 autoreconf 引导）
- 编译日期: 2026-08-14
- 编译器: clang 15.0.4（aarch64-linux-ohos，OHOS PC）
- 状态: built（conan-verify 8/8 通过；ohpcd 未发布 libgsf，不强行上传）

## 编译步骤
1. W0: `bash ci/scripts/preflight_check.sh libgsf/1.14.58` → glib/libxml2/zlib 均已发布，通过
   `conan download --only-recipe` 复核
2. W1: `git checkout main && git pull origin main && git checkout feat/abiword-plugin-sdw-3.0.8`
3. init-build: `ohc-run.py init-build libgsf 1.14.58 --url=<GitLab archive> --no-download`
   （context 指向 ~/tmp/builds，已 source 后 export 覆盖到 worktree 内 work/builds/）
4. 配方同步: 逐文件研读 bmp 配方（conanfile.py/conandata.yml/patches/test_package/reports）
   后 `cp -r` 复制到 sdw 归档，`diff -r` 复核与 bmp 一致，无改动
5. conan create: 从 sdw 归档目录实际执行，完整从源码构建
   （autoreconf --force --install → configure --disable-gtk-doc --disable-nls → make -j1 → install）
   产物: libgsf-1.so.114.0.58 + gsf/gsf-vba-dump/gsf-office-thumbnailer + libgsf-1.pc
6. conan-verify: `ohc-run.py conan-verify libgsf 1.14.58` → G0-G4 + L2/L4/L5 八道门禁全部 PASS
7. finish: `ohc-run.py finish libgsf 1.14.58 built`
   - W3 本地 CI 模拟（setup.sh + build_and_test.sh）通过（阻塞门禁）
   - .ci-result.json 由 finish 自动写入（integrity_hash 防伪造）
   - step5b（W4 知识图谱完整性）因全库预存 E219/E253/E305 root_cause 为空 未通过
     —— 全局既有问题，非本任务引入，knowledge/ 不在本任务写权限内

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitLab 归档无 configure | 非 release tarball | build() 内 `autoreconf --force --install` 引导 |
| 2 | configure 不识别 aarch64-*-ohos (E007) | config.guess/sub 无 OHOS 分支 | 0001/0002 补丁 |
| 3 | autoreconf 强制调用 gtkdocize (E089 相关) | configure.ac 含 GTK_DOC_CHECK | 0003-0006 stub 补丁（gtk-doc.make/gtkdocize/m4 宏/configure.ac） |
| 4 | make 并行 jobserver FIFO 禁止 (E074) | HMDFS + SELinux | `make -j1` |
| 5 | 链接选中旧静态 glib 缺符号 (E107/E142) | 全局 LDFLAGS=-L/usr/local/lib | LDFLAGS 用 conan 依赖 libdirs 前置 + -lintl |
| 6 | config.status 无法写临时目录 (E129/E167) | HMDFS mktemp setgid 权限 | ac_tmp 固定到预创建 fixed_tmp |
| 7 | 上游 make check 14/14 无法运行 | OHOS 预装 perl 缺 XML::Parser（需 Expat C 库） | 安装 XML::Parser 2.59 + Expat 2.7.3 后实跑 11/14 通过（详见验证结果） |

## 源码修改
补丁（均为 git a/b 前缀格式，strip: 1，6 个）：
- 0001-config.guess.patch: OHOS 适配 config.guess（识别 aarch64-*-ohos）
- 0002-config.sub.patch: OHOS 适配 config.sub（识别 ohos* / linux-ohos）
- 0003-gtk-doc.make.patch: gtk-doc.make stub
- 0004-gtkdocize.patch: gtkdocize stub 脚本
- 0005-m4-ohos-gtkdoc-stub.m4.patch: GTK_DOC_CHECK stub m4 宏
- 0006-configure.ac-gtkdoc.patch: configure.ac 注释掉无条件 GTK_DOC_CHECK

## 依赖版本
- glib/2.84.0.1（ohpcd 已发布）
- libxml2/2.15.3.1（ohpcd 已发布）
- zlib/1.3.1.1（ohpcd 已发布）

## 验证结果
```bash
# conan create（从 sdv 归档目录，完整从源码构建）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → 构建成功，test_package 100% tests passed (1/1)

# conan-verify 八道门禁
python3 scripts/ohc-run.py conan-verify libgsf 1.14.58
# → G0-G4 + L2/L4/L5 全部 PASS

# 上游 make check perl 测试实跑（2026-08-20，本机 OHOS，XML::Parser 2.59 + Expat 2.7.3）
# 环境: PATH=~/bin（zipinfo 软链）; LD_LIBRARY_PATH=conan glib/libxml2/libgsf 库目录
# 前置: make test-ole test-iconv test-csv test-compress 等 check_PROGRAMS（构建目录缺省未编译）
for t in t1000-zip-single t1001-zip-multiple t1002-zip-aaaa t1003-zip-noise \
         t1004-zip-zip64 t1005-zip-nonseekable t1100-ole t1101-ole-many \
         t2000-iconv t2001-csv t2002-compress t9999-epilogue; do
  perl ~/.conan2/p/<libgsf-src>/tests/$t.pl   # 11 PASS
done
perl ~/.conan2/p/<libgsf-src>/tests/t8000-valgrind-zip.pl   # SKIP (无 valgrind)
perl ~/.conan2/p/<libgsf-src>/tests/t8020-valgrind-ole.pl   # SKIP (无 valgrind)
# → 11 PASS / 1 FAIL (t2000-iconv 平台 glib 差异) / 2 SKIP (valgrind 缺失)

# 产物
conan list "libgsf/1.14.58#*:*"   # recipe 343a41cf + armv8 包 b7b65de8
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（CI 输入） |
| conandata.yml | 源码 URL + sha256 + 6 补丁声明（CI 输入） |
| patches/ | 6 个 OHOS 适配补丁（CI 输入） |
| test_package/ | 消费者 L1 测试（conanfile.py + test.c + MANIFEST.yml，CI 输入） |
| reports/ | conan-create.log + conan-verify-report.md + test-report.md |
| .ci-result.json | W3 本地 CI 结果（finish 写入，含日志哈希） |

## 注意事项
- 下游 abiword-plugin-sdw 通过 `libgsf/1.14.58` conan 依赖解析；本地 cache 已有
  完整配方 + armv8 共享库包（shared=True），下游 conan create 直接复用
- ohpcd 制品仓未发布 libgsf（已知），发布随主任务发布流程处理
- make check 上游 perl 测试：安装 XML::Parser 2.59（Expat 2.7.3）后实跑 14 项 → 11 通过 / 1 失败（t2000-iconv，OHOS glib 2.84 的 g_convert_with_fallback 对欧元符号输出单字节 '*'，上游输出 "\u20ac" 文本，平台 glib 行为差异非库缺陷）/ 2 跳过（t8000/t8020 valgrind，OHOS 无 valgrind，exit 77 标准 SKIP）

**编译结束**: 2026-08-14
**最终状态**: built
