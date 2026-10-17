# omega 2.0.0 适配笔记

## 编译环境
- 构建系统: autotools（configure + make，automake serial harness）
- 上游包: xapian-omega 2.0.0（Xapian Omega，CGI 搜索应用 + omindex 索引器）
- 源码: https://oligarchy.co.uk/xapian/2.0.0/xapian-omega-2.0.0.tar.xz
  sha256 `85088a16cf64ea676d0856813244909f132e1b32013a56928c40a1e333a6734a`（与上游一致，5,823,212 B）
- 编译日期: 2026-09-10
- 编译器: clang 15.0.4 / LLVM (OHOS aarch64, libc++, musl)
- 状态: built（conan create 通过后由 finish 更新）

## 编译步骤

依赖注入（全部来自 ohpcd 制品仓，禁止 --build=missing，R36 已核验）：

```bash
conan install --requires=xapian-core/2.0.0 --requires=zlib/1.3.1.1 \
    --requires=pcre2/10.47 --requires=libmagic/5.48 \
    -g PkgConfigDeps -g AutotoolsDeps -g VirtualBuildEnv -g VirtualRunEnv \
    --deployer=full_deploy -of $DEPS
```

探索构建（真机，日志见文末路径）：

```bash
export XAPIAN_CONFIG=$DEPS/binfix/xapian-config   # 修正 prefix 的副本，见问题#2
export PKG_CONFIG_PATH=$DEPS                       # libpcre2-8 / libmagic / zlib 的 .pc
sh ./configure --prefix=$DEFAULT_PREFIX            # rc=0
make -j2                                           # rc=0
make install DESTDIR=$TEST_PREFIX                  # rc=0
MAGIC=$DEPS/full_deploy/host/libmagic/5.48/Release/armv8/share/misc/magic.mgc \
LD_LIBRARY_PATH=<xapian-core>/lib:<zlib>/lib make check   # rc=0, 11/11
```

配方内等价逻辑：generate() 用 Environment 注入 XAPIAN_CONFIG（修正副本）、
PKG_CONFIG_PATH（generators 目录的 .pc）、MAGIC（libmagic 包内 magic.mgc）、
LD_LIBRARY_PATH（libxapian.so）；build() OHOS 分支沿用 xapian-core/2.0.0 已验证的
`CC="bash clang"` wrapper + llvm-ar/ld.lld 命名法（W0b 历史踩坑比对），随后
`make` 并在 can_run 保护下执行 `make -j1 check`（R51 上游测试入 build）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: `cannot guess build type` | config.guess(2025-07-10) 不识别 `uname -s`=HarmonyOS | 补丁 0001/0002（config.guess 输出 aarch64-unknown-linux-ohos、config.sub 接受 linux-ohos），与 xapian-core/2.0.0 已发布补丁同源同上下文，`patch --dry-run` 先行验证 |
| 2 | `xapian-config --cxxflags` 报 `-I//include`，构建找不到 xapian.h | 已发布 xapian-core/2.0.0 包内 bin/xapian-config 的 `prefix="/"` 是 conan install 前缀重写产物，静态读取无法重定位；xapian.m4 又强制要求可执行的 xapian-config | omega 配方 generate() 把该行改写为依赖实际 package_folder，生成 build_folder 私有副本（R49：不碰共享前缀），经 XAPIAN_CONFIG 注入 |
| 3 | make check: omindextest FAIL "Failed to load the file magic database" | 静态 libmagic.a 默认搜索路径（/usr/share/misc 等）在 OHOS 不存在，magic.mgc 在 libmagic 包 share/misc/ 下 | 注入 `MAGIC=<libmagic>/share/misc/magic.mgc`（配方 Environment，构建期与 make check 同效）；复跑 11/11 PASS |
| 4 | configure tmp 目录创建失败风险（toybox mktemp + HMDFS umask） | HMDFS 下 `umask 077 && mktemp -d` 组合产生不可读目录/失败（E046 同类） | 补丁 0003：umask 077→022（同 xapian-core/2.0.0 补丁 0004 思路，本包 configure 仅 2 处） |
| 5 | refresh-patch 首轮误收 4 个生成物补丁（mhtml2html 等 shebang 路径变化） | configure 重新生成 .in 模板，非源码修改（R6） | 从 .orig 还原 4 文件后重跑 refresh-patch，补丁收敛为 3 个真实修改 |

其他记录：
- `id: inaccessible or not found`（configure 探测 toybox 无 id）——无害，autoconf 回退。
- 发布 tarball 默认 `--enable-documentation` off，docs 目标 "Nothing to be done"，无需 help2man/rst2man。
- omegatest.pl：`faketime` 工具缺失时自动跳过相关内部用例（脚本自带保护），注册用例仍 PASS。
- check_PROGRAMS 中 omindexcheck/timecheck 构建但不在 TESTS 注册表（供其他用例调用），如实不计入统计。
- omega CGI 查询参数为 `P=`（omegatest.pl 实证）；`query=` 会被静默忽略。
- 包布局：bin/ 为 5 个 CLI（omindex, scriptindex, omindex-list, dbi2omega, mbox2omega），
  omega CGI 与 perl 过滤脚本在 lib/xapian-omega/bin/（上游 --program-prefix 布局），
  package_info runenv_info 已把该目录挂 PATH。

