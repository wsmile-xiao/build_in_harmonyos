# libdisplay-info-tools 0.3.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-17
- 编译器: clang 15.0.4
- 依赖: 无（静态链接，产物只依赖 libc/libm）
- 状态: built

## 本包与库包的分工

| 归档 | 交付物 |
|------|--------|
| archives/l/libdisplay-info/0.3.0 | libdisplay-info.a/.so、头文件、libdisplay-info.pc |
| archives/l/libdisplay-info-tools/0.3.0 | bin/di-edid-decode（静态，自包含） |

构建期把整图都编出来（上游没有 CLI 开关，见下），`package()` 里删掉
`include/ lib/ share/`，保证同一个文件只有一个属主。

## 编译步骤

1. `source()`: `get()` 下载 `libdisplay-info-0.3.0.tar.gz`
   （sha256 `2b467e3336aec63819d6aca28d7310d3dc7415b2b3a3c3a5aec9d3727053c078`，
   与库包同一份），打补丁 0001/0002/0003，再把随配方携带的 `data/pnp.ids`
   落到源码树
2. `meson setup -Ddefault_library=static -Dwrap_mode=nodownload`
3. `ninja`
4. `meson install` 后裁剪安装树，ELF 自签名

## 遇到的问题与解决方案

| # | 问题 | 根因 | 处理 |
|---|------|------|------|
| 1 | 没有可用的"只出 CLI"开关 | 0.3.0 根本没有 `meson_options.txt`，根 `meson.build` 无条件 `subdir('di-edid-decode')` 与 `subdir('test')` | 不依赖开关，整图构建后在 `package()` 里裁剪 |
| 2 | `--version` / `--help` 都拿不到 0 退出码 | 上游 `getopt_long` 短选项串只有 `"h"`，`-h` 与未知选项两条路径都 `return -1`（退出码 255） | 补丁 0001 增加 `-V/--version`（版本号由 `meson.project_version()` 编译期内联），并让 `--help` 以 0 退出 |
| 3 | `meson setup` 报 `File /usr/share/hwdata/pnp.ids does not exist` | hwdata 是纯数据包、没有 conan 配方，设备上也没有它的 pkg-config 文件，上游 `dependency('hwdata')` 必然 not found，于是回退到写死的 `/usr/share/hwdata/pnp.ids` | 补丁 0002 把回退路径改成随配方携带的 `data/pnp.ids` |
| 4 | `tool/gen-search-table.py` 抛 `ValueError: not enough values to unpack (expected 2, got 1)` | hwdata 的 `pnp.ids` 里有只有 ID 没有厂商名的行（如单行的 `MV`），上游无条件 `line.split(maxsplit=1)` 后解包 | 补丁 0003 改成与"非法 PNP ID"同样地跳过并告警 |
| 5 | 数据文件不能在 `build()` 里联网下载 | `raw.githubusercontent.com` 不可达时 `curl` 一直等到 60s 超时，整条 `conan create` 拖到任务超时 | 改为 `export_sources()` 携带 `data/pnp.ids`，`source()` 落进源码树，全程离线 |
| 6 | 新二进制无法执行 | 鸿蒙要求 ELF 带 `.codesign` | `package()` 内调用 `llvm-objcopy` + `binary-sign-tool` 自签名 |

## 源码修改

| 补丁 | 修改内容 |
|------|----------|
| `0001-cli-version-flag.patch` | `di-edid-decode` 增加 `-V/--version`，并让 `-h/--help` 以 0 退出 |
| `0002-meson-hwdata-ids.patch` | `meson.build` 的 pnp.ids 回退路径：`/usr/share/hwdata/pnp.ids` → `data/pnp.ids` |
| `0003-gen-search-table-malformed-lines.patch` | `tool/gen-search-table.py` 跳过无厂商名的行而不是崩溃 |

## 验证结果

```bash
ohc-run.py conan-verify libdisplay-info-tools 0.3.0   # G0-G4 / L2 / L4 / L5 全绿
```

`test_package/test.sh`（由 `test_package/conanfile.py` 的 `test()` 调起）的断言：

```
[test] di-edid-decode --version
        [ok] di-edid-decode 0.3.0
[test] di-edid-decode --help
        [ok] --help exit status 0
[test] fixture ready: acer-p1276.edid (256 bytes)
[test] di-edid-decode acer-p1276.edid
        [ok] decoded 72 lines, conformity PASS
[test] di-edid-decode <empty input> (expected failure)
        [ok] empty input rejected
All tests passed.
```

## 注意事项

- `meson.install()` 会把静态库、头文件、pkg-config 一并铺进 `package_folder`，
  拆分包必须靠 `package()` 里的 `rmdir` 兜底，不能只依赖 `install` 参数。
- `generate()` 里向 `conan_meson_native.ini` 注入 `ar`/`ranlib` 绝对路径
  （`llvm-ar` / `llvm-ranlib`）是防御性动作：profile 只声明了 `c`/`cpp`，
  conan 生成的 ini 不一定带归档器条目；缺失时静态库归档会走 meson 的兜底查找。
- `EDID conformity: PASS` 是上游对夹具的判定结果，夹具 `acer-p1276.edid`
  以 base64 形式随 `test_package/data/` 携带（R02：PR diff 不能带二进制）。
