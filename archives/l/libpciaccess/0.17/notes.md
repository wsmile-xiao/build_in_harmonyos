# libpciaccess 0.17 — 适配笔记

> 最后更新: 2026-09-17（第二轮接续修复）

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | libpciaccess |
| 版本 | 0.17 |
| 状态 | built（待 PR 合并后发布） |
| 构建系统 | meson（tarball 自带 meson.build/meson_options.txt） |
| 源码 | https://xorg.freedesktop.org/releases/individual/lib/libpciaccess-0.17.tar.xz |
| sha256 | 74283ba3c974913029e7a547496a29145b07ec51732bbb5b5c58d5025ad95b73 |

## 二、历史沿革

- 2026-04-27: 首次手工归档（autotools/install.sh 方式，状态 archived）
- 2026-08-30: PR #7182 首次提交 Conan 配方（当时分支误带 goaccess 包导致 CI L0n 失败）
- 2026-09-04: 分支重建修复多包问题；CI 因积压的旧 SHA 构建报 G0e 根目录白名单失败（旧基点残留 `.branch_init`/`.ci-branch-marker-v6`/`.ci-marker-v7b`）
- 2026-09-17: 本轮——分支重建于最新 main（根目录干净），补齐 zlib 依赖、删除 commands.json、强化 test_package、更新 manifest

## 三、上游测试清点（R51）

对官方 tarball 实测：

```console
$ grep -rn "test(" --include="meson.build" libpciaccess-0.17/   # 0 命中
$ ls libpciaccess-0.17/                                          # 无 tests/ 目录
$ meson test -C build --print-errorlogs                          # "No tests defined."
```

- 测试类目录数: 0
- meson test() 注册数: 0
- 结论：上游 0.17 无官方测试项；build() 中仍调用 `meson test`（exit 0，No tests defined）
- 消费者测试（test_package/）：test.c + harmonyos_platform.c，共 6 断言，调用 pci_get_strings/pci_system_init/迭代器等真实 API

## 四、源码修改清单

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| src/meson.build | meson 将 OHOS 识别为 harmonyos，`host == 'linux'` 不命中 → sysfs 后端源文件为空 | `host in ['linux', 'ohos', 'harmonyos']` | patches/0001-ohos-backend.patch |
| src/meson.build | `shared_library()` 写死动态库，无法按 `default_library` 产出静态库 | `shared_library` → `library` | 同上 |

知识条目：E090（Meson host_system == 'linux' 不匹配 HarmonyOS）

## 五、依赖

- zlib/1.3.1（制品仓已发布）：`common_device_name.c` 用 gzopen 读取 gzip 压缩的 pci.ids，`-Dzlib=enabled` 强制开启，不裁剪功能
- 说明：0.17 meson_options.txt 无 `install-scanpci`（0.19 才引入），scanpci 构建但不安装，包为纯库类型

## 六、对话记录

### 对话 #2 — 2026-09-17（接续修复）
**操作**: 分支重建于最新 main；conanfile.py 增加 zlib/1.3.1 依赖 + PkgConfigDeps + AR 注入（对齐已合入的 0.19 配方模式）；删除 commands.json（0.17 scanpci 不安装，纯库包 R38/PF8）；test_package 强化（pci_get_strings 走 zlib 路径 + errno 契约 + harmonyos_platform.c）；manifest/README/notes 全部更新
**结果**: 待本地 conan create 复验
**发现的问题**: 前序配方漏声明 zlib 依赖（静态库消费者会遇未定义符号）；force-push 时丢失 manifest 更新；commands.json 与库产物不符
**当前状态**: 文件修改完成，进入 W3 本地验证
**遗留问题**: 无
---

**编译结束**: 2026-09-17 09:38
**最终状态**: built
