# ca-certificates 20250419 适配笔记

## 编译环境
- 构建系统: custom（纯数据包，无编译）
- 编译日期: 2026-08-06
- 编译器: N/A
- 状态: built

## 编译步骤

ca-certificates 是纯数据包，不需要传统编译。主要工作是运行 certdata2pem.py 将 Mozilla certdata.txt 转换为 PEM 格式证书文件。

```bash
cd mozilla/
python3 certdata2pem.py
# 生成 150 个 .crt 证书文件
```

安装步骤：
1. 复制 150 个 Mozilla CA 证书到 `share/ca-certificates/mozilla/`
2. 复制 update-ca-certificates 工具到 `sbin/`
3. 复制 man page 到 `share/man/man8/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | certdata2pem.py 无法导入 cryptography | Rust .so 无法在 HarmonyOS 上加载（ELF 签名要求） | 创建补丁 0001-ohos-optional-cryptography.patch，使 cryptography 导入可选 |

## 补丁说明

### 0001-ohos-optional-cryptography.patch
- 将 `from cryptography import x509` 改为 try/except 可选导入
- 将证书过期检查包裹在 `if HAS_CRYPTOGRAPHY:` 条件中
- **不裁剪任何功能**：所有 150 个证书仍然生成
- cryptography 仅用于非致命的过期警告，不影响证书生成
- 证书 PEM 编码使用 base64.b64encode()，不依赖 cryptography

## 依赖版本
无编译依赖

## 验证结果
- 150 个 CA 证书文件生成
- 证书格式为标准 PEM
- update-ca-certificates 工具可用
---

**编译结束**: 2026-08-06 03:01
**最终状态**: built
