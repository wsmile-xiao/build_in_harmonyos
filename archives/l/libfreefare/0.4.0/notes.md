# libfreefare 0.4.0 适配笔记

> W3 真机 conan create 已通过（2026-09-23，rc=0，ctest 1/1 Passed）。
> 本文档记录 W0 依赖检查、源码/构建系统分析、配方与 test_package、真机 W3 实际踩坑解法。

## 一、W0 依赖发布检查（本机 conan 2.31.2 + ohpcd remote）

| 依赖 | 要求 | ohpcd 实测 | 结论 |
|---|---|---|---|
| libnfc | >= 1.7.0（PKG_CHECK_MODULES） | `libnfc/1.8.0` recipe 已发布（rev fe01b607, 2026-09-02） | ✅ 已发布 |
| openssl/libcrypto | DES_ecb_encrypt + openssl/{aes,des,rand}.h | `openssl/3.5.6` 已发布（另有 1.1.1w/3.0.16/3.5.x 等） | ✅ 已发布 |
| libusb-compat (libnfc 传递依赖) | — | `libusb-compat/0.1.7` 已发布（rev 149f825e, 2026-08-25） | ✅ 已发布 |
| Cutter（上游单测框架） | >= 1.1.7，**可选** | 本环境无；configure 探测不到 → `WITH_CUTTER=no` | ⚪ 关闭，非阻塞 |

W0 结论：**所有必需依赖均已在 ohpcd 制品仓发布，无需拆依赖库单独适配。**

检查命令（本机复现）：
```sh
conan download "libnfc/1.8.0" -r=ohpcd --only-recipe
conan download "libusb-compat/0.1.7" -r=ohpcd --only-recipe
conan list "openssl/*" -r=ohpcd
```

## 二、源码 / 构建系统分析

- 上游：https://github.com/nfc-tools/libfreefare （tag `libfreefare-0.4.0`）
- 官方源码：`https://github.com/nfc-tools/libfreefare/releases/download/libfreefare-0.4.0/libfreefare-0.4.0.tar.bz2`
- tarball sha256：`bfa31d14a99a1247f5ed49195d6373de512e3eb75bf1627658b40cf7f876bc64`
  （本机经 ghfast.top 代理下载字节实测；ghfast.top 仅用于本机分析，未写入 conandata——R39/PF7 要求配方源为官方源，CI 自动追加镜像 fallback。建议真机首跑前用官方 release 页再核一次 sha256。）
- 构建系统：**Autotools**（`configure.ac` + `Makefile.am` + libtool），同时 `AC_PROG_CXX`（libtool 需要 C++）。
- 产物：
  - 库：`libfreefare.la` → `lib/libfreefare.{a,so}`，头文件 `freefare.h`（依赖 `<nfc/nfc.h>`）。
  - examples/：13 个 `bin_PROGRAMS`（mifare-classic-*/mifare-desfire-*/mifare-ultralight-*）安装到 `bin/` → R38 需 `commands.json`（已建，软件级）。
  - test/：仅在 `WITH_CUTTER=yes` 时构建 13 个 cutter 用例；无 Cutter 时不构建、`make check` 为 0 用例。
- configure 关键检查：
  - `AC_CHECK_LIB([crypto],[DES_ecb_encrypt])` + `AC_CHECK_HEADERS([openssl/aes.h openssl/des.h openssl/rand.h])` → 必需 OpenSSL。
  - `PKG_CHECK_MODULES([LIBNFC],[libnfc >= 1.7.0])` → 必需 libnfc。
  - endian：`endian.h`/`sys/endian.h`/`CoreFoundation` 三选一（OHOS/musl 有 `endian.h`，预期通过）。
  - `CFLAGS="$CFLAGS -std=c99"`。
  - 无 `--disable-examples` / `--disable-doc` 开关（examples 与 man 无条件构建）。

## 三、本地产物清单（仅本库目录）

```
archives/l/libfreefare/
├── commands.json                 # 软件级，13 个 mifare-* 工具声明 (R38)
└── 0.4.0/
    ├── conanfile.py              # Autotools + 依赖注入（PKG_CONFIG_PATH/CPPFLAGS/LDFLAGS/LIBS=-lcrypto）
    ├── conandata.yml             # 官方源码 URL + sha256；patches 暂空
    ├── manifest.yaml             # 版本级元数据（占位 status，待 finish 定稿）
    ├── notes.md                  # 本文件
    └── test_package/
        ├── conanfile.py          # CMakeDeps/CMakeToolchain，ctest 驱动
        ├── CMakeLists.txt        # find_package(libfreefare) + add_test
        ├── test.c                # 无硬件纯计算 API 断言（扇区几何/AID/DES·AES key/MAD/TLV）
        └── MANIFEST.yml          # 上游 13 个 cutter 用例声明（Cutter+设备硬阻塞）
```

