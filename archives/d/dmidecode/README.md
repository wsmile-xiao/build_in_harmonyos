# dmidecode

dmidecode 是一个读取计算机 SMBIOS（DMI）数据的工具，可以显示硬件信息如 BIOS、处理器、内存等。

## 功能概述
- 读取并解析 SMBIOS/DMI 数据
- 显示 BIOS、系统、主板、处理器、内存等硬件信息
- 支持多种输出格式（quiet、dump、type 过滤、string 查询）
- 支持 `--from-dump` 离线分析 SMBIOS 二进制数据
- 无外部依赖

## OHOS 适配
- 纯 Makefile 项目，`make CC=clang -j1` 即可编译
- 无需任何补丁，原生兼容 HarmonyOS
- config.h 已包含 `__aarch64__` 支持 (USE_SLOW_MEMCPY)
- 在 aarch64 上仅编译 dmidecode（x86 专用的 biosdecode/ownership/vpddecode 不编译）
- **平台限制**: HarmonyOS 无 `/dev/mem` 和 sysfs DMI 表，直接读取硬件信息不可用
- **离线分析**: `--from-dump` 功能完全可用，SMBIOS 解析引擎正确

## 依赖关系
- **编译依赖**: 无
- **运行依赖**: musl libc (libc.so)

## 编译命令
```bash
make CC=clang -j1
```

## Conan 配方
```bash
conan create --user=ohpcd --channel=stable
```

## 测试
- 20 项功能测试全部通过
- Conan 验证 8 道门禁全部 PASS (G0-G4 + L2/L4/L5)

## 参考资料
- 官网: https://www.nongnu.org/dmidecode/
- 源码: https://download.savannah.gnu.org/releases/dmidecode/
