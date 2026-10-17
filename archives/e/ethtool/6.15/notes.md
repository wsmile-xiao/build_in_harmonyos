# ethtool 6.15 — 适配笔记

> 档案创建时间: 2026-08-06
> 最后更新: 2026-09-20
> 状态: built（conan-verify G2 通过；PR CI 校验通过）

---

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | ethtool |
| 版本 | 6.15 |
| 描述 | Utility for examining and tuning network interface parameters |
| 构建系统 | autotools |
| 语言 | C |
| 许可证 | GPL-2.0 |
| 依赖 | libmnl/1.0.5 (netlink 接口) |

---

## 二、编译阶段记录

### Phase 1: 环境准备
- ✅ ohc-run.py init-build 完成（从 kernel.org 下载 tarball）
- ✅ 源码解压到 ~/tmp/builds/ethtool-6.15.work

### Phase 2: 编译
- ✅ configure 完成（参数: `--prefix=$DEFAULT_PREFIX`）
  - 平台识别: 通过 config.guess/sub 补丁
  - 编译器: clang 15.0.4
  - libmnl: ✅ 通过 pkg-config 检测到
  - netlink: ✅ 默认启用
- ✅ make -j2 编译完成，1 个 warning (GNU variable-sized type, 非致命)
- ✅ make install DESTDIR=$TEST_PREFIX 完成（staging 验证通过）

### Phase 3: 测试验证
- ⚠️ make check: test-cmdline 3 cases fail (环境问题: 无网络设备)
- ✅ ethtool --version: version 6.15
- ✅ conan create G2: PASS (ethtool --version test passed)

### Phase 4: 重试验证 (2026-09-20, attempt 3)
- ✅ libmnl/1.0.5 已发布到 ohpcd 制品仓（conan download --only-recipe 验证通过）
- ✅ 本地 conan create 复验通过（ohos-aarch64 profile，test_package: ethtool --version → 6.15）
- ✅ 远程 CI 校验通过（2026-09-18 build #50462: L0/L1 门禁 + test_package 全绿）
- ✅ AI 检视意见 2×P2 + 2×P3 已全部闭环（test-report.md 删除、补丁生成方式表述修正、软件级 manifest.yaml 补齐）
- ⚠️ 2026-09-20 CI 重触发观察：build #53687 因 worker git-clone 网络抖动中断（与 2026-09-04 #38433 同类基础设施瞬时故障，非配方问题）；当日 CI 调度队列拥堵（>2h 延迟），重触发后以本 notes 提交刷新 sourcestamp

---

## 三、遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HMDFS mktemp 权限 | umask 077 && mkdir 在 HMDFS 上创建 drwx--S--- 目录 | 修改 configure: 使用 $TMPDIR + chmod 755 |
| 2 | E119 sockaddr_storage | OHOS SDK linux/socket.h 与 sys/socket.h 冲突 | 通过 libmnl 依赖的 patch 0004 传递解决 |

---

## 四、源码修改清单

| 文件 | 原因 | 方式 | 补丁 |
|------|------|------|------|
| configure | HMDFS mktemp 权限修复 | refresh-patch --auto 生成 | 0001-configure.patch |

---

## 五、依赖说明

- libmnl/1.0.5: ethtool 的 netlink 接口默认启用，需要 libmnl
- libmnl/1.0.5 已发布到 ohpcd 制品仓（recipe revision 5f009907, 2026-09-09）
- ethtool CI 依赖解析已验证通过（build #50462）

---

**最终状态**: built (conan-verify G2 通过, PR CI 校验通过)
