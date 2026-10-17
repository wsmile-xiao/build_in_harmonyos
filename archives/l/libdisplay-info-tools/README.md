# libdisplay-info-tools

`di-edid-decode` —— libdisplay-info 自带的 EDID/DisplayID 解码命令行工具。

## Description
把显示器 EDID/DisplayID 二进制块解码成人类可读的报告（厂商、型号、时序、
色度、HDR 静态元数据、CTA-861 扩展块等），并给出 `EDID conformity:PASS/FAIL`
一致性结论。上游把它和解析库放在同一个 meson 工程里，本归档只出命令行工具。

## Project URL
https://gitlab.freedesktop.org/emersion/libdisplay-info

## License
MIT

## HarmonyOS 适配说明

### 构建信息
- **版本**: 0.3.0（与库包 `libdisplay-info/0.3.0` 同源同版本）
- **构建系统**: meson
- **编译器**: clang 15.0.4
- **链接方式**: `-Ddefault_library=static`，工具自包含，不依赖 `libdisplay-info.so`

### 与库包的分工
`archives/l/libdisplay-info/0.3.0` 负责 `libdisplay-info.a/.so`、头文件与
`libdisplay-info.pc`；本包只负责 `bin/di-edid-decode`。配方在 `package()`
里删掉 `include/ lib/ share/`，保证同一个文件只有一个属主。

### 平台限制与补丁
| 问题 | 根因 | 处理 |
|------|------|------|
| `meson setup -Dtools=...` 无效 | 0.3.0 根本没有 `meson_options.txt`，根 `meson.build` 无条件 `subdir('di-edid-decode')` / `subdir('test')` | 不依赖开关，整图构建后在 `package()` 裁剪安装树 |
| `--version` / `--help` 无法返回 0 | 上游 `getopt_long` 短选项串只有 `"h"`，`-h` 与未知选项两条路径都 `return -1` | 补丁 `0001-cli-version-flag.patch` 增加 `-V/--version`（版本号取自 `meson.project_version()`），并让 `--help` 以 0 退出 |
| 构建期缺 `hwdata` 的 `pnp.ids` | hwdata 是纯数据包、没有 conan 配方，设备上也没有它的 pkg-config 文件，上游 `dependency('hwdata')` 必然 not found，于是回退到写死的 `/usr/share/hwdata/pnp.ids`（OHOS 上不存在），`meson setup` 直接报 `File /usr/share/hwdata/pnp.ids does not exist` | 补丁 `0002-meson-hwdata-ids.patch` 把回退路径改成本配方携带的 `data/pnp.ids`（`export_sources()` 导出，`source()` 落进源码树），全程不需要联网 |
| `pnp.ids` 里有只有 ID 没有名称的行 | hwdata 的 `pnp.ids` 含单行 `MV` 这类条目，`tool/gen-search-table.py` 无条件 `[pnpid, name] = line.split(maxsplit=1)` 直接抛 `ValueError: not enough values to unpack (expected 2, got 1)`，custom_target 失败、构建中断 | 补丁 `0003-gen-search-table-malformed-lines.patch` 改成与"非法 PNP ID"同样地跳过并告警 |
| 新二进制无法执行 | 鸿蒙安全机制要求 ELF 带 `.codesign` | `package()` 内调用 `llvm-objcopy` + `binary-sign-tool` 自签名 |

### 使用方式
```bash
di-edid-decode /sys/class/drm/card0-DP-2/edid    # 解码指定 EDID 文件
di-edid-decode < edid.bin                        # 从 stdin 读取
di-edid-decode --version                         # 打印版本
```

### 验证结果
- `ohc-run.py conan-verify libdisplay-info-tools 0.3.0`: G0-G4 / L2 / L4 / L5 全绿
- `test_package/test.sh`: 5 项断言（`--version`、`--help` 退出码、官方 EDID 夹具解码、CTA 扩展块解析、空输入反例）