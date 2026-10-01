# libfreefare 0.4.0 — 已发布 autotools 依赖 .la 残留第三方库旧 prefix 绝对路径，及链接顺序修法（draft）

**Category**: build-system | libtool | linking | ohos · **Severity**: 3 · **Tool**: configure/make/libtool/conan

## 症状

在 OHOS aarch64 上用 autotools/libtool 构建 `libfreefare/0.4.0`，链接期连续两报：

1. 链接 `libfreefare.la` 本体：
   ```
   libtool: link: ... /usr/local/lib/libusb-1.0.la is not a valid libtool archive
   ```
2. 链接 examples/ 下 13 个 `mifare-*` 可执行：
   ```
   undefined symbol: libusb_set_interface_alt_setting,
                     libusb_clear_halt, libusb_reset_device ...
   ```

## 根因

- 本包依赖 `libnfc/1.8.0`（ohpcd 已发布的 autotools 二进制包）。该包在自身构建时 `prefix=/usr/local`，
  其 `lib/libnfc.la` 的 `dependency_libs=` 行硬编码了当时的绝对路径
  `/usr/local/lib/libusb-1.0.la`（这是 libusb-compat 依赖 libusb-1.0 的 libtool 串联记录）。
- 消费方 libfreefare 在 OHOS 真机上构建，`/usr/local/lib/libusb-1.0.la` 这个绝对路径根本不存在
  （OHOS 上 libusb-1.0 实包在 conan cache 的 hash 目录里），libtool 按 dependency_libs 逐路径 sed，
  命中不存在的 `.la` 就报 `is not a valid libtool archive`。
- 与既有 `DRAFT-ohos-la-libdir-hardcode`（speech-dispatcher 案例）同族但**路径形态不同**：
  那条是 `libdir='//lib'`（prefix 为空）、dependency_libs 指向 `//lib/libpcre2-8.la`；本条是
  已发布包在 `/usr/local` 前缀下构建、把**第三方库**（libusb-1.0）的旧绝对路径写进了**本包**
  （libnfc）的 dependency_libs——消费方删自己 .la 没用，必须动依赖包的 .la。
- 第二个报错是链接顺序：libusb-compat（0.1 兼容层）的符号引用 libusb-1.0，但默认 LIBS 里
  只有 `-lusb` 没有 `-lusb-1.0`，且 -lusb-1.0 必须排在 -lusb 之后才能解析符号。
  AutotoolsToolchain 不会自动把所有依赖的 `-l` 拼到 LIBS 末尾。

## 处置（可复用）

1. **删掉依赖 .la 里指向不存在位置的绝对 .la 引用**（不是复制改写到 staging，更轻）：
   ```python
   # build() 里，configure 之前
   nfc_la = os.path.join(self.dependencies["libnfc"].package_folder, "lib", "libnfc.la")
   self.run("sed 's# /usr/local/lib/libusb-1.0.la##g' '%s' > _nfc.la.new && "
            "cat _nfc.la.new > '%s' && rm _nfc.la.new" % (nfc_la, nfc_la))
   ```
   保留 dependency_libs 里的 `-L<实际 libusb 目录> -lusb`，libtool 仍能从实际位置找到库；
   只删那个 HMDFS 上不存在的绝对 `.la` 串联引用。
2. **把所有依赖的 `-l` 注入 LIBS 末尾**（generate()，不是 build()——要在 configure 前 bake 进 Makefile）：
   ```python
   for dep in self.dependencies.values():
       for lib in dep.cpp_info.libs:
           env.append("LIBS", "-l" + lib)
   env.append("LIBS", "-lcrypto")   # openssl 未被 PKG_CHECK_MODULES 引用，显式补
   ```
   这样 libusb-compat → libusb-1.0 → libcrypto 的符号解析顺序正确。
3. 与本问题无关但同批命中的 HMDFS/老 autotools 项（已在 notes.md 踩坑表）：
   `sh ../configure`（HMDFS 无执行位）、`--build/--host=aarch64-unknown-linux-gnu`（config.guess 不识 OHOS）、
   `sed 's/umask 077/umask 022/g' configure`（E011）、PATH 注入 binutils_2.45/bin。

## 验证

`conan create`（ohos-aarch64-fixed, clang 15）rc=0；libfreefare.la 链接成功、
13 个 `bin/mifare-*` 全部链接通过；test_package `1/1 Passed`（11 条无硬件纯计算断言）。

## 与既有条目的边界

- `DRAFT-ohos-la-libdir-hardcode`：`.la` 的 `libdir` 字段 + dependency_libs 指向 `//lib`，
  修法是复制改写到 staging + `-L staging` 注入 configure LDFLAGS。本条是 dependency_libs 里**单个**
  第三方 .la 绝对路径失效，且该库本身仍可通过 `-L`+`-l` 正常找到，直接 sed 删除即可，
  无需 staging。两者互补：先判断失效引用能否由 `-L`+`-l` 兜底，能就 sed 删，不能再走 staging。
