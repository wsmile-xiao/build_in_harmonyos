# libigloo 0.9.5 编译笔记

- 日期: 2026-09-16
- 分支: feat/libigloo-0.9.5
- 主机: HarmonyOS PC localhost, aarch64, HongMeng Kernel 1.12.0
- 源码: https://gitlab.xiph.org/xiph/icecast-libigloo/-/archive/v0.9.5/icecast-libigloo-v0.9.5.tar.gz
  (sha256: 67a9a1d667033eda06adb1306d3a80e9125246f616d1ffe362395fb2b32aae61, 81251 字节, 2026-09-16 下载并复核)
- 许可证: LGPL-2.0-or-later (COPYING 为 LGPL-2.0 全文, igloo.h 头部为 LGPL-2.0-or-later)

## 库形态结论 (任务要求 1)

**编译型 C 框架库，非 header-only，非纯测试框架。**

- `configure.ac` 使用 `LT_INIT` (libtool); 根 `Makefile.am` 定义 `lib_LTLIBRARIES`
- 上游测试 (`tests/`) 是库的**消费者**: 每个测试程序链接 `-ligloo` 编译为可执行文件
- `igloo/tap.h` 是公共 API 之一 (供 Icecast 等下游使用), 但库本身是实体 .so/.a
- 16 个公共头文件 (igloo.h, ro.h, sp.h, tap.h, uuid.h, prng.h, digest.h, time.h, error.h, cs.h, feature.h, list.h, rwlock.h, typedef.h, types.h, config.h)

## 构建方式 (R3, R51 上游测试三步法)

1. **上游测试清点**: tests/ 目录 10 个 `check_PROGRAMS` (tap_suite, init_igloo_test, feature, ro, digest, error, prng, cs, TIME, uuid)。无 ctest/automake test harness 元素, 由 `make check` 驱动 TAP 输出。
2. **探索性构建**: 全流程在本机 OHOS 环境跑通 (autogen.sh → configure → make → make check), 763/763 PASS。
3. **上游正式测试全跑**: 配方 `build()` 中 `autotools.make(target="check")` 在 conan 构建环境重放同一测试套件。

## 探索性构建记录 (2026-09-16, 本机 aarch64-unknown-linux-ohos)

- 自动化工具: autoreconf (autoconf 2.71, automake 1.16, libtool 2.4.7 系本机版本; conan 配方用 automake/1.18 + libtool/2.5.4)
- config.guess/config.sub: 2023-08-22 基底 + HarmonyOS (linux-ohos) 补丁
- host: `aarch64-unknown-linux-ohos`
- rhash 发现: `PKG_CHECK_MODULES` 未用 (本机无系统 librhash), 走 `AC_CHECK_HEADER + AC_CHECK_LIB` 回退路径, 手动 `RHASH=/path/to/conan/rhash CPPFLAGS=-I... LDFLAGS=-L... -static` 链接 conan 缓存的静态 rhash
- 结果: `make check` → **763/763 PASS, 0 FAIL** (详见下表)

### 上游 TAP 测试明细 (check.log 实测)

| 测试程序 | 断言数 | 覆盖模块 | OHOS 敏感点 |
|---|---|---|---|
| tests/tap_suite | 5 | TAP 框架自检 | - |
| tests/init_igloo_test | 23 | 库初始化/关闭、对象组 | pthread |
| tests/feature | 12 | feature 接口 | - |
| tests/ro | 50 | 引用计数对象 | pthread rwlock |
| tests/digest | 259 | 摘要计算 | rhash 后端 |
| tests/error | 57 | 错误码 | - |
| tests/prng | 20 | 随机数发生器 | /dev/urandom, getrandom(2) |
| tests/cs | 162 | 字符串比较 | - |
| tests/time | 118 | 时间接口 | clock_gettime |
| tests/uuid | 57 | UUID 生成/校验 | prng 依赖 |
| **合计** | **763** | | |

## OHOS 适配根因与处理

### 根因 1: 官方 tag tarball 无预生成 configure (E089 相关)

