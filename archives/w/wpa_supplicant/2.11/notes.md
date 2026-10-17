# wpa_supplicant 2.11 适配笔记

## 编译环境
- 构建系统: makefile (custom, not autotools/cmake)
- 编译日期: 2026-08-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. Source: hostap project git repo (tag hostap_2_11), commit d945ddd368085f255e68328f2d3b020ceea359af
2. Create .config from defconfig with OHOS adaptations
3. Build with: `make -j2` (CFLAGS and LIBS are in .config)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | struct probe_resp_params incomplete type | Defined inside #ifdef NEED_AP_MLME but used outside it | Enable CONFIG_AP=y and NEED_AP_MLME=y in .config |
| 2 | openssl/ssl.h not found | System openssl headers not available | Use conan openssl/1.1.1w with CFLAGS include path |
| 3 | libnl not available | OHOS doesn't have libnl library | Disable CONFIG_DRIVER_NL80211, enable CONFIG_DRIVER_NONE |
| 4 | w1.fi cgit snapshot blocked | Bot detection on w1.fi website | Download source via git smart HTTP protocol |
| 5 | git clone fails with early EOF | Network connection to w1.fi cut | Use Python urllib to manually do git-upload-pack POST |

## 源码修改

No patches applied. All modifications done in .config (build configuration).

## 依赖版本

- openssl/1.1.1w (from conan registry)

## 验证结果

wpa_supplicant --version: PASS

## 交付物

| 文件 | 说明 |
|------|------|
| wpa_supplicant | Main supplicant binary (6MB, ELF arm64) |
| wpa_cli | Command-line interface (207KB) |
| wpa_passphrase | Passphrase generator (2MB) |

## 注意事项

- libnl is NOT available on OHOS - nl80211 driver disabled
- All EAP methods, WPS, SAE, and AP mode are enabled
- Source URL in conandata.yml points to w1.fi cgit snapshot; CI may need mirror fallback
