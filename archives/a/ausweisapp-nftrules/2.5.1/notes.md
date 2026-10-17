# ausweisapp-nftrules 2.5.1 适配笔记

## 编译环境
- **构建系统**: 无（纯数据包，单 nftables 规则文件）
- **编译日期**: 2026-09-01
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 关键事实
- **ausweisapp-nftrules 是 AusweisApp2（德国联邦身份证官方认证应用）的 nftables
  防火墙规则集**——放行 BundID AusweisApp2 通信端口 24727
- **上游 AusweisApp 源码 tarball 内不含此规则文件**——规则由 Alpine Linux
  aports 维护（community/ausweisapp/ausweisapp.nft）
- 本配方 conandata 直接指向 Alpine aports 的 raw 单文件 URL

## 编译步骤（conan create 全流程）

```bash
conan create archives/a/ausweisapp-nftrules/2.5.1 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
- 单文件下载：`download(self, url, filename="ausweisapp.nft", sha256=...)`
  ——注意是 `download()` 而非 `get()`（单文件非 tarball，get() 期望压缩包）

### 2. 打包（package()）
- 纯数据包——无编译
- `package()` 把 ausweisapp.nft 拷到 `etc/nftables.d/`
- package_type=application（数据/配置包形态）+ commands.json（R38）

## 语言预检（lang-preflight）
- 纯数据文件被检测为 `other`（无源码）——需 `OHPCD_LANG=other` 声明任务语言
  才能通过预检（默认 cpp 会拒）

## 上游测试（rule 4）
- 上游无测试套件（纯数据包，无编译、无测试）
- 适配后：test_package R34 真实内容校验——验证打包的
  etc/nftables.d/ausweisapp.nft 存在且内容含预期 nft 规则
  （table inet filter / tcp dport 24727 accept），1/1 = 100%

## 已知限制
- 规则文件由 Alpine aports 维护（非上游 AusweisApp 发行）——版本 2.5.1 与
  AusweisApp 2.5.1 对应，但规则内容变更跟随 aports，不跟随 AusweisApp 版本
---

**编译结束**: 2026-09-01 23:52
**最终状态**: built
