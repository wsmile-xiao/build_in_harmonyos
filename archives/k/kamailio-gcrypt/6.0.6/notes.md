# kamailio-gcrypt 6.0.6 适配笔记 — HarmonyOS PC / aarch64

## 1. 概况

| 项 | 值 |
|----|----|
| 库名 / 版本 | kamailio-gcrypt / 6.0.6 |
| 上游仓库 | https://github.com/kamailio/kamailio（官网 https://www.kamailio.org） |
| 适配路径 | `archives/k/kamailio-gcrypt/6.0.6/` |
| 许可证 | GPL-2.0-or-later |
| 语言 | C（**工单标注 C++，实测上游 gcrypt 模块全为 C 源，无 C++ 源文件**，如实登记） |
| 构建系统 | kamailio 经典 Makefile 体系（`src/Makefile` + `Makefile.defs`），非 CMake/autotools |
| 打包口径 | 仅打包 Alpine `main/kamailio` APKBUILD 的 `kamailio-gcrypt` 子包对应模块：`_mod_list_gcrypt="gcrypt"` |
| 产物 | `lib/kamailio/modules/gcrypt.so`（1 个 core 插件模块） |
| 外部依赖 | `libgcrypt/1.12.2`（→ 传递 `libgpg-error/1.55`），二者制品仓均已发布 |
| 补丁数 | **0**（`conandata.yml` 中 `patches: {}`） |
| 源码 | 官方 `kamailio-6.0.6_src.tar.gz`，sha256 `32e4290c6813c9d0289abe9ec2de9138e12e0381179218a7fed374ad813ecc48` |
| 使用知识库条目 | E525（OHOS SELinux 禁 FIFO → make 统一 `-j1`）、E074、同族先例 kamailio-{tls,xml,unixodbc,extras} |

模块职责：把 libgcrypt 的 AES-128-CBC 与 UUID 生成暴露给 kamailio 配置脚本（cfg 命令）
与 KEMI 路由脚本（`KSR.gcrypt.aes_encrypt/aes_decrypt`）。源码目录 `src/modules/gcrypt/`：
`gcrypt_mod.c`（模块入口，447 行）、`gcrypt_aes128.{c,h}`（AES-128-CBC，零 IV、16B 块）、
`gcrypt_uuid.{c,h}`、`api.h`、`Makefile`、`CMakeLists.txt`、`doc/`、`README`。

### 1.1 依赖发布状态（R36 / W0：适配前先查依赖）

| 依赖 | 制品仓状态 | 证据 |
|------|-----------|------|
| libgcrypt/1.12.2 | ✅ 已发布（recipe rev `31623037ac107da56f8eda86fa63a956`，2026-07-27） | `conan download libgcrypt/1.12.2 -r=ohpcd` → rc=0（recipe 与 binary 均取回） |
| libgpg-error/1.55 | ✅ 已发布（recipe rev `514ce64c1bb232a6dc552738856ae7e1`，2026-07-15） | `conan download libgpg-error/1.55 -r=ohpcd` → rc=0 |

→ 无缺失依赖，本任务**不需要**新建依赖项分支（依赖链已具备，CI 不会落回 `--build=missing` 源码构建）。

## 2. 打包范围（1 个模块）

| 模块 | 上游源（`src/modules/`） | 产物 | 模块级外部依赖 |
|------|------------------------|------|---------------|
| gcrypt | `gcrypt/gcrypt_mod.c`、`gcrypt_aes128.c`、`gcrypt_uuid.c` | `lib/kamailio/modules/gcrypt.so` | `libgcrypt`（`-lgcrypt`，经模块 Makefile 的 `pkg-config --exists libgcrypt` 探测） |

不打包 kamailio 主程序（与本仓同族 10 个 `kamailio-*` 配方一致：模块 .so 由 kamailio
运行时 `loadmodule` 加载，模块包不依赖 kamailio 本体包）。

## 3. 构建方法

