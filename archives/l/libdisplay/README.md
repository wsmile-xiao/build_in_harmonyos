# libdisplay

EDID and DisplayID library for parsing display metadata.

## Description
libdisplay is a C library (upstream: libdisplay-info) providing tools to parse EDID (Extended Display Identification Data) and DisplayID metadata from displays. It is primarily used by Wayland compositors and other display management software.

## Project URL
https://gitlab.freedesktop.org/emersion/libdisplay-info

## License
MIT

## HarmonyOS 适配说明

### 构建信息
- **版本**: 0.3.0
- **构建系统**: meson
- **编译器**: clang 15.0.4
- **状态**: published (2026-06-02)

### 依赖
- hwdata 0.366 (pnp.ids 纯数据包, 需设置 PKG_CONFIG_PATH 包含 `~/usr/local/share/pkgconfig`)

### 平台限制
| 限制 | 影响 | 解决方案 |
|------|------|----------|
| /tmp 只读 | meson test 脚本 mktemp 失败 | TMPDIR=$HOME/tmp |
| ELF 签名 | 新安装二进制需签名 | ohc-run.py sign-elf |
| SIGTRAP (exit 133) | di-edid-decode 部分文件返回 133 | 输出内容正确,不影响功能 |

### 验证结果
- 质量门禁 G0-G4: ✅ PASS (G0 手动验证)
- di-edid-decode: ✅ 所有 32 个 EDID 文件解码输出正确
- C API: ✅ di_info_parse_edid/get_edid/destroy 验证通过
- pkg-config: ✅ modversion=0.3.0, libs/cflags 正确

### 使用方式
```bash
# 安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libdisplay 0.3.0

# 或手动设置环境
export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig:~/usr/local/share/pkgconfig
export LD_LIBRARY_PATH=~/usr/local/lib

# 编译链接
cc your_program.c $(pkg-config --libs --cflags libdisplay-info) -o your_program

# 解码 EDID
di-edid-decode /path/to/edid.bin
```

### 注意事项
- hwdata 是纯数据包,需先安装 pnp.ids 到 `~/usr/local/share/hwdata/`
- 此软件无源码修改,0 补丁,编译参数仅 `--prefix=$DEFAULT_PREFIX -Dc_std=c11`