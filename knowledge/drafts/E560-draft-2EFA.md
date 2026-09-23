# E560（draft）— Meson install 原位改写 .dynstr 使内嵌 .codesign 哈希失效：安装后用 build-tree 原始产物覆盖

- **来源**: coeurl 0.3.2 HarmonyOS PC 适配
- **状态**: draft（待审，勿自行 promote）
- **关联**: gupnp 1.6.10 notes 同族教训（"meson install rewrites DT_RUNPATH → overwrite installed .so"）；E077（post-install-script）/E295（sign-elf 缺失）为签名/后处理邻域

## 1. 现象

coeurl 0.3.2 原生探索阶段：`meson install --destdir <dir>` 安装出的
`lib/libcoeurl.so.0.3` 无法被本机 musl 加载器加载：

```
$ LD_LIBRARY_PATH=<destdir>/lib ./tp-smoke
Error loading shared library libcoeurl.so.0.3: (needed by .../tp-smoke)
Error relocating .../tp-smoke: _ZN6coeurl6ClientC1Ev: symbol not found
```

同一 build 目录中的 `build-native/libcoeurl.so.0.3`（被上游测试直接链接
加载）加载正常。两个文件 sha256 不同：

```text
9106527a…df0cbe3178ab6  builds/coeurl-0.3.2.work/build-native-tls/libcoeurl.so.0.3   ← 可加载
46c71c50…3c3bc13c6cd5d  test-install/usr/local/lib/libcoeurl.so.0.3                 ← 加载失败
```

两个副本都仍有 `.codesign` section（`readelf -S | grep -c codesign` = 1）。

## 2. 根因

- hnp 工具链的 ELF 产物自带链接器签名（`.codesign` section，哈希覆盖整个
  文件映像）；
- `meson install --destdir` 在安装副本的 `.dynstr` 区内**原位改写**
  `DT_RUNPATH` 字符串字节（不整文件重写）→ 文件字节变化，而内嵌的
  `.codesign` 哈希未同步更新；
- 本机 musl 加载器加载时校验签名失败 → `Error loading shared library` /
  `Permission denied`（dlopen 与 NEEDED 两种加载路径同样失败）。
- 与 strip 破坏签名（gupnp/libsoup3 记录的 "never strip shared libraries"）
  是同族根因：任何对已签名 ELF 的原位字节改写都会失效签名。

## 3. 修法（保持原始产物字节，不重签）

Conan 配方 `package()` 中，`meson.install()` 之后用 build-tree 原始产物
覆盖安装副本（仅 shared 变体需要；static `.a` 无签名、可直接用）：

```python
def package(self):
    meson = Meson(self)
    meson.install()
    if self.options.shared:
        _lib = "libcoeurl.so.0.3"          # 带版本/soversion 的真实文件名
        _src = os.path.join(self.build_folder, _lib)
        _dst = os.path.join(self.package_folder, "lib", _lib)
        if os.path.exists(_src):
            shutil.copy2(_src, _dst)
```

gupnp 1.6.10 配方同款处理（`libgupnp-1.6.so.0.106.10`）。

### 禁止做法
- ❌ `binary-sign-tool sign -selfSign` 对 `.so` 重签——本机 musl 加载器
  SIGSEGV（workflow §5.3 实测），且掩盖真实的安装层字节破坏；
- ❌ 对安装副本 strip / 任何后处理字节改写——同样破坏签名。

## 4. 验证证据（coeurl 0.3.2 实测）

- 加载失败副本 sha256 = `46c71c50…`，build-tree 原始副本
  sha256 = `9106527a…`，均为 1038848 字节、同带 `.codesign`；
- 用 build-tree 副本覆盖后，测试消费者进程内加载成功并完成 13/13 断言
  （`COEURL_TEST_PACKAGE_OK`）；
- Conan 配方 `package()` 覆盖后 `conan create` 的 test_package 阶段
  消费者加载/运行通过（静态变体不受影响）。

## 5. 适用面与边界

- **适用**: 一切 meson 工程的 shared library 在 hnp clang（OHOS）下的
  `meson install` 产物；Conan 配方以 `meson.install()` 落包时必现；
  手工 `meson install --destdir` 部署同样命中。
- **不适用**: autotools/cmake 的 install（整文件复制，无原位 dynstr
  改写）；static 库；非 hnp 工具链产物。
- **识别方法**: 同一目标 build-tree 副本与安装副本 sha256 不同 +
  `.codesign` section 仍在 + 加载报 `Error loading shared library`
  （而非 `not found` 细节）三件套。
- ** loader 边界补充**: 本机 musl 加载器不读 DT_RUNPATH（本次实测：
  RUNPATH 存在仍按 `LD_LIBRARY_PATH` 解析），运行期依赖一律经环境
  `LD_LIBRARY_PATH` 解析；RUNPATH 失效不构成加载失败的独立根因。
