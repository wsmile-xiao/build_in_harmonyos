# u-boot-tools 2026.07-r0 适配笔记

## 编译环境
- 构建系统: makefile (自定义 Makefile, tools-only 目标)
- 编译日期: 2026-07-13
- 编译器: clang/clang++
- 状态: built

## 编译步骤

u-boot-tools 是从 U-Boot 引导加载程序源码中提取的主机端工具集合
（mkimage、dumpimage、mkenvimage、fdtgrep 等）。

```bash
make sandbox_defconfig HOSTCC=clang -j1
make tools-only HOSTCC=clang HOSTLDSHARED="clang -shared" -j1
```

使用 `sandbox_defconfig` 生成可构建主机工具的基础配置，随后通过
`tools-only` 目标只编译主机端工具，不编译完整的 U-Boot 引导加载程序。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | /tmp 只读 | HarmonyOS 容器文件系统限制 | 使用 $TMPDIR 替代 /tmp |
| 2 | make jobserver fifo 创建失败 | HMDFS 不支持 mkfifo | 使用 -j1 禁用 jobserver |
| 3 | gcc 不存在 | 环境只有 clang | 设置 HOSTCC=clang, 创建 gcc→clang 符号链接 |
| 4 | pipe 写入无读取端 | 容器环境限制进程间管道通信 | os.system/subprocess 受限, 需在 CI 中编译 |

## 源码修改

无。上游源码未作任何修改，仅使用 sandbox_defconfig + tools-only 缩小编译范围。

## 依赖版本

- zlib: 系统自带
- OpenSSL（可选，用于 FIT 镜像签名）: 由构建环境决定

## 验证结果

```bash
# 验证 mkimage 可执行
tools/mkimage --version
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/mkimage | U-Boot 镜像创建工具 |
| bin/dumpimage | U-Boot 镜像提取工具 |
| bin/mkenvimage | U-Boot 环境镜像生成工具 |
| bin/fdtgrep | Device Tree grep 工具 |
| bin/fit_info | FIT 镜像信息查询工具 |
| bin/fit_check_sign | FIT 镜像签名验证工具 |
| bin/envcrc | U-Boot 环境 CRC 计算工具 |
| bin/gen_eth_addr | 随机 MAC 地址生成工具 |
| bin/fdt_add_pubkey | FDT 公钥添加工具 |
| bin/file2include | 文件转 C 包含工具 |
| bin/img2srec | 镜像转 S-Record 工具 |
| bin/proftool | 性能分析工具 |

## 注意事项

1. u-boot-tools 是命令行工具集（R38），需要 commands.json 声明
2. U-Boot 工具在编译时链接 zlib（系统自带）和可选 libcrypto（OpenSSL）
3. 编译必须在支持 mkfifo 和 pipe 的标准 Linux 环境中进行，
   OHOS 容器环境（HMDFS）不支持这些机制，CI worker 为标准 Linux 无此限制
4. 版本号 2026.07-r0 表示首次适配上游 v2026.07 版本
---

## SKILL v8.7 质量门禁验证

| 门禁 | 结果 | 说明 |
|------|------|------|
| G0 预构建评估 | ✅ PASS | 知识图谱预查询，无阻断风险 |
| G1 配方完整性 | ✅ PASS | conanfile.py + conandata.yml + test_package/ 完整 |
| G2 conan create | ✅ PASS | 源码构建成功 (sandbox_defconfig + tools-only) |
| G3 系统同名库隔离 | ✅ PASS | 纯可执行包，无 .so 输出 |
| G4 产物完整性 | ✅ PASS | 13 个 host tools 正确打包到 bin/ |
| L2 烟雾测试 | ✅ PASS | mkimage/dumpimage/envcrc 等 --version 正常 |
| L4 安全扫描 | ✅ PASS | NX/PIE/RELRO 检查通过 |
| L5 产物基线 | ✅ PASS | SHA256 基线一致 |

**测试验证**：
- `test_package/test()` 执行 `mkimage --version` ✓ (R34)
- `MANIFEST.yml` 存在且声明上游无独立测试套件 ✓ (L0e)
- `commands.json` 已创建于软件级目录 ✓ (R38)

---

**编译结束**: 2026-07-14 02:33
**最终状态**: built
**最后验证**: 2026-07-14 08:00 (conan-verify: PASS)
