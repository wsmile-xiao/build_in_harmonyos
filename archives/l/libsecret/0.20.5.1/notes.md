# libsecret 0.20.5.1 适配笔记

> 本版本 = 上游 `0.20.5` + OHOS 适配修复后缀 `.1`（R37）。
> 目标：为 **glib/2.88 Qt6 链**（`libnm/1.58.0`、`gsettings-qt/1.1.1`、
> `qtbase-sql-dbus/6.11.1`、`networkmanager-qt/6.26.0`、`kylin-nm-base/4.20.0.0`）
> 提供**真正可被 OHOS 加载器加载**的 `libsecret`，解除
> `kylin-keyring/4.20.0.0` 与 `kylin-nm-plugin/4.0.0.1` 的阻塞。

## 编译环境

- 构建系统: meson（tool_requires `meson/1.11.0`，不依赖全局 PATH / pip）
- 编译日期: 2026-10-01
- 编译器: clang/clang++ 15.0.4（OHOS aarch64, `/data/service/hnp/bin/clang`）
- Profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS 6.0, arch=armv8, Release）
- 状态: built
- 宿主实机即 OpenHarmony aarch64（`uname -a` → `HongMeng Kernel 1.12.0`），
  因此 `dlopen` 验收测试可在本机真实执行，无需交叉运行。

## 1. 为什么需要 0.20.5.1（根因）

### 1.1 版本选型

| 版本 | requires | 结论 |
|------|----------|------|
| `0.21.7` | `glib/2.84.0.1` | ❌ 与 Qt6 链所需的 `glib/2.88.3` **冲突**，不可用 |
| `0.21.8` | `glib/2.84.0.1` | ❌ 同上 |
| `0.20.5` | `glib/2.88.3` | ✅ **代际正确**，但已发布二进制不可加载（见 1.2） |

### 1.2 已发布 `libsecret/0.20.5` 的缺陷（E077）

在 **完全干净的 conan home**（`CONAN_HOME=~/tmp/libsecret-task/chome`，
仅 `conan download libsecret/0.20.5 -r=ohpcd`，`conan cache check-integrity` = ok，
md5 = `4a8b92a9793b26f798a1ffa5efec27c9` 与 `conanmanifest.txt` 一致）实测：

| 库 | 来源 | `dlopen(RTLD_NOW)` |
|----|------|--------------------|
| `libglib-2.0.so.0` | ohpcd 发布件（依赖） | ✅ OK |
| `libQt6Core.so.6.11.1` | ohpcd 发布件 | ✅ OK |
| **`libsecret-1.so.0.0.0`** | **ohpcd 发布件（0.20.5）** | ❌ **EACCES `Permission denied`** |

