# DRAFT-ohos-la-libdir-hardcode — 依赖包 .la（libtool archive）libdir 硬编码 //lib

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-03
> **Severity**: 🟡 medium | **Category**: ohos / libtool / .la / linking

## 相关既有条目（同族差异化定位）

本 skill 与既有 "pkg-config/.pc 改写" 及 ".la 依赖" 条目共享依赖注入背景，但本条目是
**`.la`（libtool archive）文件的 libdir/dependency_libs 硬编码**——非重复条目；
申报路径 B 时以此差异化定位为准。

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **DRAFT-ohos-pc-libdir-hardcode**（systemd） | 草稿 | **.pc** 把 libdir/includedir 硬编码 `/usr/lib`、`/usr/include`（非 ${prefix}） | 同族（依赖元数据硬编码路径），但**载体不同**——那是 `.pc`（pkg-config 解析、configure/link 阶段 `-L` 指向 /usr/lib → `unable to find library -l`）；本条目是 **`.la`（libtool archive，libdir=//lib + dependency_libs 引用 //lib/libxxx.la）**，libtool 链接按绝对路径 sed 报 `is not a valid libtool archive`。**修法不同**：.pc 改写 prefix/libdir 即可；.la 需复制改写 + `-L staging` 注入 **configure** LDFLAGS（bake 进 Makefile 才生效） |
| **E123**（meson 静态库 libintl） | 正式收录 | 链接期 g_libintl_* 符号缺失 | 非本题——那是**符号缺失**；本条目是**.la 路径变量硬编码**导致 libtool 找不到 archive |
| **DRAFT-6048-babeltrace-glibtest-autotools** | 草稿 | autotools 构建 glib 测试 | 非本题——那是**测试构建**；本条目是 **libtool 链接期 .la 解析** |

> 全库查证（2026-09-03）：`.la`/`libtool archive`/`is not a valid libtool archive`/
> `dependency_libs` 硬编码命中 0 条——无正面撞车；本条目为 pc-libdir-hardcode 的
> `.la` 载体增量。

## Scope（何时用）

在 OHOS 上用 autotools/libtool 构建、链接依赖 glib/pcre2 等**带 .la 的依赖包**时，若出现：

- `libtool: error: '//lib/libxxx.la' is not a valid libtool archive`；
- `sed: //lib/libxxx.la: No such file or directory`（libtool 按 .la 的 dependency_libs
  绝对路径 sed）；
- `libtool: warning: library '.../libxxx.la' was moved`（.la 的 libdir 与实际位置不符）；
- 链接 libspeechd.la 时 glib 的 Requires 链把 pcre2/libffi 的 .la 拉进来触发。

典型实例：speech-dispatcher/0.12.1（CI #36976/#37284/#37446/#37458 反复失败）。

## Symptom

```text
libtool: warning: library '.../pcre2.../p/lib/libpcre2-8.la' was moved.
sed: //lib/libpcre2-8.la: No such file or directory
libtool:   error: '//lib/libpcre2-8.la' is not a valid libtool archive
make: *** [Makefile:530: libspeechd.la] Error 1
```

## Root Cause

1. libtool 链接 `.la`（libtool archive）时读其 `libdir=` 与 `dependency_libs=`；
2. 部分依赖包（如 pcre2/libffi）的 `.la` 在 OHOS 上构建时把 `libdir='//lib'`
   （prefix 为空）、`dependency_libs='... //lib/libpcre2-8.la ...'` 硬编码；
3. libtool 按 `dependency_libs` 里的**绝对路径** `//lib/libpcre2-8.la` 去 sed，
   OHOS 无该路径 → `is not a valid libtool archive`；
4. 与 `.pc` 的 libdir 硬编码同根因，但载体是 `.la`、解析方是 libtool、错误特征不同。

## Recommended Solution

**主方案：generate() 里复制改写依赖 .la 到 staging，并把 `-L staging` 注入 configure 的 LDFLAGS。**

```python
# conanfile.py
def _fix_dep_la(self):
    staging = os.path.join(self.build_folder, "ohos-la")
    os.makedirs(staging, exist_ok=True)
    # 复制所有依赖包 lib/*.la 到 staging，收集 basename -> 实际 lib 目录
    # 改写每个 .la：libdir='<实际 lib>'；dependency_libs 里 /lib、//lib 路径 → staging
    ...
    return staging

# generate()（configure 前）：
la_staging = self._fix_dep_la()
# 关键：-L staging 注入 configure 的 LDFLAGS（bake 进 Makefile，make 链接才能用到）
"LDFLAGS=-L%s -L/lib -L%s/ohos-shim -lohosshim" % (la_staging, self.build_folder)
```

⚠️ **关键教训**：不要只改 `build()` 里的 `os.environ["LDFLAGS"]`——make 用的 LDFLAGS 是
configure 时 bake 进 Makefile 的，os.environ 改动对已生成的 Makefile **无效**（CI #37458
实测：本地 os.environ 注入看似生效、CI 仍报 //lib/libxxx.la）。

**回退方案**：若 .la 改写不可行，patch 源码绕开带 .la 的依赖链（如只构建不依赖它们的
子目录）——改动面大，不推荐。

## 单库实证

| 库 | 角色 | 结果 |
|----|------|------|
| **speech-dispatcher/0.12.1** | 主验证（本 PR） | ✅ 覆盖前 libtool 报 `//lib/libpcre2-8.la is not a valid libtool archive`（CI 反复失败）；`_fix_dep_la()` + `-L staging` 注入 configure LDFLAGS 后 libspeechd.la 链接成功，conan create 通过 |

## 测试覆盖边界

- .la 改写只影响 **链接期 libtool 对依赖 archive 的解析**，不改库行为；
- 声明通过率时：以 conan create 全流程（libspeechd.so 链接 + test_package R34）为实证；
  speech-dispatcher 上游测试按 rule 1.2 平台限制声明（缺运行中的 daemon/D-Bus/声音设备）。
