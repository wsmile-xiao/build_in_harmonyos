# libnfc 1.8.0 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-09-01
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

```bash
# 依赖注入：libusb-compat/0.1.7 提供 libusb 0.1 API（usb.h/libusb.pc）
export PKG_CONFIG_PATH="$HOME/tmp/libnfc-deps/pkgconfig:..."
export CPPFLAGS="-I.../libusb-compat/include -I.../libusb-1.0/include/libusb-1.0"
export LDFLAGS="-L.../libusb-compat/lib -L.../libusb-1.0/lib"

./configure --prefix=$DEFAULT_PREFIX --disable-doc --disable-log
make -j1
make check   # 上游测试依赖 Cutter + 物理 NFC 设备，均缺失 → 0 用例可执行
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `cannot guess build type` | config.guess(2018) 不识别 HarmonyOS | 补 config.guess/config.sub HarmonyOS 三元组（patch 0001/0002） |
| 2 | `can't create ./confXXXXXX/subs1.awk: Permission denied` | configure 临时目录 umask 077，HMDFS 组无写权限（E011） | configure 内 umask 077→022（patch 0003） |
| 3 | configure 找不到 libusb | libnfc usbbus 用 libusb 0.1 API（usb.h），本机无系统 libusb | 依赖 libusb-compat/0.1.7（0.1 兼容层，内部链 libusb-1.0） |
| 4 | 链接 `undefined symbol: libusb_exit` | libusb-compat 静态链需要 libusb-1.0；pkg-config Requires.private 不展开 | 配方 generate() 注入 LIBS/LD_LIBRARY_PATH 含传递依赖 |

## 源码修改

- `patches/0001-config.guess.patch`: 增加 `*:HarmonyOS:*:*` 分支，输出 `aarch64-unknown-linux-ohos`
- `patches/0002-config.sub.patch`: 增加 `linux-ohos` 三元组识别（maybe_os/basic_machine/OS 列表/内核列表）
- `patches/0003-configure.patch`: 临时目录 `umask 077`→`umask 022`（HMDFS E011）

## 依赖版本

- libusb-compat/0.1.7（依赖 libusb/1.0.27，均已在 ohpcd 制品仓发布）

## 验证结果

```bash
# HarmonyOS 专项测试（无设备场景，真实调用 nfc_version/nfc_init/nfc_exit/nfc_list_devices）
harmonyos_smoke: ALL CHECKS PASSED   # exit 0，日志 sha256 已记录

# conan create（G2）→ 通过；W3 本地 CI → Success 1/1
```

## 注意事项

- 上游测试（Cutter，6 个独立用例）需物理 NFC 读卡器，当前环境无设备 + 无 Cutter，全量通过率 0/6，如实记录。
- USB 读卡器真实数据通路（nfc_open→initiator→discover）需带设备人工复核（R40 外设类）。
---

**编译结束**: 2026-09-01 20:32
**最终状态**: built