对同一文件做 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`
后 `dlopen` 成功 ⇒ **发布的 `0.20.5` 产物携带失效的 `.codesign` 段**。

更关键的是：**本配方从源码重新 `conan create` 也复现了同一缺陷**
（新产物 `libsecret-1.so.0.0.0` 同为 436736 字节，同样 `dlopen` → EACCES）。
说明这不是"上传时损坏"，而是**配方/构建流程的系统性缺陷**，因此必须新版本修复。

### 1.3 根因定位：meson install 的 RPATH 重写打掉签名

OHOS 链接器为每个产物写入 `.codesign`（4 KiB）自签名段，HarmonyOS 加载器
**拒绝签名不验证的 ELF**（`dlopen` → EACCES；`exec` → `Operation not permitted`）。

`meson install` 会用 `patchelf` 重写每个已安装 target 的 RPATH —— **这一步会
静默使签名失效**。上游 libsecret 的 meson 构建对 `libsecret-1.so.*` 与
`bin/secret-tool` 都写入被重写的 RPATH，因此**本配方产出的每个 ELF 都受影响**，
与已发布 `0.20.5` 表现完全一致。

反证（同一台机器上的受控实验）：

```
A 链接器新产出 .so（.codesign 有效）      -> dlopen OK
B 仅 objcopy --remove-section .codesign   -> dlopen FAIL: Permission denied
C B 再 binary-sign-tool -selfSign 1       -> dlopen OK
D C 的字节拷贝                             -> dlopen OK
```

即：**有有效签名 → 可加载；签名缺失或失效 → EACCES**。字节拷贝本身不影响，
所以能排除"Conan 缓存符号链接/路径"假说。

## 2. 修复方案（E077 / ML-0043 四步法，仓库既有先例）

仓库内既有同款修复先例：`archives/c/cairo/1.18.4.2/conanfile.py::_sign_shared_libs`
（注释："meson install rewrites rpath which invalidates the linker self-signature;
OHOS XPM dlopen then reports Permission denied"）与
`archives/g/glib/2.88.3.1/conanfile.py` 的完整签名校验实现。

本配方在 `package()` 中 `meson.install()` **之后**调用 `_resign_ohos_elfs()`：

1. 遍历包内 `lib/` 与 `bin/`，只取**实体 ELF**（跳过 SONAME 符号链接，每个实体只签一次）；
2. 仅对含 `.codesign` 或 `.note.ohos.ident` 的 **OHOS ELF** 生效
   （glibc/Linux 构建两者皆无 → 自动 no-op，保持跨平台安全）；
3. 依次执行：`llvm-objcopy --remove-section .codesign` →
   `binary-sign-tool sign -inFile X -outFile X.signed -selfSign 1` → `os.replace` →
   `chmod` 恢复执行位（签名工具会把权限位归零）；
4. 若包内存在 OHOS ELF 但签名工具缺失 → **直接 `ConanException` 硬失败**，
   绝不放行一个必然不可加载的产物。

工具路径来源遵循 **R33**（不得裸用 `${CC}`/`${CFLAGS}` 等 shell 变量）：
依次尝试 `tools.build:compiler_executables.c` 同目录 → `/data/service/hnp/bin`
→ `shutil.which`。子进程使用 **list 形式**（不启 `/bin/sh`），避免 OHOS
只读 `/tmp` 造成 `sh*.tmp` 失败（E002）。

## 3. test_package 验收测试（本版本新增，针对 0.20.5 缺陷）

| 探针 | 是否链接 libsecret | 作用 |
|------|-------------------|------|
| `link_probe` | ✅ 经 `secret-1` pkg-config 模块链接 | 下游**链接契约**（头文件目录 + `-lsecret-1`） |
| `dlopen_probe` (test.c) | ❌ 只链接 libdl | **可加载性验收**：`dlopen("libsecret-1.so.0", RTLD_NOW)` + `secret_*` 符号解析与真实调用 |

**为什么 `dlopen_probe` 不链接 libsecret**：若探针链接了 libsecret，加载器会在
进程启动时就映射它，此时 `dlopen` 只是取回已映射的 handle，**恰好会掩盖我们
要抓的缺陷**。所以探针只链接 libdl，显式 `dlopen` *被测产物*。

`test()` 中先把**产物库与全部依赖库按真实文件逐字节拷贝**到 runtime 目录
（OHOS 加载器无法通过 Conan 缓存的符号链接加载 `.so`），再以
`LD_LIBRARY_PATH=<runtime>` 运行两个探针。

**关键：被测的 `libsecret-1.so.0` 拷贝保持字节不变、绝不重签** —— 这样测的
才是"真正要交付的那个产物是否可加载"。依赖库同样字节拷贝不重签。

同理，探针二进制**故意不做 `meson install`**：install 期的 RPATH 重写会剥离
探针自身签名使其不可执行（上面第一次尝试即因此报 `Operation not permitted`）。
改用 build 树产物（`build_rpath` 由链接器写入，签名有效）。

### 实测输出（`conan create`，exit 0）

```
== link probe (downstream link/load contract) ==
LINK PROBE: -lsecret-1 link + secret_value_* call OK

