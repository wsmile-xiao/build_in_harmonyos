# owfs 3.2p4 — 编译进度

> 档案创建时间: 2026-09-08
> 最后更新: 2026-09-08
> 编译完成日期: —

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | owfs |
| 版本 | 3.2p4 |
| 状态 | 🔄 pending |
| 构建系统 | autotools |
| 源码来源 | github.com/owfs/owfs (release tarball) |
| 许可证 | GPL-2.0-only AND LGPL-2.0-only |
| 上游最后发布 | 2020-08-23 |

## 二、适配策略

### 初始目标

仅编译**网络模式**组件，禁用所有硬件总线主机适配器：

| 模块 | 状态 | 说明 |
|------|------|------|
| owlib (libow) | ✅ 启用 | 核心 1-wire 协议库 |
| owcapi (libowcapi) | ✅ 启用 | C API 接口 |
| owserver | ✅ 启用 | 网络服务器 |
| owhttpd | ✅ 启用 | HTTP 服务器 |
| owftpd | ✅ 启用 | FTP 服务器 |
| owshell | ✅ 启用 | CLI 工具集 |
| ownet / ownetlib | ✅ 启用 | 网络客户端库 |
| owtap / owmon | ✅ 启用 | 调试/监控工具 |
| owfs (FUSE) | ⚠️ 条件启用 | 依赖内核 FUSE 支持 |
| USB 适配器 | ❌ 禁用 | 初始阶段不启用 |
| i2c 适配器 | ❌ 禁用 | 初始阶段不启用 |
| W1 适配器 | ❌ 禁用 | OHOS 无 W1 内核模块 |
| 并口适配器 | ❌ 禁用 | OHOS 无 parport 设备 |
| FTDI 适配器 | ❌ 禁用 | 初始阶段不启用 |
| SWIG 绑定 | ❌ 禁用 | 不需要 |
| 单元测试 | ❌ 禁用 | 需 check 框架，后续启用 |

### HarmonyOS 特殊处理

| 问题 | 根因 | 解决方案 |
|------|------|---------|
| configure umask 077 | HMDFS 不支持 per-process umask 隔离 | patch umask → 022 |
| daemon() 不可用 | OHOS 沙箱禁止 fork+setsid | `__OHOS__` 条件编译跳过 |
| config.guess 不识别 OHOS | 老版 autotools 不知 HongMeng 内核 | 注入 OHOS 检测块 |
| config.sub 不识别 ohos | 同上 | 注册 ohos → linux-gnu 映射 |
| install_sh 路径 | OHOS /system/bin/install | conanfile fix_install_helpers |

## 三、依赖

| 依赖 | 版本 | 仓库已有 | 备注 |
|------|------|---------|------|
| libfuse | 3.18.2 | ✅ | fuse3，Meson 构建 |
| libusb | 1.0.27 | ✅ | 可选，初始禁用 |
| uthash | 2.4.0 | ✅ | header-only |
| pthread | — | 系统 | musl 内置 |

## 四、编译阶段

### Phase 1: 环境准备
- [ ] init-build 完成
- [ ] autoreconf（如需要）

### Phase 2: 编译
- [ ] configure 完成
- [ ] make 编译完成
- [ ] make install 完成

### Phase 3: 测试验证
- [ ] test_package 通过（编译+链接）
- [ ] test_package 运行通过（可运行环境）

### Phase 4: 预编译包制作
- [ ] ohc-run.py package 完成

### Phase 5: 归档收尾
- [ ] manifest.yaml 更新 status/build_date
- [ ] notes.md 更新各阶段状态
- [ ] functional-test-report.md 生成