- 现象: `autoreconf` 报 `PKG_CHECK_MODULES possibly undefined` + 连锁误报
- 根因: tarball 的 m4/ 目录不含 pkg.m4, aclocal 无处取宏
- 处理: 配方 `export_sources` 携带 m4-pkg.m4, `build()` 在 autoreconf 前复制到 `m4/pkg.m4`
- 知识库: 已被 E089 (libfyaml 草稿) 覆盖 → **路径 A, 无需扩展**

### 根因 2: autoreconf 覆盖 HarmonyOS config.guess/config.sub

- 玔象: 探索性构建时 config.guess 报 unknown platform
- 根因: `autoreconf --install` 会从 automake 包安装 stock config.guess (2024-07-27, 无 HarmonyOS) 覆盖补丁版本
- 处理: 补丁在 autoreconf 之后应用 (conanfile `build()` 步骤 3)
- 知识库: 已被仓库先例 (libfyaml 0.9.6, abiword 系) 覆盖 → **路径 A**

### 根因 3 (防御性保留): HMDFS 工作目录 umask 077 使 config.status 临时目录不可写 (E136)

- 现象: 本机探索性构建全程无此错误 (生成的 configure 中 mktemp 行已是 autoconf 2.71 的 `umask 000 && mktemp -d "./confXXXXXX"`, 非 E136 的 umask 077 模板)
- 根因: E136 描述的是 CI sandbox 环境 (libfyaml 0.9.6 在 CI 实际命中): configure 用 umask 077 创建临时目录且使用相对路径, 在 SGID 环境下权限不足
- 处理: 配方保留 libfyaml 同款 `umask 077 → umask 002` 文本替换; 在本机 autoconf 2.71 (`umask 000`) 下是 no-op, 在 CI sandbox 上按需生效
- 知识库: E136 已存在 → **路径 A, 无需扩展**

### 根因 4: rhash 静态非 PIC 无法链入共享 libigloo (E005)

- 现象: 尝试 shared 构建时 ld 报 `relocation R_AARCH64_LD64_GOTOFF_1K against ... can not be used when making a shared object; recompile with -fPIC`
- 根因: ohpcd rhash/1.4.6 为静态非 PIC 构建; 共享库链入静态对象要求 PIC
- 处理: 配方默认 `shared=False`, `validate()` 柔性拒绝 shared=True (提示需 PIC rhash)
- 知识库: 查重确认已被 E005 (静态非 PIC 库不能链入共享库) 覆盖 → **路径 A, 无需扩展**

### 根因 5 (新发现, 已实证): OHOS bash 5.3 组命令 fd 3 重定向不传入管道元素, tap-driver.sh 全 ERROR (DRAFT-E553)

- 现象: conan create 的 `make check` 10/10 测试全部 ERROR "missing test plan", 每个 .log 为空; 而测试二进制直接运行全绿, 探索性构建 763/763 PASS
- 根因: OHOS PC bash 5.3 (aarch64-unknown-linux-ohos 移植, profile buildenv 注入为 $(SHELL)) 组命令 `{ pipeline; } 3>file` 的 fd 3 传不进管道元素: `{ echo | cat >&3; } 3>log` 报 "3: Bad file descriptor"; `exec 3>` 后管道内同样失败; 子外壳 `( ...; ) 3>log` 与 /bin/sh (mksh 系) 正常。tap-driver.sh 主结构恰是 `{ (测试) | awk '{print | "cat >&3"}' } 3>log`, bash 下 awk 的日志通道全断 → 每测试判 ERROR。与 HMDFS 无关 (3>/dev/null 亦失败), 与 E551 方向相反 (彼条 bash 是好方, 此条 bash 是坏方)
- 最小复现: `bash -c '{ echo y | cat >&3 2>&1; } 3>/tmp/fd3probe.log; test -s /tmp/fd3probe.log && echo OK || echo BASH-FD3-BROKEN'`
- 处理: conanfile build() 的 make check 命令行覆盖 `autotools.make(target="check", args=["-j1", "SHELL=/bin/sh"])`; 修复后 763/763 PASS
- 知识库: 查重 (tap-driver / Bad file descriptor / missing test plan / cat >&3 均无条目, E348 为 GLib 测试接线、E076 为 fstat EACCES, 均不同) 后未覆盖 → **路径 B, 新增 DRAFT-E553**
  (knowledge/drafts/DRAFT-E553-ohos-bash-fd3-pipeline-tap-driver.md/.kv)