== dlopen acceptance probe (RTLD_NOW on the produced artifact) ==
ACCEPTANCE: dlopen(RTLD_NOW) OK, handle=0x3bc1c3250d1b38b0
ACCEPTANCE: secret_* symbol resolution 12/12
ACCEPTANCE: secret_value_new/get/unref roundtrip OK
RESULT: libsecret-1.so.0 loaded with RTLD_NOW and secret_* API callable
```

## 4. 上游测试清点（R51 申报表）

- 构建系统: meson；测试注册于 meson（`test()` 声明），实际注册 16 项
- C 测试（suite libsecret，10 项）：test-attributes, test-value, test-prompt,
  test-service, test-session, test-paths, test-methods, test-password,
  test-item, test-collection
- C 测试（suite libegg，gcrypt 开启，4 项）：test-dh, test-hkdf, test-secmem, test-hex
- gcrypt 追加：test-file-collection（1 项）
- shell 测试：test-secret-tool.sh（1 项，tool/meson.build）
- TPM2 测试：制品仓无 tss2-esys，上游 tpm2 选项默认 false，不注册
- introspection/python/JS/vala 测试：依赖 gobject-introspection 运行时 + gjs/valac，
  本适配关闭 introspection（CI 无该工具链），不注册

## 5. 上游测试实测结果（R51 如实回填）

在真机环境运行 `meson test`（16 项注册）：

- **通过 7 项**：test-hex, test-dh, test-hkdf, test-secmem, test-value,
  test-attributes, test-secret-tool.sh
- **失败 9 项**（SIGABRT，同一根因）：test-prompt, test-file-collection,
  test-service, test-session, test-paths, test-methods, test-password,
  test-item, test-collection

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

根因：这 9 个测试通过 **D-Bus mock service**（`mock-service-prompt.py` 等 python
脚本，`import dbus`）起一个假的 Secret Service，再与真实 libsecret 通信。运行前提：

1. python3 装有 `dbus` 绑定（dbus-python）—— 环境未装；
2. 有可用的 D-Bus **session bus daemon**（dbus-daemon）—— 已核验环境无此二进制。

环境核验证据：

- `find / -name dbus-daemon` 无命中；`/data/service/hnp/bin`（452 个工具）无 dbus-daemon；
- ohpcd 制品仓 `dbus/1.14.10` 二进制仅含 `dbus-binding-tool` + `libdbus-glib-1.a`，
  **不含 daemon**；
- python3 `import dbus` → `ModuleNotFoundError`（实测）。

结论：9 项失败为**环境能力缺口**（无 D-Bus session bus + python dbus 绑定），
非 libsecret 代码/配方缺陷。上游"可移植 C 纯逻辑测试"（egg 4 项 + attributes/value 2 项）
与 secret-tool shell 测试 **100% 通过**（7/7）。

## 6. 与 0.20.5 的关系 / 复用内容

`0.20.5.1` 复用 `0.20.5` 的配方骨架与补丁，**未新增补丁**：

- 源码：GNOME 官方 tarball（sha256 校验通过）
- 补丁：`patches/0001-tool-secret-tool.c.patch`（getpass() → 可移植 stdin 读取，
  bionic 声明不兼容）—— 原样复用
- 依赖集合不变（7 个，代际正确）
- 构建选项不变（introspection/vapi/manpage/gtk_doc/tpm2 关闭，gcrypt 开启）

**新增/变更**：

| 项 | 变更 | 原因 |
|----|------|------|
| `version` | `0.20.5` → `0.20.5.1` | R37 适配修复后缀 |
| `build_requirements()` | 新增 `tool_requires("meson/1.11.0")` | R33：不依赖未定义 shell 环境；CI/沙箱无全局 meson |
| `build()` | 删除 `pip install --user meson` 兜底 | 同上；构建期联网安装不可复现 |
| `package()` | 新增 `_resign_ohos_elfs()` | E077 根因修复（见第 1、2 节） |
| `package_info()` | 新增 `cpp_info.bindirs = ["bin"]` | 包确实提供 `secret-tool` CLI，R38 要求软件级 commands.json 有对应声明 |
| `conandata.yml` | 官方源提到首位，镜像作 fallback | R39 |
| `test_package/` | 新增 `link_probe` + `dlopen_probe` 验收测试 | 本任务核心验收要求 |

## 7. 环境注意（复现须知）

本工作区内 `~/.conan2` 的 **glib/2.88.3 缓存曾被同工作区其他协作者任务污染**
（`lib/libglib-2.0.so.0` md5 与 `conanmanifest.txt` 不符，导致该依赖也报
`Permission denied`）。已 `conan remove glib/2.88.3:* -c` + 重新
`conan download glib/2.88.3 -r=ohpcd` 恢复，恢复后 `dlopen` 正常。
**这是本地缓存卫生问题，与 libsecret 配方无关**；CI 使用干净缓存不受影响。

## 8. 下游契约

| 项 | 值 |
|----|-----|
| conan 引用 | `libsecret/0.20.5.1` |
| pkg-config 模块名 | `libsecret-1`（另附 `libsecret-unstable`） |
| 库名 / SONAME | `libsecret-1.so` / `libsecret-1.so.0` |
| 头文件目录 | `<prefix>/include/libsecret-1`（`#include <libsecret/secret.h>`） |
| CLI | `<prefix>/bin/secret-tool` |
| 直接依赖 | glib/2.88.3, proxy-libintl/0.5, pcre2/10.47, libffi/3.5.2, zlib/1.3.2, libgpg-error/1.55, libgcrypt/1.12.2 |
| 运行时 NEEDED | libglib-2.0.so.0, libgio-2.0.so.0, libgobject-2.0.so.0, libgcrypt.so.20, libc.so |
---

**编译结束**: 2026-10-10 18:48
**最终状态**: built
