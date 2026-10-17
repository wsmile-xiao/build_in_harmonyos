# libyubikey

C library for manipulating Yubico one-time passwords.

## 基本信息

| 属性       | 值                                                  |
|------------|-----------------------------------------------------|
| 名称       | libyubikey                                          |
| 描述       | C library for manipulating Yubico one-time passwords |
| 许可证     | BSD-2-Clause                                        |
| 语言       | C                                                   |
| 构建系统   | autotools                                           |
| 主页       | https://developers.yubico.com/yubico-c/             |

## 核心功能

- **YubiKey OTP 编码/解码**: modhex 和 hex 格式转换
- **AES 加密/解密**: YubiKey 令牌的 AES 处理
- **OTP 生成与解析**: `yubikey_generate()` 和 `yubikey_parse()` API
- **CRC16 校验**: `yubikey_crc16()` 校验算法

## 库类型

仅提供静态库 (`libyubikey.a`)，包含目标文件：
- yktoken.o: OTP 令牌结构体操作
- ykhex.o: hex/modhex 编解码
- ykcrc.o: CRC16 校验
- ykaes.o: AES 加解密

## 命令行工具

| 工具         | 功能                          |
|--------------|-------------------------------|
| modhex       | modhex 编码/解码转换          |
| ykparse      | 解析 YubiKey OTP 令牌         |
| ykgenerate   | 生成 YubiKey OTP 令牌         |

## 已编译版本

| 版本 | 状态      | 编译日期   | 补丁数 | 备注 |
|------|-----------|------------|--------|------|
| 1.13 | built     | 2026-06-06 | 2      | 2026-06 真机 ohc-run 构建 published；2026-09 补齐 Conan 配方与 test_package |

## 平台适配要点

1. 需替换 config.guess/config.sub (E007) 为 2023+ 版本以识别 `aarch64-unknown-linux-ohos`（已固化为 patches/0001、0002）
2. 需使用 GNU ld 替代 SDK lld（lld 依赖 libxml2.so.16）
3. 需 ELF 签名 wrapper（未签名二进制无法执行）
4. 需 mktemp wrapper（HMDFS umask 077 目录权限问题）

> 要点 2-4 是 2026-06 ohc-run 手工真机构建时的环境 workaround；Conan CI runner 环境通常已内置等效处理，若 shadow CI 复现同类报错再对照 `notes.md` 的历史经验表排查。