配方 `conanfile.py` 的 `build()` 实际执行（等价于手工两步）：

```bash
# 1) 生成 src/config.mak（必须先 cfg，否则 make 报 No rule to make target 'cfg-defs'）
make cfg include_modules="gcrypt" \
     extra_defs="-D_GNU_SOURCE -DHAVE_GETHOSTBYNAME2 …" \
     GCRYPT_BUILDER="pkg-config libgcrypt" LOCALBASE=<libgcrypt 包目录>

# 2) 编模块（-j1 见 §4.5）
make modules modules="modules/gcrypt" -j1 \
     extra_defs="…" GCRYPT_BUILDER="pkg-config libgcrypt" LOCALBASE=<libgcrypt 包目录>
```

编译器与依赖路径经 Conan `Environment` 显式注入（R33，不裸用 `${CC}`/`${CFLAGS}`）：
`CC`/`CXX` ← `tools.build:compiler_executables`；`CPATH`/`LIBRARY_PATH`/`PKG_CONFIG_PATH`
← `libgcrypt` 与 `libgpg-error` 两个 conan 依赖包的 `include`/`lib`/`lib/pkgconfig`。

## 4. 平台差异与解决（4 条，全部经 make 命令行变量表达 → 0 补丁）

### 4.1 平台探测宏缺失（`OS=harmonyos` 不在 `Makefile.defs` 平台分支内）

`Makefile.defs` 只处理 linux/solaris/freebsd/darwin 分支，OHOS 命中不了任何 `HAVE_*`
探测宏，模块源码中的条件编译会走错分支。解决：经 make 命令行变量 `extra_defs` 注入
linux 分支等价宏集（9 项，见 `conanfile.py` 的 `PLATFORM_DEFS`），与同族
kamailio-tls/kamailio-xml/kamailio-extras 先例逐项一致（宏集已对照 OHOS SDK musl
语义 sysroot 实证存在）。**未改任何上游文件，故 0 补丁。**

### 4.2 只编模块、不编 core（0 补丁的关键）

kamailio 主程序（core）在 OHOS 上有两处 musl 头文件差异会导致编译失败：
`core/resolve.c` 的 `HAVE_RESOLV_RES` → `_res`、`core/lock_ops.h` 的
`HAVE_UNION_SEMUN` → `union semun`。这两条路径**只在编译 kamailio 主程序时触发**；
本配方只编 `modules/gcrypt`，不触碰 → 无需任何补丁。模块运行期所需 core 符号由
kamailio 主程序在 `loadmodule` 时提供（模块是 core 插件，非独立库）。

### 4.3 libgcrypt 依赖探测三重钉死

`src/modules/gcrypt/Makefile` 在 `CROSS_COMPILE` 为空时执行
`pkg-config --exists libgcrypt` 探测（命中取 `--cflags/--libs`），未命中回退
`-I$(LOCALBASE)/include` + `-L$(LOCALBASE)/lib -lgcrypt`。构建机若装有系统 libgcrypt
会劫持探测结果（交叉编译事故源），故三重钉死：

1. 命令行变量 `GCRYPT_BUILDER="pkg-config libgcrypt"` + `PKG_CONFIG_PATH` 指向 conan
   依赖包 → make 命令行变量优先于 Makefile 内部赋值，探测只可能命中依赖包；
2. `CPATH`/`LIBRARY_PATH` 指向依赖包（pkg-config 缺失时仍可编译/链接）；
3. `LOCALBASE` 指向 libgcrypt 包目录（回退分支同样指向依赖包）。

### 4.4 模块 .so 的外部动态依赖语义（实测依赖形态）

