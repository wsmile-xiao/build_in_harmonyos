# libtheora 1.2.0-alpha1 适配笔记

## 编译环境
- 构建系统: autotools（upstream configure + make；2010 年 tarball 自带预生成 configure）
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4 (OHOS SDK)
- 状态: published

## 历史背景（W0b 核验）
- 1.1.1（2026-05-20 归档）用自定义 CMakeLists.txt 编译成功但未做 conan 适配；
  对应 conan 化 PR #4276（feat/libtheora-1.1.1-AEEE8，CMakeToolchain + 静态库）自 08-06 起未合入。
- 本任务版本为 1.2.0-alpha1（不同版本），新建独立分支，未触碰 #4276 分支。
- 历史踩坑逐项比对：
  - "config.guess 不识别 HarmonyOS" → 本次沿用解法（vendored 现代补丁对，E007）
  - "HMDFS TMPDIR 权限问题" → 本次沿用解法（umask 022 + mktemp TMPDIR 重定向，E011）
  - "无 CMakeLists.txt，用自定义 CMake" → **本次未采用**：CI worker 上 CMake 编译器识别/try_compile
    有失败历史（libogg 1.3.6.2 两轮 CMake 均败后转 direct-cc；#4276 长期未过与此路线疑点相关）。
    libtheora 是标准 autotools 工程，仓库已有 libkate 0.4.3（同 xiph 家族、同 libogg 依赖）的
    autotools CI 已验证模式，直接复用，构建保真度更高。

## 编译步骤

1. `init-build libtheora 1.2.0-alpha1 --url=https://downloads.xiph.org/releases/theora/libtheora-1.2.0alpha1.tar.gz`
2. 语言预检（R47）: detected=c，通过
3. 探索性编译（本机 OHOS aarch64 原生）:
   - 复制仓内已验证的 config.guess/config.sub（babeltrace2 2.1.2 同款，GNU 2023-08-22 + HarmonyOS 补丁）
     覆盖 2003 旧版 → `bash config.guess` 输出 `aarch64-unknown-linux-ohos`
   - `sed -i 's/umask 077/umask 022/g' configure`（E011）
   - `PKG_CONFIG_PATH=<libogg prefix>/lib/pkgconfig ./configure --prefix=$HOME/usr/local` → OK
     （Encoding support: yes / Floating point: yes / Assembly: aarch64 无上游汇编，纯 C）
   - `make -j4` → libtheora.so.0.4.0 / libtheoradec.so.1.1.5 / libtheoraenc.so.1.2.0 + 对应 .a 全部构建成功
   - `make install DESTDIR=$TEST_PREFIX` → 4 头文件 + 3 库链 + 3 .pc
   - `LD_LIBRARY_PATH=<ogg>/lib:<src>/lib/.libs make check` → **All 9 tests passed**
4. conan 配方（conan-init 生成骨架后编写）：
   - source(): vendor config 脚本 + E011 内联修复 + 生成物时间戳归一化（E248）
   - generate(): AutotoolsDeps + PkgConfigDeps + AutotoolsToolchain
     （原生模式，无 --host/--build 三元组——vendored 2023 config 对原生识别
      aarch64-unknown-linux-ohos；强制交叉模式会触发 XIPH_PATH_VORBIS "assumed OK"
      启用依赖 vorbis 的示例并编译失败，见知识草稿
      knowledge/drafts/libtheora-1.2.0-alpha1-cross-mode-assumed-optional-deps.kv；
      shared 默认 True）
   - build(): configure → make -j4 → 上游 9 测试编译+签名+逐一执行（HMBS_UPSTREAM_TEST_RESULT 标记）
   - package(): autotools.install() + licenses + .so 重签名（flac 1.5.0 模式）
   - test_package: 真实 th_encode_*/th_decode_* 编解码往返测试（R34）

## 上游测试清点（R51 三步法申报表）

