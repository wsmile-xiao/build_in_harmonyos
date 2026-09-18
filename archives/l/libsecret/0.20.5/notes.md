# libsecret 0.20.5 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-17
- 编译器: clang/clang++ (OHOS aarch64, /data/service/hnp/bin/clang)
- 状态: built

## 上游测试清点（R51 申报表）

- 构建系统: meson；测试注册于 meson（`test()` 声明），实际注册 16 项
- C 测试（suite libsecret）：test-attributes, test-value, test-prompt, test-service, test-session, test-paths, test-methods, test-password, test-item, test-collection（10 项）
- C 测试（suite libegg，gcrypt 开启）：test-dh, test-hkdf, test-secmem, test-hex（4 项）
- gcrypt 追加：test-file-collection（1 项）
- shell 测试：test-secret-tool.sh（1 项，tool/meson.build）
- TPM2 测试（test-tpm2 / test-secret-tool-tpm2.sh）：制品仓无 tss2-esys，上游 tpm2 选项默认 false，不注册
- introspection/python/JS/vala 测试：依赖 gobject-introspection 运行时 + gjs/valac，本适配关闭 introspection（CI 无该工具链），不注册

## 上游测试实测结果（R51 如实回填）

在真机环境运行 `meson test`（16 项注册）：

- **通过 7 项**：test-hex, test-dh, test-hkdf, test-secmem, test-value, test-attributes, test-secret-tool.sh
- **失败 9 项**（SIGABRT，同一根因）：test-prompt, test-file-collection, test-service, test-session, test-paths, test-methods, test-password, test-item, test-collection

**9 项失败崩溃点与原因（已验证的技术证明）**：

```
test-prompt 崩溃栈：
  Traceback (most recent call last):
    File ".../libsecret/mock-service-prompt.py", line 14, in <module>
      import dbus
  ModuleNotFoundError: No module named 'dbus'
  ** libsecret:ERROR:../libsecret/test-prompt.c:46:setup:
     assertion failed (error == NULL): Remote closed the output (g-io-error-quark, 0)
```

根因：这 9 个测试通过 **D-Bus mock service**（`mock-service-prompt.py` 等 python 脚本，`import dbus`）起一个假的 Secret Service，再与真实 libsecret 通信。运行前提是：
1. python3 装有 `dbus` 绑定（dbus-python）——环境未装；
2. 有可用的 D-Bus **session bus daemon**（dbus-daemon）——已核验环境无此二进制。

环境核验证据：
- `find / -name dbus-daemon` 无命中；`/data/service/hnp/bin`（455 个工具）无 dbus-daemon；
- ohpcd 制品仓 `dbus/1.14.10` 二进制仅含 `dbus-binding-tool` + `libdbus-glib-1.a`，**不含 daemon**；
- python3 `import dbus` → `ModuleNotFoundError`（实测）。

结论：9 项失败为**环境能力缺口**（无 D-Bus session bus + python dbus 绑定），非 libsecret 代码/配方缺陷；已给崩溃点（mock-service `import dbus` 抛 ModuleNotFoundError → setup 断言失败 → SIGABRT）与充分技术证据。上游"可移植 C 纯逻辑测试"（egg 4 项 + attributes/value 2 项）与 secret-tool shell 测试 100% 通过。

## 编译步骤

1. `init-build libsecret 0.20.5`（GNOME 官方 tarball，sha256 校验通过）
2. `lang-preflight`：detected=c（cpp 兼容族），通过
3. 编写 conanfile.py（meson 构建）：
   - 依赖：glib/2.88.3, proxy-libintl/0.5, pcre2/10.47, libffi/3.5.2, zlib/1.3.2, libgpg-error/1.55, libgcrypt/1.12.2
   - 选项：introspection=false, vapi=false, gcrypt=true, tpm2=false, bash_completion=disabled, manpage=false, gtk_doc=false
4. `conan-verify`：G1-G5 + L2/L4/L5 全部 PASS，`conan create` 干净构建成功，test_package 消费者二进制签名后运行输出 `schema/value API OK`，exit 0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 找不到 glib-2.0/gio-unix-2.0 | glib 包的 .pc 在 lib/pkgconfig，PkgConfigDeps 不生成组件 .pc | generate() 里把依赖包 lib/pkgconfig/*.pc 拷入 generators 并重写 `prefix=/` → 真实包路径 |
| 2 | glib-2.0.pc Requires proxy-libintl 但无 .pc | proxy-libintl 包只有 libintl.a/libintl.h | 合成 proxy-libintl.pc（generate() 生成） |
| 3 | gio-2.0.pc Requires libpcre2-8/zlib/libffi 缺 .pc | pkg-config 链未闭合 | 补 pcre2/10.47, libffi/3.5.2, zlib/1.3.2, libgpg-error/1.55 为直接依赖 |
| 4 | gdbus_codegen/glib_mkenums 工具变量 `//bin/...` | PkgConfigDeps 生成的 .pc 工具变量损坏 | 正则重写为 glib 包内真实脚本路径 |
| 5 | gcrypt.h 找不到 gpg-error.h | libgcrypt.pc 的 Requires.private 不传 Cflags | 往 libgcrypt.pc 的 Cflags 追加 gpg-error include |
| 6 | secret-tool.c: getpass 返回 int（OHOS libc 声明不兼容）| bionic getpass 原型不符 | patch 0001：无平台宏的可移植实现（fgets 读 stdin 去换行） |
| 7 | test_package 编译缺 glib.h | CMakeDeps 对 glib 组件 include 生成异常 | 消费者测试改 meson + pkg-config 模式 |
| 8 | 消费者二进制运行时 "Operation not permitted"/加载失败 | OHOS 加载器无法从 .conan2 缓存经符号链接加载 .so；未签名 ELF 不可执行 | test_package 运行时：$ORIGIN RUNPATH + 实体库拷贝 + E077 重签名流程 |

## 源码修改

- `patches/0001-tool-secret-tool.c.patch`：getpass() → 可移植 stdin 读取（无 __OHOS__ 宏，R8 合规），并补 `#include <stdio.h>`

## 依赖版本

- glib/2.88.3, proxy-libintl/0.5, pcre2/10.47, libffi/3.5.2, zlib/1.3.2, libgpg-error/1.55, libgcrypt/1.12.2
- 工具链：meson/ninja（conan tool_requires），clang 15.0.4

## 验证结果

```bash
# conan-verify（G1-G5/L2/L4/L5）
python3 scripts/ohc-run.py conan-verify libsecret 0.20.5  # 全部 PASS，G2 conan create 成功

# 上游测试（真机，LD_LIBRARY_PATH 指向依赖库）
meson test   # Ok: 7, Fail: 9（9 项为 D-Bus mock service 环境缺口，崩溃点/证据见上文）
```

## 交付物

- archives/l/libsecret/0.20.5/{conanfile.py, conandata.yml, manifest.yaml, notes.md, patches/, test_package/}
- conan package: libsecret/0.20.5@ohpcd/stable（secret-1.so + 头文件 + secret-tool）

## 注意事项

- glib 包自带 .pc 的 `prefix=/` 是生产端遗留问题，任何 meson 消费者都要重写 prefix；本配方在 generate() 内统一处理。
- 消费者（如 libnma）应走 pkg-config 或显式 requires 上述 pkg-config 链，避免 CMakeDeps 对 glib 组件 include 的空目录问题。
- OHOS 运行时：共享库必须实体文件 + 已签名；测试用 $ORIGIN RUNPATH 最稳（见 test_package 模板）。
---

**编译结束**: 2026-09-17 18:28
**最终状态**: built