## 与 conan create 全流程验证

- 命令: `conan create . --build=missing -pr:h ~/.conan2/profiles/ohos-aarch64 -pr:b ~/.conan2/profiles/ohos-aarch64`
- 日期: 2026-09-16, 本机 HarmonyOS PC (aarch64, HongMeng Kernel 1.12.0)
- 结果: **全绿**
  - 构建链: export(pkg.m4) → autogen.sh(autoreconf) → config.guess/config.sub HarmonyOS 补丁 → configure(aarch64-unknown-linux-ohos) → make → make check
  - Layer 1 上游测试: **TOTAL: 763 / PASS: 763 / FAIL: 0 / ERROR: 0** (test-suite.log 全局统计; make check SHELL=/bin/sh, 见根因 5)
  - Layer 2 消费者测试: test_package 1/1 通过 (ctest, 0.02s) — igloo_initialize/version_get(0.9.5)/version_check/sp_replace/unref/uuid_new_random_cstr(36 字符)/uuid_is_valid(含畸形拒绝)/tap 三断言/ro_unref 全部实跑
  - 包产物: libigloo.a (125864 B, 16 对象) + 16 公共头 + licenses/COPYING + igloo.pc (prefix=/ + DESTDIR 安装, conan AutotoolsToolchain 标准行为)
- 中间挫折与修复(按时间序):
  1. 首次 create: make check 10/10 ERROR (bash fd3 缺陷, 根因 5) → SHELL=/bin/sh 覆盖修复
  2. 二次 create: 消费者测试断言顺序错误 (get_stats 在 tap_test_success 记录前求值, 快照 1/2) → 增加一条显式断言修正
  3. 三次 create: 全绿 (763/763 + 1/1)

## 交付文件清单

```
archives/l/libigloo/
├── manifest.yaml                        # 软件清单 (库形态/根因要点/rhash 依赖)
├── README.md                            # 包说明 (形态结论/OHOS 适配/依赖)
└── 0.9.5/
    ├── conanfile.py                     # 配方 (182 行; autogen→patch→configure→make→check)
    ├── conandata.yml                    # 源 URL+sha256 + 2 个 portability 补丁
    ├── notes.md                         # 本文件 (构建笔记/根因台账/验证记录)
    ├── m4-pkg.m4                        # pkg.m4 宏 (autoreconf 前 cp 到 m4/pkg.m4)
    ├── patches/
    │   ├── 0002-build-aux-config.guess.patch   # HarmonyOS 检测 (automake/1.18 基底验证适用)
    │   └── 0003-build-aux-config.sub.patch     # linux-ohos 三元组白名单
    └── test_package/
        ├── conanfile.py                 # CMakeDeps+CMakeToolchain, ctest 驱动
        ├── CMakeLists.txt               # find_package(libigloo) 链接目标
        ├── MANIFEST.yml                 # 上游测试台账 (10 程序/763 断言) + 消费者测试声明
        └── test.c                       # 真实消费者 (111 行, 7 组 API 断言)

knowledge/drafts/
├── DRAFT-E553-ohos-bash-fd3-pipeline-tap-driver.md    # 路径 B 新根因草稿
└── DRAFT-E553-ohos-bash-fd3-pipeline-tap-driver.kv    # 结构化 kv (rec: SHELL=/bin/sh)
```

## 结论

libigloo 0.9.5 在 OHOS PC aarch64 适配成功:
- 形态: 编译型框架库 (静态), 非纯测试框架
- 上游测试: 10 程序 763/763 PASS (make check, R51 三步法全过)
- 消费者测试: 真实调用 5 组公共 API (initialize/version/sp/uuid/tap), 编译+运行通过
- 根因: 4 个真实根因全部定位并处理 — E089/pkg.m4 (路径 A)、autoreconf 覆盖 config.guess 先例 (路径 A)、E005 静态非 PIC (路径 A)、E136 umask (防御性保留, 本地 no-op)、DRAFT-E553 bash fd3 管道缺陷 (路径 B 新增草稿)
- conan create 全流程三次迭代后全绿