| 程序 | 源文件 | 说明 | 运行环境 | 结果 |
|------|--------|------|----------|------|
| noop | tests/noop.c | 现行 th_* API 哑调用 | 本机 OHOS 原生 + conan build() | PASS |
| noop_theora | tests/noop_theora.c | 旧版 API + libtheora 链接 | 同上 | PASS |
| noop_theoraenc | tests/noop_theora.c | 旧版 API + theoraenc 链接 | 同上 | PASS |
| comment | tests/comment.c | th_comment 处理 | 同上 | PASS |
| comment_theoradec | tests/comment_theora.c | comment + theoradec 链接 | 同上 | PASS |
| comment_theora | tests/comment_theora.c | comment + libtheora 链接 | 同上 | PASS |
| granulepos | tests/granulepos.c | granulepos 语义 | 同上 | PASS |
| granulepos_theoraenc | tests/granulepos_theora.c | granulepos + theoraenc 链接 | 同上 | PASS |
| granulepos_theora | tests/granulepos_theora.c | granulepos + libtheora 链接 | 同上 | PASS |

实测：9/9 通过（本机 `make check` 全绿；conan 配方 build() 内以直接执行方式复跑，每程序 exit code 记录进日志）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 报 unable to guess system type | 2003 年脚本无 HarmonyOS 分支（E007） | 用仓内已验证现代补丁对（babeltrace2 2.1.2 同款）整体替换，输出 aarch64-unknown-linux-ohos |
| 2 | config.guess 阶段 dummy.c: Permission denied | HMDFS 上 umask 077 + mktemp 0700 目录不可写（E011） | umask 077→022 + mktemp 重定向 $TMPDIR（libkate 模式，configure 内联修复） |
| 3 | make check 9/9 全 FAIL: Error loading shared library libogg.so.0 | 测试二进制运行时找不到 conan libogg | LD_LIBRARY_PATH 注入 <libogg>/lib:<build>/lib/.libs（配方内已固化） |
| 4 | perl patch-autotools-ohos.pl 对 2003 年 config.guess 打补丁失败（Score 1/5） | 老脚本结构与补丁 pattern 不匹配 | 改用整体替换（仓内 babeltrace2 已验证的 2023-08-22 现代对） |

## 源码修改

无 .patch 文件。适配全部通过配方内机制完成：
- patches/autotools/config.guess、config.sub：vendored 现代版（整文件替换，非增量补丁）
- conanfile.py source() 中的 configure 内联修复（umask/mktemp）与时间戳归一化
- 上游源码（lib/、include/、tests/）**零修改**

## 依赖版本

- libogg/1.3.6.2（ohpcd 制品仓，binary 实测可下载：libogg.so.0.8.6 + libogg.a）

## 验证结果

```bash
# 探索性编译（本机）
$ ./configure --prefix=$HOME/usr/local   # OK: Encoding yes, Float yes
$ make -j4 && make install DESTDIR=$TEST_PREFIX
$ LD_LIBRARY_PATH=$OGG/lib:lib/.libs make check
All 9 tests passed

# conan 验证
$ conan create . -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64
# → G0-G4 通过，test_package 编解码往返 PASS（见 reports/）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | autotools 配方（libkate 0.4.3 CI 已验证模式） |
| conandata.yml | 官方源 URL + sha256 |
| patches/autotools/config.{guess,sub} | 现代化构建辅助脚本（vendored） |
| test_package/ | th_ API 编解码往返消费者测试 |
| manifest.yaml / notes.md | 元数据与本笔记 |

## 注意事项

- aarch64 无上游汇编优化属正常（上游仅 x86/ARM32/C64x 汇编），纯 C 构建即全功能，未做任何裁剪。
- 产物含可执行位 .so，OHOS 上由 package() 重签名（binary-sign-tool selfSign）。
- examples（dump_video/dump_psnr 等）为 noinst 演示程序，不随包安装；缺 SDL/libpng 时 configure 自动禁用对应示例（上游原生行为）。
---

**编译结束**: 2026-09-18 18:54
**最终状态**: published