`gcrypt.so` 的 `DT_NEEDED` = `{libc.so, libgcrypt.so.20}`（实测，见 §6）。libgcrypt 在
OHOS sysroot 与目标机 `/lib` 中**不是**系统同名库（无 `libgcrypt.so*`），故不落入 R26
「系统同名库须静态」的适用范围，按仓库口径由 conan 依赖链提供运行时 .so；模块自身
**无 RPATH/RUNPATH**（实测），部署时经 `LD_LIBRARY_PATH`（或等价加载路径）定位
libgcrypt.so.20 / libgpg-error.so.0，与同族 cnxcc（动态 libevent）判例一致。
`package_info()` 中 `libdirs = ["lib/kamailio/modules"]`、`libs = []`（模块不被链接消费）。

### 4.5 统一 `-j1`（E525/E074）

OHOS SELinux 禁止用户进程创建 FIFO，而 GNU make jobserver 依赖 FIFO 传递令牌，
`-j>1` 存在挂起/报错风险 → 全流程 `-j1`，与同族 kamailio-* 配方一致。

## 5. 上游测试（R51 三步法）

### 5.1 清点（源码包实测全量）

官方源码包 `kamailio-6.0.6_src.tar.gz`（sha256 `32e4290c…`）内：

- **顶层 `test/` 目录：0 个**（6.0.6 的 `_src` 发布包不含独立 `test/` 目录，与 git 仓库不同）
- 分散的 `test`/`tests` 目录共 **4 个**、文件共 **17 个**：

| 目录 | 文件数 | 性质 |
|------|-------|------|
| `utils/kamctl/dbtextdb/tests/` | 10 | 数据文件（由同目录 `dbtextdb_test.py` 消费） |
| `src/modules/janssonrpcc/test/` | 3 | jsonrpc-c 模块脚本 + 配置（非本包模块） |
| `src/modules/rtpproxy/test/` | 3 | rtpproxy 模块配置 + 命令行记录（非本包模块） |
| `src/modules/tm/test/` | 1 | tm 模块开发期 IPC 清理脚本（非本包模块） |

- **gcrypt 模块自身无上游测试**：`src/modules/gcrypt/` 内只有
  `CMakeLists.txt`/`Makefile`/`README`/`api.h`/`doc/`/`gcrypt_{mod,aes128,uuid}.{c,h}`，
  无测试源、无 `check` 目标注册（`src/Makefile` 与模块 Makefile 均无 `check` 目标）。

### 5.2 实测运行（可运行环境：OHOS aarch64 交叉构建环境）

17 个文件中**唯一自包含、不需要运行中 kamailio 实例**的上游测试是
`utils/kamctl/dbtextdb/dbtextdb_test.py`（上游自带 unittest 入口，3 个用例，仅依赖
Python 标准库）。已在 `conanfile.py` 的 `build()` 末尾真实执行（CI 每次构建都会跑）：

```
python3 dbtextdb_test.py -v
testExecute (__main__.TestDbtextdb.testExecute) ... ok
testOpenTable (__main__.TestDbtextdb.testOpenTable) ... ok
testParseQuery (__main__.TestDbtextdb.testParseQuery) ... ok
----------------------------------------------------------------------
Ran 3 tests in 0.016s

OK
```

→ 上游可运行测试通过率 **3/3 = 100%**（failures=0, errors=0, skipped=0）。

### 5.3 未执行项逐项原因（非「没环境」，均为具体技术原因）

| 文件 | 未执行原因 |
|------|-----------|
| `tests/` 下 10 个数据文件 | 纯数据（无执行位、无断言），由已执行的 `dbtextdb_test.py` 读取消费 |
| `janssonrpcc/test/run-tests.sh` | 需同源码树构建的 kamailio **主程序** + 该模块 loadmodule 运行实例；本包产物仅 `gcrypt.so`（同族口径不构建 core） |
| `janssonrpcc/test/mem-test.sh` | 同上，另需 `valgrind`（OHOS 无该工具链） |
| `janssonrpcc/test/test.cfg` | 配置文件，无执行入口 |
| `rtpproxy/test/kamailio.cfg` | 配置样例，需运行中 kamailio + 外部 rtpproxy 进程 |
| `rtpproxy/test/exec_{rtpproxy,pjsua}.txt` | 纯文本命令行记录（无执行位、无断言），pjsua 为外部二进制 |
| `tm/test/kill_sem.sh` | 非测试用例：需 root，且 `ipcrm` 会删除构建机**全部** SysV IPC 对象，在共享 CI worker 上会破坏其他进程；上游仅作开发调试清理用 |

