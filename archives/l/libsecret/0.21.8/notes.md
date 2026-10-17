# libsecret 0.21.8 适配笔记

## 编译环境
- 构建系统: meson 1.11.1 + ninja
- 编译日期: 2026-09-20
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built（conan-verify G0-G4/L2/L4/L5 全过，待 PR 合并后 CI upload）

## 0.21.8 vs 0.21.7 变更分析（W0b 历史比对）

| 上游变更 | 适配影响 | 结论 |
|---|---|---|
| linker version script（libsecret.map，隐藏私有符号） | lld 支持 -Wl,--version-script；cc.get_supported_link_arguments 自动探测 | 无需适配，符号导出正常（test_package 消费验证通过） |
| file-backend flock() 线程安全锁（!171） | 新代码用 O_CREAT/O_RDWR 但未含 <fcntl.h>（glibc 传递引入，musl 不传递） | **补丁 0002**：+1 行 #include <fcntl.h> |
| egg test-dh-length 新测试（!170 DH 长度回归） | 纯 libgcrypt 计算，无 D-Bus 依赖 | 纳入可运行测试（2000 试验实测 14.3s） |
| meson test_setup feature 选项（!162） | 默认 auto，无 dbus-run-session 仅提示 | 无需传参，行为同 0.21.7 |
| 单独加密 items（!174）、content-type 参数（#114） | file-collection 格式变更，测试覆盖 | test-file-collection 实测通过 |
| secret-tool --collection 选项（!164） | 无平台相关代码 | 无需适配 |

## 编译步骤

```bash
# 1. W0 依赖核验（制品仓 R35 探测，已发布）
conan download "glib/2.84.0.1" -r=ohpcd
conan download "libgcrypt/1.11.0" -r=ohpcd

# 2. conan create（CI 同款，配方驱动：glib .pc prefix 重写 + _MUSL_LINK_ARGS + 上游测试）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable

# 3. 上游测试（conan build() 内自动执行，也可手动复现）
meson test -v -C builddir --timeout-multiplier=16 --no-rebuild \
  libsecret:test-hex libsecret:test-secmem libsecret:test-dh libsecret:test-dh-length \
  libsecret:test-hkdf libsecret:test-attributes libsecret:test-value \
  libsecret:test-file-collection "libsecret:test-secret-tool.sh"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `secret-file-collection.c:836: error: use of undeclared identifier 'O_CREAT'/'O_RDWR'` | 0.21.8 新增 flock 锁代码用 O_CREAT/O_RDWR，上游靠 glibc `<sys/file.h>` 传递引入 `<fcntl.h>`；OHOS musl 头文件严格不传递 | 补丁 0002：`#include <fcntl.h>`（纯可移植性，无平台宏） |
| 2 | `Program //bin/gdbus-codegen found: NO` | glib 包 .pc prefix=/（DESTDIR 安装） | 配方 generate() 重写 glib .pc prefix（0.21.7 同款 accountsservice/GOA 模式） |
| 3 | `error: call to undeclared function 'getpass'` | OHOS musl libc 有 getpass 符号但 SDK unistd.h 无声明 | 补丁 0003：补 extern 声明（glib/2.84.0 patch 0002 同款） |
| 4 | 链接 `undefined symbol: getpass` | SDK sysroot libc.so 无 getpass；只有系统 musl loader 有 | `-L/lib -l:ld-musl-aarch64.so.1`（glib 配方 _MUSL_LINK_ARGS 同款） |
| 5 | egg 测试 scratch 硬编码 /tmp（E002 只读） | 上游硬编码 | 补丁 0001：g_get_tmp_dir()（0.21.7 同款）+ 顺带修复中间字符串未释放（W4 审计 P3 建议） |
| 6 | meson install 重写 DT_RUNPATH 导致 .codesign 失效 | OHOS loader 校验嵌入哈希（libsoup3 教训） | package() 从 builddir 拷回链接原产物（0.21.7 同款） |

## 上游测试定性（R51 三步法）

**Step 1 清点**：meson 注册 **17 个测试目标**（`meson test --list` 实测）：
- egg（suite libegg）：test-hex、test-secmem、test-dh、**test-dh-length（0.21.8 新增）**、test-hkdf
- libsecret（suite libsecret）：test-attributes、test-value、test-prompt、test-service、test-session、test-paths、test-methods、test-password、test-item、test-collection、test-file-collection
- tool（suite secret-tool）：test-secret-tool.sh

**Step 2 实测**（conan create 构建期，本机 OHOS 实跑）：

| 测试目标 | TAP 子用例 | 结果 |
|---|---|---|
| test-hex | 4 | ✅ |
| test-secmem | 7 | ✅ |
| test-dh | 8 | ✅（perform/short_pair 仅非 quick 模式注册） |
| test-dh-length | 1 | ✅ 14.30s（2000 次试验） |
| test-hkdf | 7 | ✅ |
| test-attributes | 12 | ✅ |
| test-value | 11 | ✅ |
| test-file-collection | 8 | ✅（含 0.21.8 新增 concurrent-write；subprocess 半用例在 g_test_trap 子进程内运行） |
| test-secret-tool.sh | 6 | ✅ |
| **合计** | **64** | **ok 64 / not ok 0** |

**Step 3 豁免依据**（8 目标 139 注册子用例）：test-prompt/service/session/paths/methods/password/item/collection 依赖 python D-Bus mock service（libsecret/mock/service.py），需要 `python3 dbus`/`dbus.glib` 模块 + `gi.repository`（PyGObject）+ D-Bus session bus（dbus-daemon）。OHOS 无 dbus-daemon，python3 无 dbus/gi 模块（0.21.7 实测：pip 装 dbus-python 后仍缺 gi + 无 session bus 可连）。豁免证据报错原文：
```
ModuleNotFoundError: No module named 'dbus'
libsecret:ERROR:../libsecret-0.21.8/libsecret/test-prompt.c:46:setup:
assertion failed (error == NULL): Remote closed the output (g-io-error-quark, 0)
```

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| glib | 2.84.0.1 | ohpcd 制品仓（携带 libffi/3.4.4、pcre2/10.45、zlib/1.3.1.1） |
| libgcrypt | 1.11.0 | ohpcd 制品仓（携带 libgpg-error/1.55） |

## 验证结果

```
conan-verify: G0 ✅ G1 ✅ G2 ✅ G3 ✅ G4 ✅ L2 ✅ L4 ✅ L5 ✅
meson test: Ok 9 / Fail 0 / Skip 0（64 TAP 子用例全过）
test_package: consumer test PASS + secret-tool file 后端 store/lookup/clear 冒烟 PASS
```

## 注意事项

- 版本号 0.21.8 为上游正式版（download.gnome.org 官方源），非 fork
- 配方沿用 0.21.7 的 `_MUSL_LINK_ARGS`（secret-tool 链接系统 musl 的 getpass）与 package() 签名恢复逻辑
- 0.21.7 已在制品仓（libsecret/0.21.7），本版本 0.21.8 为新增目录，不触碰旧版本
---

**编译结束**: 2026-09-20 15:54
**最终状态**: built