## 四、test_package 实质断言（R34，非空壳）

test.c 真实链接并调用 libfreefare API（无需读卡器）：
1. MIFARE Classic 扇区几何：`mifare_classic_sector_block_count/first/last_block/block_sector`
2. DESFire AID：`mifare_desfire_aid_new` / `aid_get_aid`
3. 密钥对象：`mifare_desfire_des_key_new_with_version` / `aes_key_new_with_version` → `key_free`（间接验证 libcrypto 链接）
4. MAD：`mad_new` / `mad_get_version` / `mad_set_version` / `mad_free`
5. TLV：`tlv_encode` / `tlv_decode` 往返
共 11 条断言。

## 五、真机 W3 实际结果（2026-09-23，conan create rc=0，ctest Passed）

真机环境：HarmonyOS aarch64（HAD-W24），conan 2.29.1（OHOS 适配版），profile `ohos-aarch64-fixed`
（os=OHOS os.version=6.0, clang 15, libc++），runner = `~/bin/ohos-test-runner.sh`（smoke 模式 + try-lock）。

实际踩坑与解法（均已固化进 conanfile.py 的 build()/generate()）：

| # | 实际问题 | 根因 | 解法 |
|---|---|---|---|
| 1 | `Invalid: settings.os.version value not defined` | 用了 `ohos-aarch64` profile（缺 os.version），与 ohpcd 预编译依赖包 package_id 对不上 | 改用 `ohos-aarch64-fixed` profile（含 os.version=6.0 + compiler_executables） |
| 2 | `configure: Permission denied (exit 126)` | HMDFS 不保留/不支持执行位，解包后 configure owner=20001006 | 不用 `./configure`，改 `sh ../configure`（只需读权限；currentUser 能读） |
| 3 | `cannot guess build type` | 2012 版 config.guess 不识别 HarmonyOS uname | configure 加 `--build/--host=aarch64-unknown-linux-gnu`（config.sub 认识 gnu；clang 仍用 PATH 里的） |
| 4 | `cannot find ar` | binutils 不在默认 PATH | PATH 加 `/data/service/hnp/binutils.org/binutils_2.45/bin` |
| 5 | `config.status: can't create ./confXXX/subs1.awk: Permission denied` (E011) | configure 内部 `(umask 077 && mktemp -d)` 建的临时目录 owner=20001006、权限 0700，currentUser 无权限 | build() 里 `sed 's/umask 077/umask 022/g' ../configure`（参照 libnfc 0003-configure.patch） |
| 6 | `libtool: link: /usr/local/lib/libusb-1.0.la is not a valid libtool archive` | libnfc.la 的 dependency_libs 硬编码了 libnfc 构建时的绝对路径 `/usr/local/lib/libusb-1.0.la`，HMDFS 上不存在 | build() 里 sed 删 libnfc.la 里的这个绝对 .la 引用（保留 -lusb + -L 找实际 libusb） |
| 7 | examples 链接 undefined symbol: libusb_* | 链接顺序：libusb-compat 引用 libusb-1.0，需 -lusb-1.0 在其后 | generate() 把所有 dep 的 `-l` 注入 LIBS 末尾（参照 libnfc） |
| 8 | test_package `fatal error: nfc/nfc.h not found` | freefare.h 直接 include <nfc/nfc.h>，但 libnfc 未标记传递头 | requires 加 `transitive_headers=True` |
| 9 | 真机下 GitHub 源码慢/卡 | 真机直连 GitHub 不可达 | 本机下载 tarball 经 base64 传到真机，conandata 临时改 file://（PR 版本仍写官方 URL） |

最终：`conan create` rc=0，test_package `1/1 Passed`，`100% tests passed`。
产物：`lib/libfreefare.a` + 13 个 `bin/mifare-*` + `include/freefare.h`。

## 六、下一步（W4 审计 → PR）

1. 本机 worktree 提交 `feat/libfreefare-0.4.0`，推 Fork。
2. 走 `ohc-run.py finish libfreefare 0.4.0 built`（W4 审计 + AI Review + CI 闭环）。
3. CI 会自动追加镜像 fallback 下官方源码（真机临时 file:// 不进 PR）。
4. 注意：build() 里的 sed 修法（#5/#6）目前是运行时 patch，后续可固化为 `patches/0003-configure.patch`（参照 libnfc）。

## 七、本轮状态

- W0：✅ 通过（依赖均已发布）
- 源码/构建系统分析：✅ 完成（Autotools，依赖 libnfc+openssl）
- 配方 + test_package：✅ 已就绪
- 本机验证：✅ 源码 sha256 实测、目录结构、test.c 断言自洽
- 真机 W3：✅ conan create rc=0，ctest Passed，产物真实存在
- W4 审计 / PR：⏳ 下一步