### 5.4 适配后测试（鸿蒙特有，`test_package/`）

| 用例 | 内容 | 实测结果 |
|------|------|---------|
| `check_gcrypt_module.py` | 纯 Python ELF 自解析：ELF 身份、模块契约名 `exports->name == "gcrypt"`、12 个契约导出符号、`DT_NEEDED == {libc.so, libgcrypt.so.20}`、无 RPATH/RUNPATH、49 个未定义符号 100% 归类、依赖包逐符号核验 `gcry_*`、libgcrypt→libgpg-error 链闭合、许可证随包 | **16/16 通过** |
| `test_gcrypt_e2e.c` | 端到端消费者用例（rule12）：`dlopen(RTLD_NOW)` → `exports` 描述符（name/dlflags/cfg 命令表 3 项/参数表 3 项）→ `mod_register()` → 观察 `sr_kemi_modules_add()` 收到的 KEMI 表（2 项：子模块名 gcrypt、函数 aes_encrypt/aes_decrypt、返回类型 SR_KEMIP_INT、参数类型 (str,str,str,none…)）→ `dlsym(aes128_*)` 做 **AES-128-CBC 已知答案测试**（2 组向量：FIPS-197 与 NIST SP 800-38A F.2.1，密文由 openssl 独立复算；含 round-trip 解密与 destroy 置空）→ NULL 上下文负例 → `dlclose()` | **50/50 断言通过** |
| `kamailio_core_stub.{c,h}` | core 符号最小层（gcrypt.so 是 core 插件，OHOS musl 不做惰性绑定，dlopen 时全部未定义符号须可解析；测试以 `-Wl,--export-dynamic` 导出符号供解析） | 随 e2e 编译通过 |

## 6. 验证证据（W3：本地 OHOS aarch64 `conan create`）

```
$ conan create . --build=missing -pr:h ci/conan/profiles/ohos-aarch64 -pr:b default
…
kamailio-gcrypt/6.0.6: Calling build()
…
testExecute (__main__.TestDbtextdb.testExecute) ... ok      ← 上游 dbtextdb 3/3
Ran 3 tests in 0.016s / OK
…
kamailio-gcrypt/6.0.6: package(): Packaged 1 '.so' file: gcrypt.so
…                                                            ← test_package
[check] 16/16 checks passed                                  ← 产物结构/依赖闭包
ALL OHOS E2E PASSED (50 assertions, loadmodule path dlopen->exports->cmds/params->mod_register->KEMI table->aes128 KAT->dlclose)
======== Testing the package: Done. ========
=== conan create rc=0
```

关键实测事实（`test_package/check_gcrypt_module.py` 断言 + `llvm-readelf`/`llvm-nm` 交叉核验）：

| 项 | 实测值 |
|----|--------|
| ELF 身份 | ELF64 LSB、`ET_DYN`、`EM_AARCH64` |
| 模块契约名 | `exports->name == "gcrypt"`（module_exports 首字段） |
| 契约导出符号 | 12 个（`exports`、`mod_register`、`module_version/flags/interface_ver`、`bind_gcrypt`、`gcrypt_generate_callid`、`gcrypt_register_callid_func`、`aes128_{context_init,context_destroy,encrypt,decrypt}`） |
| `DT_NEEDED` | `{libc.so, libgcrypt.so.20}`（无其他） |
| `RPATH`/`RUNPATH` | 无（部署经 `LD_LIBRARY_PATH` 定位依赖链） |
| 未定义符号 | 49 个，100% 归类：libc/CRT 9 + libgcrypt.so.20 17（带 `GCRYPT_1.6` 版本标签）+ kamailio core 23 |
| 依赖链闭合 | `libgcrypt.so.20` 在 conan 依赖包内实测存在；其引用的 `gcry_*` 逐符号核验由该包导出；`libgcrypt.so.20 → libgpg-error.so.0` 闭合 |
| AES KAT | `key=000102…0f / pt=001122…ff → ct=69c4e0d86a7b0430d8cdb78070b4c55a`（FIPS-197）；`key=2b7e…/pt=6bc1… → ct=3ad77bb40d7a3660a89ecaf32466ef97`（NIST SP 800-38A F.2.1），密文均由本机 `openssl` 独立复算 |
| 许可证 | `licenses/COPYING`（GPL-2.0-or-later）随包 |

