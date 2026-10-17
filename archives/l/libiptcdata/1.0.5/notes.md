# libiptcdata 1.0.5 — 适配笔记

## 上游调查

- **项目**：libiptcdata — 纯 C 库，解析/修改/保存 IPTC 元数据（JPEG 等）
- **上游**：https://github.com/ianw/libiptcdata  (tag `release_1_0_5`)
- **License**：LGPL-2.0-or-later（COPYING = GNU Library GPL v2）
- **源码包**：libiptcdata-1.0.5.tar.gz，593779 字节
  - SHA256：`c094d0df4595520f194f6f47b13c7652b7ecd67284ac27ab5f219bc3985ea29e`
  - MD5：`c04bc1375c280d41c0106255d1df711a`
  - （与 Gentoo distfiles manifest 一致；Debian orig.tar.gz 586983 字节为重压缩产物，哈希不同，不用）

## 构建系统

- Autotools；release tarball 自带预生成 `configure`（+ Makefile.in / aclocal.m4 / ltmain.sh / config.guess / config.sub）。
- **不需要 autoreconf**：只用 `./configure && make && make install`。

## 依赖

- 核心 libiptcdata C 库：**无运行时依赖**。
  - `i18n.h` 在 `ENABLE_NLS` 未定义时把 `gettext`/`dgettext` 宏化为恒等映射，不需 libintl。
  - `libiptcdata/Makefile.am` 的 `libiptcdata.la` 不 link `-lintl`/`-liconv`。
- 可选组件（本配方全部禁用，只留核心库）：
  - Python bindings（`--disable-python`）
  - gtk-doc 参考手册（`--disable-gtk-doc`）
  - NLS（`--disable-nls`）
  - `iptc` 命令行工具随核心库一起构建，但 test_package 只验证库 API。

## 上游测试体系

- **上游无 `make check` / 无 tests/ 目录 / 无 check_PROGRAMS**。
  - Makefile.am 各级均无 `TESTS`/`check_*` 目标；`grep -rn "int main" *.c` 仅命中 `iptc/main.c`（CLI 工具，非测试）。
  - 故 `upstream_test_in_build: false`，测试完全由 test_package 覆盖。

## OHOS 适配要点

1. **config.sub 识别**：自带 config.guess/sub 为 2018-02-24 版，不识别 `*-linux-ohos`
   （`config.sub aarch64-linux-ohos` → "system `ohos' not recognized"）。
   采用与 libconfini/1.16.4、libdatrie/0.2.13 相同做法：传
   `--build=aarch64-unknown-linux-musl --host=aarch64-unknown-linux-musl`，
   因 configure 不做任何 OHOS 专属探测，musl triplet 被接受且产物一致。
   **实际编译器仍为 aarch64-unknown-linux-ohos clang + OHOS sysroot，非普通 musl。**

2. **umask 077 → 022（上游构建脚本修改）**：configure 的 config.status 用
   `(umask 077 && mktemp -d "./confXXXXXX")` 建私有临时目录，写入 subs1.awk，
   然后由 config.status 子 shell 读回。在 OHOS PC HMDFS 文件系统上，umask 077
   导致 subs1.awk 对子 shell 不可读：
   ```
   ./config.status: line 837: ./confXXXX/subs1.awk: Permission denied
   config.status: error: could not setup config files machinery
   ```
   尝试了五种非源码修改方案，全部失败：
   - os.umask(0o022) — 子 shell 重新设置 077
   - shell `umask 022` — 子 shell 重新设置 077
   - TMPDIR + chmod 0777 — HMDFS 忽略 chmod
   - CONFIG_SHELL wrapper (export -f umask) — RC=126 exec 失败
   - BASH_ENV umask() 函数覆盖 — config.status 不 source BASH_ENV
   唯一可行的方案是将 configure 脚本中的 `umask 077` 改为 `umask 022`。
   **这是对上游构建脚本（configure）的最小 OHOS 兼容性修改，在 build() 内以
   原地文本替换实现（非独立 .patch 文件）。这不是"零源码修改"——上游 configure
   确实被修改了，已如实披露。**

3. **libtool .la 清理**：install 后删 `lib/*.la`（其内嵌绝对 libdir `/lib` 误导下游）。

## test_package 设计

真实功能往返断言（非编译冒烟）：
1. `iptc_data_new` + `iptc_dataset_new` 构造；
2. `iptc_dataset_set_tag(APP_2, OBJECT_NAME)` + `set_data(..., IPTC_VALIDATE)` 写入字符串值；
3. `iptc_data_add_dataset` 入集合；
4. `iptc_data_get_dataset` 按记录+标签取回；
5. `iptc_data_save` 序列化为字节流；
6. `iptc_data_new_from_data` 反序列化并校验往返值一致；
7. `iptc_dataset_get_data` 取原始字节校验长度/内容。

共 7 处断言（①-⑦）；交叉编译时只验编译+链接（`cross_building` 分支）。

## 验证命令

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
zsh ci/conan/build_and_test.sh archives/l/libiptcdata/1.0.5
```
