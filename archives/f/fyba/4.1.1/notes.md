# fyba 4.1.1 适配笔记

## 编译环境
- 构建系统: autotools（configure.ac + Makefile.am，LT_INIT libtool）
- 编译日期: 2026-09-27
- 编译器: clang/clang++ 15.0.4（OHOS SDK sysroot aarch64-linux-ohos）
- 状态: published
- 上游: https://github.com/kartverket/fyba （Kartverket 挪威测绘局，SOSI 国家地理数据标准读写库）
- 源包 SHA-256: 99f658d52e8fd8997118bb6207b9c121500700996d9481a736683474e2534179（经 ghfast.top 与 gh-proxy.com 双镜像交叉核验一致）

## 编译步骤

1. 下载官方 tag tarball 并核验 SHA-256（双镜像交叉验证）。
2. `autoreconf --force --install`：官方 4.1.1 tag 自带 configure 为 2014 旧版，在 OHOS 上
   报 `cannot find install-sh`（aux 文件未随包）且 `cannot guess build type`
   （uname -s = "HarmonyOS"）。autoreconf 自举后生成 install-sh/config.guess/config.sub，
   新 config.sub 支持 aarch64-linux-ohos triplet。
3. `./configure --build=aarch64-linux-ohos --host=aarch64-linux-ohos --prefix=<prefix>`
   （config.guess 无法识别 HarmonyOS，必须显式传 triplet）。
4. `make -j1`：libfyba / libfygm / libfyut 三个库（.a + .so）均用 clang++ 15 + OHOS
   sysroot 编译链接成功（242 个上游注释 UTF-8 告警，无错误）。
5. `make install DESTDIR=<staging>`：头文件 → include/fyba/{fyba,fygm,fyut}.h，
   库 → lib/，pkgconfig → lib/pkgconfig/fyba.pc。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot find install-sh` | 官方 tag tarball 未包含 automake aux 文件 | `autoreconf --force --install` 自举 |
| 2 | `configure: error: cannot guess build type` | config.guess 不认识 HarmonyOS（uname -s） | 显式传 `--build/--host=aarch64-linux-ohos`（新 config.sub 已支持） |
| 3 | github.com 直连不可达 | 本机网络策略 | 通过 ghfast.top 镜像下载官方 tarball，SHA-256 双镜像交叉核验 |
| 4 | upstream 无 tests/ 目录 | fyba 4.1.1 release tag 未打包 README 提及的 tests folder | 上游测试源声明数 = 0；由 test_package 消费者测试（HO_New 创建 + 字节校验）补充 |

## 源码修改
1 个补丁：`patches/0001-FYBA-Makefile-am-vpath-includes.patch`
（将 src/FYBA/Makefile.am 的 `-I../GM -I../UT` 改为 `-I$(top_srcdir)/src/GM -I$(top_srcdir)/src/UT`，
确保 out-of-source（VPATH）构建能解析兄弟子目录头文件 fygm.h/fyut.h）。
配方 build() 中运行时 `autoreconf -fi` 自举（上游 2014 旧 configure 在 OHOS 上不可用）。

## 依赖版本
无运行时依赖（仅 libc/libm；配方 tool_requires: automake/1.18, libtool/2.5.4）。

## 验证结果

```bash
conan create ...  # 见 .ci-result.json
# 手工验证：
./configure --build=aarch64-linux-ohos --host=aarch64-linux-ohos && make -j1 && make install DESTDIR=$TEST_PREFIX
# 三库产物：
libfyba.a / libfyba.so.0.0.0、libfygm.a/.so、libfyut.a/.so
```

## 交付物
| 文件 | 说明 |
|------|------|
| archives/f/fyba/4.1.1/conanfile.py | Conan 配方（autotools + autoreconf 自举 + OHOS triplet） |
| archives/f/fyba/4.1.1/conandata.yml | 官方源 + SHA-256 |
| archives/f/fyba/4.1.1/test_package/ | 消费者测试（HO_New 创建 SOSI 文件 + 产物字节校验 + LC_* API） |
| archives/f/fyba/4.1.1/manifest.yaml | 版本元数据 |

## 注意事项
- fyba 头文件为 C++（无 extern "C"），消费者需以 C++ 编译。
- 上游 `-Wall -O2 -D_FILE_OFFSET_BITS=64 -DUNIX -DLINUX` 硬编码在 Makefile.am 中，不改动。
- 官方源 URL 保持 https://github.com/kartverket/fyba（R39），不做镜像域名替换。

---

## R02 返工记录（PR #13075 CI 失败闭环）

**问题**：PR #13075 远端 conan-pr-check 构建失败（退出码 1）：
`./config.status: line 838: ./confOJMNPb/defines.awk: Permission denied` →
`config.status: error: could not setup config headers machinery`。
CI 沙箱佐证：AppSpawn 上下文、`id: bad uid 20020101`、缺 curl、构建目录 .cache/buildbot-worker。

**根因归属**：autotools AC_CONFIG_HEADERS 机制中 config.status 用
`(umask 077 && mktemp -d ./confXXXXXX)` 创建临时目录，在 CI AppSpawn/HMDFS 存储语义下
该 0700 临时目录不可写，`cat >"$ac_tmp/defines.awk"` 失败 → Permission denied。
同类机制在本设备可复现（umask-077 + setgid 语义下直接执行 defines.awk 亦 Permission denied）；
同配方在本设备完整构建 PASS（R01 本地门禁全绿），即完整失败仅在 CI 沙箱存储权限语义下出现。

**修复（配方级，不改语义，复用 E011/E114/E175 知识族）**：conanfile.py build() 在
`autoreconf -fi` 后、configure 前，把生成的 configure 中 `umask 077` 替换为 `umask 022`
（临时目录仅作 scratch、运行后即删，configure 产物语义不变；与 argp-standalone/abiword-plugin-* 同款方案）。

**复验**：conan-verify G2/G3/G4 PASS；finish W3 本地 CI 模拟 PASS；W2 原子性 PASS；
test_package ctest 2/2 通过；knowledge 查重：umask-077 config.status 临时目录
为 E011/E114/E175 完整重复 → reuse_existing，不建新草稿。

---

**编译结束**: 2026-09-27 16:27
**最终状态**: published