## 7. 已知限制与未覆盖项（如实登记）

1. **运行时依赖不在包内**：`gcrypt.so` 的 `DT_NEEDED` 含 `libgcrypt.so.20`（非系统同名库），
   该 .so 由 conan 依赖链（`libgcrypt/1.12.2`）提供，部署时须使目标机可达该库
   （`LD_LIBRARY_PATH` 或等价机制）。本仓库同族 cnxcc（动态 libevent）同判例。
2. **不构建 kamailio core**（同族 10 个 `kamailio-*` 配方一致口径）：本包不含 kamailio
   主程序，故无法在本包内做「真实 kamailio 进程 loadmodule 后跑 cfg 脚本」级验证；
   e2e 以 core 符号桩层（`kamailio_core_stub.c`）加载同一 `gcrypt.so` 并真实调用
   模块导出函数，作为消费者路径的等价验证。
3. **UUID 生成路径（`gcrypt_uuid.c`）无运行期用例**：e2e 只核验 `gcrypt_generate_callid`、
   `gcrypt_register_callid_func` 两个导出符号存在与契约面，未做运行期 UUID 断言
   （该函数需 kamailio core 的 callid 注册上下文）。上游亦无该模块测试用例。
4. **上游测试覆盖面**：源码包 17 个 test/tests 文件中仅 1 个（dbtextdb 的 unittest）可在
   无 kamailio 运行实例条件下执行，已实跑 3/3；其余 16 项逐项原因见 §5.3。
5. **不做平台功能裁剪**：模块的 cfg/KEMI 导出面与上游一致，未 stub 任何功能。

## 8. 拟沉淀知识（供知识图谱收录）

本次适配产生两条**共性问题**知识（非本库专属补丁），已按 R19 先草稿后审核的流程落盘
`knowledge/drafts/`：

| 草稿 | 共性问题 | 检测手段 | 处理策略 |
|------|---------|---------|---------|
| `kamailio-gcrypt-6.0.6-ohos-plugin-stub-type-alignment` | OHOS/musl 加载器不做惰性绑定（dlopen 等价 RTLD_NOW），**core 插件**类 .so 的消费测试须自带 core 符号桩层；而桩层类型必须逐字段对齐上游头文件，否则日志路径（`LM_ERR`）解引用野指针 → **SIGSEGV 掩盖真实失败原因** | 桩层定义与上游 `dprint.h`/`kemi.h` 逐项比对：`my_pid`/`dprint_color` 是**函数**而非变量、`log_level_info` 是**数组**、`_km_log_func` 必须指向**非空 sink** | 桩层类型对齐 + 日志指针指向 sink（而非 `NULL` 或仅 getter 返回值） |
| `kamailio-gcrypt-6.0.6-ohos-plugin-external-dynlib-closure` | 插件模块携带非系统同名库的 `DT_NEEDED`（此处 `libgcrypt.so.20`）时的产物闭包校验与运行时定位口径：编译通过 ≠ 可加载，须验证「未定义符号是否 100% 被依赖包提供」+「依赖链是否闭合」 | `readelf -d`（DT_NEEDED/RPATH）+ `nm -D --undefined-only` 逐符号归类 + 依赖包导出符号交叉核验（或脚本化等价实现） | 依赖链由 conan 提供运行时 .so（不静态、不打 RPATH）；合并前用产物检查脚本门禁化 |