## 源码修改

补丁（patches/，由 refresh-patch --auto 生成，均为上游文件平台适配，无 `__OHOS__` 宏，R8 合规）：
- 0001-config.guess.patch：+11 行，HarmonyOS → aarch64-unknown-linux-ohos
- 0002-config.sub.patch：+4 行，接受 ohos-linux 三元组
- 0003-configure.patch：2 处 umask 077→022

## 依赖版本

| 依赖 | 版本 | 来源 | 备注 |
|---|---|---|---|
| xapian-core | 2.0.0 | ohpcd 制品仓（recipe rev b8c36347…, pkg 4178e02c…，2026-09-10 发布） | configure XO_REQUIRE(>=2.0.0)，1.4.26 不可降级 |
| zlib | 1.3.1.1 | ohpcd | 与 xapian-core/2.0.0 的 pin 对齐（避免版本冲突）；omega 直接 -lz |
| pcre2 | 10.47 | ohpcd | 静态，pkg-config 带 -DPCRE2_STATIC |
| libmagic | 5.48 | ohpcd | 静态 libmagic.a + share/misc/magic.mgc |
| perl | 设备 /data/service/hnp/bin/perl | PATH | configure AC_PATH_PROG 必需（omegatest.pl 执行体） |
| pkg-config | 0.29.2 /data/service/hnp/bin | PATH | pcre2/magic 探测 |

## 上游测试申报（R51）

- 清点：Makefile.am:176-192 → TESTS 注册 11 项（8 个 C++ 单测程序 + omegatest.pl + sourcetest + omindextest）；
  TESTS_ENVIRONMENT 含 UBSAN suppressions；EATMYDATA 可选缺失。
- 真机实际执行（2026-09-10，automake serial）：
  TOTAL: 11 / PASS: 11 / SKIP: 0 / FAIL: 0（首轮未注入 MAGIC 时 10/11，见问题#3）
- 逐项结果：atomparsertest PASS, csvesctest PASS, htmlparsertest PASS, jsonesctest PASS,
  md5test PASS, omegatest.pl PASS, omindextest PASS, sdbntest PASS, sourcetest PASS,
  urlenctest PASS, utf8converttest PASS
- 日志路径：
  - 依赖核验: /storage/Users/currentUser/tttt/omega-2.0.0-adapt/logs/w0-deps-2026-09-10.log
  - 二进制核验: 同目录 w0-binaries-2026-09-10.log / w0-xapian-core-full-2026-09-10.log / w0-binaries2-2026-09-10.log
  - configure 失败现场: explore-configure-2026-09-10-2330.log（config.guess 判型失败）
  - configure 通过: explore-configure4-2026-09-10-2339.log
  - make: explore-make2-2026-09-10-2340.log；install: explore-install-2026-09-10-2341.log
  - 首轮 make check(10/11): explore-makecheck-2026-09-10-2342.log
  - omindextest 单测复验: explore-omindextest-2026-09-10-2343.log
  - 权威全量 make check(11/11): explore-makecheck-final-2026-09-10-2344.log

## 验证结果

```bash
# 探索构建产物
$ ./omega --version    -> omega - xapian-omega 2.0.0   (rc=0)
$ ./omindex --version  -> omindex - xapian-omega 2.0.0 (rc=0)
$ ./scriptindex --version -> scriptindex - xapian-omega 2.0.0 (rc=0)
# 端到端（test_package 同款）
$ scriptindex testdb indexscript < data -> records added=1
$ OMEGA_CONFIG_FILE=omega.conf omega 'P=quick brown fox'
  -> Query((Zquick@1 AND Zbrown@2 AND Zfox@3))
$ file omega -> ELF 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
```
## 会话记录

### 对话 #1（2026-09-10 ~ 09-11，Agent 3F8F）

- 任务：omega/2.0.0（xapian-omega）OHOS 适配全流程（W0→探索构建→conan-verify→finish）。
- 前置：W0 五依赖 conan download 全 rc=0（recipe+binary）；xapian-core/2.0.0 当日 12:23 UTC 发布解除阻塞（09-05 分析曾判 dependency_missing）。
- 过程：config.guess/sub 判型失败→补丁；xapian-config prefix="/"-→配方私有副本；omindextest MAGIC-→Environment 注入；G0 clean-verify 受 HMDFS getcwd 限制止步（3/3 补丁可应用性已验证）。
- 终态：conan-verify PASS，W3 本地 CI exit 0，上游 make check 11/11（两轮：create 内 + w3 内）。
- 沉淀：knowledge/drafts/E429-draft-3F8F.kv（*-config 前缀重写消费侧方案）、E430-draft-F387.kv（静态 libmagic MAGIC）。
---

**编译结束**: 2026-09-11 00:35
**最终状态**: built
