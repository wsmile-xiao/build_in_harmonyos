# lftp 4.9.3 — OpenHarmony 编译记录

## 基本信息
- 软件: lftp
- 版本: 4.9.3
- 构建系统: autotools
- 目标: ohos-aarch64

## 编译指导
- 依赖 readline/8.3、zlib/1.3.1（configure 硬要求）、openssl/3.5.6（TLS 支持），均为制品仓已发布版本
- 首次构建前需应用 patches/ 下 E007 平台三元组补丁（`apply_conandata_patches` 自动处理）
- 使用 `make -j1`（HMDFS 并行构建限制）
- 上游 `make check` 共 7 项测试，其中 4 项需公网，离线环境如实记录 gaps，不 veto 打包

## 补丁清单
- patches/0001-build-aux-config.guess.patch：增加 HarmonyOS 系统识别分支，输出 *-unknown-linux-ohos
- patches/0002-build-aux-config.sub.patch：增加 ohos-linux triplet、ohos OS 表项、linux-ohos kernel 校验表项

## 已知限制
- 默认 `--without-modules`：tests/module1 在 make check 中 SKIP（上游设计如此，exit 77）
- libidn2/expat 未引入：configure 自动降级（WARN 后继续），IDNA 与相关解析走内置实现
- gettext .gmo：真机若无 msgfmt 则翻译目录跳过编译，不影响英文主流程

## 功能验证
- `lftp --version` 报告 4.9.3
- `lftp -c 'help'` 列出可用命令
- test_package/test_lftp.sh 四项离线检查（版本串/help/queue-kill/lcd-lpwd）