## 9. 文件清单

```
archives/k/kamailio-gcrypt/
├── manifest.yaml                 # 软件级元数据 + 版本索引
├── README.md                     # 软件描述
└── 6.0.6/
    ├── conanfile.py              # 单模块配方（0 补丁；R33 显式注入 CC/CPATH/LIBRARY_PATH/PKG_CONFIG_PATH）
    ├── conandata.yml             # 官方源码 URL + sha256（patches: {}）
    ├── manifest.yaml             # 版本级编译元数据（状态/证据/依赖）
    ├── notes.md                  # 本文件
    └── test_package/
        ├── conanfile.py          # 消费者测试驱动（check 脚本 + e2e 编译/运行）
        ├── check_gcrypt_module.py# 产物结构/依赖闭包断言（16 项，纯 Python ELF 解析）
        ├── test_gcrypt_e2e.c     # 端到端消费者用例（50 项断言，AES KAT）
        ├── kamailio_core_stub.c  # core 符号最小层（类型对齐上游头文件）
        ├── kamailio_core_stub.h
        └── MANIFEST.yml          # 上游测试清点/实跑台账 + 鸿蒙特有测试登记
```

### 对话 #1 — 适配路径确定与验证（关键决策与教训）

1. **任务标签与实测不符**：工单标注 C++，实测 kamailio gcrypt 模块全为 C 源（无 C++ 文件），
   PR 如实标注语言，避免"语言声明与源码不符"。
2. **下载源超时规避**：首次 `conan create` 拉取官方源码超时（约 20 分钟白等）。改用
   「本地已校验 tar 预填 conan 下载缓存 SOURCE_BACKUP」的方式（写
   `dl_cache/s/<sha256>.json`），不再依赖网络重试。注意本版 conan 无 `conan config set`
   子命令（`invalid choice: 'set'`），且 `tools.*` 命名空间被 `--core-conf` 拒绝
   （`Only core. values are allowed`），只能手改 `~/.conan2/global.conf`。
3. **e2e SIGSEGV 根因（本次最重要教训）**：`test_gcrypt_e2e` 初版编译通过但运行
   `Signal 11 (core dumped)`（rc=139）。逐层定位（`dlopen` → `dlsym` → `exports` 检查 →
   `mod_register` → AES KAT）后确认：**桩层类型与上游头文件错位** —— 上游 `dprint.h` 中
   `my_pid`/`dprint_color` 是函数、`log_level_info` 是数组，而桩层写成了变量/指针；
   模块的 `LM_ERR` 日志路径因此解引用野指针。修正桩层类型（并把 `_km_log_func` 指向
   非空 sink）后 50/50 全通过。教训：**core 插件消费测试的桩层必须逐字段对齐上游头文件**，
   不能只保证符号名存在。
4. **TMPDIR 显式提供**：鸿蒙目标机 `/tmp` 只读，test_package 编译 e2e 时若沿用环境
   `TMPDIR`，clang 直接报 `unable to make temporary file: No such file or directory`。
   已在 `test_package/conanfile.py` 中显式提供一个可写临时目录（既有 `TMPDIR` 可写则沿用，
   否则退到 build 目录下 `tmp/`）。
5. **依赖零缺口**：`libgcrypt/1.12.2` 与 `libgpg-error/1.55` 制品仓均已发布（`conan download`
   实测 rc=0），故本任务不需要新建依赖项分支。
---

**编译结束**: 2026-09-30 08:11
**最终状态**: built（R29 口径：conan create / conan-verify 已全部 PASS，但尚未 `conan upload` 到制品仓 →
真实状态为 built；合并后经发布流水线上传成功再转 published。与软件级 manifest、README 状态列一致。）
