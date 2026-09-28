# systemd 261.1 适配笔记

## 编译环境
- 构建系统: meson（conan 驱动）
- 编译日期: 2026-09-19
- 平台: aarch64-unknown-linux-ohos（HarmonyOS PC，os=OHOS/6.0, clang-15, musl libc）
- 编译器: clang/clang++
- 状态: built（conan create + test_package 本地验证通过；未 upload，发布由 CI release 流水线执行）

## 版本与源码
- 上游: https://github.com/systemd/systemd，tag v261（官方源，R39 合规）
- 源码 tarball: v261.tar.gz，sha256 `f1c2e6a0d19ea5cae946386eb288432de12f3c6b7730cdb0d2a06f8ab8e3f8dc`（实测下载校验一致）
- 本配方版本: 261.1（R37 修复后缀；registry 已存在 261 → 避免 revision 冲突必须用 261.1）

## 编译步骤（conan create 全流程）

```bash
conan create archives/s/systemd/261.1 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

1. source(): get() 官方 GitHub v261 tarball（strip_root）。
2. generate(): MesonToolchain + OHOS 内核风格宏空定义（__user/__force/__iomem/__kernel）+
   `-DHAVE_MALLINFO2=1`；依赖 .pc 复制 + prefix 改写 + PKG_CONFIG_PATH 注入
   （libcap/liblzma/libzstd/zlib/libxcrypt/libucontext）；_inject_meson_archiver
   （真机 hnp 工具链 ar/llvm-ar 不在 PATH → 注入 conan_meson_native.ini）。
3. build(): apply_conandata_patches（21 个 musl portability 补丁）→ meson configure
   （`-Dlibc=musl` 启用 src/libc/musl 兼容层；关闭 daemon/缺依赖组件）→
   `ninja libsystemd.so.0.44.0` 单目标（1540 全目标构建超时不必要）。
4. package(): 手动复制 libsystemd.so.0.44.0 + 版本链软链 + src/systemd 公开头文件 +
   libsystemd.pc + LICENSE；`_sign_shared_libs()` 用 OHOS binary-sign-tool 自签名
   （CI 运行 dlopen 必需，实测 .codesign section 存在）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `settings.os.version value not defined`（conan create 报 3 包 Invalid） | 本机 ~/.conan2/settings.yml 的 OHOS version 枚举不含 None，未声明 os.version 子设置的配方校验失败 | 本机 settings.yml OHOS version 加 `null`（用户级配置，非仓库文件）；CI 配置本就允许 |
| 2 | libzstd 二进制包 pkg 目录缺失（AssertionError folder must exist） | 被杀进程留下损坏缓存条目（index 存在、物理目录空） | `conan remove zstd:* -c` 等 6 依赖全部 remove -c 清损坏项 → 重下 |
| 3 | ninja 生成 systemd-runtest.env 报 `printf: bad %q` | meson 缓存 /system/bin/printf（OHOS 系统 printf 不支持 %q） | 用 coreutils printf（usr/local/bin/printf 支持 %q）手工生成该构建产物；.dat 亦改写 |
| 4 | test-pressure/test-bus-benchmark 编译失败 | OHOS musl sysroot pthread.h 缺 pthread_cancel 声明 | 平台工具链限制，如实计入台账（未实例化为"编译失败"类），不阻塞 libsystemd 交付 |
| 5 | 上游测试失败 127 项 | 全为 OHOS 沙箱平台限制（/tmp EROFS 硬编码 mkdtemp、safe_fclose EBADF、无 bpf/capability） | 逐项如实计 failed（非跳过），并入分母；TMPDIR/TMP/TEMP 指到可写目录复验 |

## 源码修改

21 个 portability 补丁（见 patches/，conandata.yml 逐一说明）：
- 0001: units/meson.build 移除含 \x2d 转义文件名的 daemon slice 条目（HMDFS 无法 stat）
- 0002-0021: OHOS musl 兼容层——explicit_bzero/statx/crypt_r/mallinfo2/secure_getenv/
  reallocarray/sigisemptyset/mqueue/getcwd/pwd/grp/shadow/userdb/ucontext/crypt_r 实现、
  libintl、errno program_invocation、测试支持（qsort_r TLS/.inc 生成/b_ndebug）

## 依赖版本

| 包 | 版本 | 状态 |
|----|------|------|
| libcap | 2.69 | ohpcd 已发布 |
| liblzma | 5.8.1 | ohpcd 已发布 |
| libzstd | 1.5.7 | ohpcd 已发布 |
| zlib | 1.3.1 | ohpcd 已发布 |
| libxcrypt | 4.5.2 | ohpcd 已发布（ohpcd 包名 libxcrypt，非 libcrypt） |
| libucontext | 1.5.2 | ohpcd 已发布 |

W0 预检全部 `conan download --only-recipe -r=ohpcd` 通过。

## 验证结果

```bash
# 1. conan create（交叉编译 + test_package）
conan create archives/s/systemd/261.1 --build=missing -pr:h=... -pr:b=...
# → exit 0；test_package: test_systemd.py OK + CONSUMER_PASSED

# 2. 消费者用例（公开 API 运行时验证）
./test_consumer
# → CONSUMER_OK: sd-event timer fired=1 (sd_event_new/add_time/run/unref verified)

# 3. 上游测试双口径台账（2026-09-19 实测）
# 源码声明 252 / 配置可执行 363（构建成功 361）/ 实际执行 361 /
# 通过 193 / 跳过 40 / 失败 127（全为 OHOS 沙箱平台限制）/ 超时 1 / 未实例化 16
# 当前配置可执行通过率 193/361 (53.5%)；详见 reports/upstream-tests-ledger.md 与 mapping.tsv
```

## 交付物

| 文件 | 说明 |
|------|------|
| libsystemd.so.0.44.0 + 版本链 | libsystemd 客户端库（sd-bus/sd-event/sd-daemon），已 OHOS 自签名 |
| include/systemd/*.h | 公开头文件（sd-bus.h/sd-event.h/sd-daemon.h 等） |
| libsystemd.pc | pkg-config 文件 |

## 注意事项

- systemd 是 Linux init 系统，OHOS 不运行其守护进程——daemon 运行类功能按平台限制
  声明；libsystemd 客户端库是本适配交付物，编译链接运行可用（消费者实测）。
- 上游测试失败项均为平台限制非适配缺陷，已在台账如实分类（不写跳过/不写通过）。
- 版本 261.1 与 registry 已存在的 261 不冲突（R37 后缀规则）。
- 本机 /tmp 只读（E002），所有构建/测试统一用 $TMPDIR=/storage/Users/currentUser/tmp。
---

**编译结束**: 2026-09-19 11:55
**最终状态**: built

## r03 追加：跳过 40 项强制执行返工（2026-09-19）

- 用户裁定 40 项 exit 77 不得以"自身 SKIP"豁免；本轮完成逐项归因
  （reports/r03-skip-cause-ledger.md，引用上游源码行）、启用尝试
  （reports/r03-feature-enable-attempt.md：首次/末次 registry 复核 + slow-tests 启用
  后重建实跑仍 rc=77）、权限/平台隔离探针（reports/r03-permission-platform-probes.md：
  13 探针 + 40 项逐入口重测 + 0700 候选挂载点/TMPDIR/能力位）。
- 双口径不变：252 声明/363 配置/361 执行/193 通过/40 跳过（已逐项证明不可运行）/
  127 平台限制失败/1 超时/16 未实例化；skipped 每项有源码行 + 探针 + 恢复条件。
