# afuse 0.5.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-07
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
# 配方通过 conan create 驱动，源码为 GitHub tag 归档（不含预生成 configure）
autoreconf --install --verbose     # 自举生成 configure
sed -i 's/umask 077/umask 000/g' configure   # E114: config.status 临时目录沙箱权限
./configure --prefix=/
make -j1
```

关键点：`ACLOCAL_PATH` 必须注入到 toolchain env（`tc.environment()` →
`tc.generate(env=env)`），配方自身的 `buildenv_info` 不影响自身构建环境，
否则 aclocal 找不到 pkg.m4，`PKG_CHECK_MODULES(FUSE, fuse3 >= 3.0)` 无法展开。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G2 下载超时 | conandata.yml 用 ghfast.top 镜像，沙箱不可达 | R39：只保留官方 GitHub URL，由 CI 镜像 fallback |
| 2 | configure `syntax error near unexpected token FUSE` | aclocal 找不到 pkg.m4（PKG_CHECK_MODULES 未展开） | generate() 用 toolchain env 注入 ACLOCAL_PATH |
| 3 | `fatal error: 'fuse.h' file not found` | libfuse 3.x 头文件在 include/fuse3/ | 补丁把 include 改为 `<fuse3/fuse.h>`/`<fuse3/fuse_opt.h>` |
| 4 | test_package 失败 | `afuse -h` 的 KEY_HELP 设计退出码为 1，测试曾断言 exit 0 | 校验非 0 退出码；无参数/`-h` 若为 0 则 FAIL（R34） |

## 源码修改

- `0001-configure.ac.patch` — FUSE2→FUSE3 pkg-config/宏版本：
  `PKG_CHECK_MODULES` 由 `fuse >= 2.3` 改为 `fuse3 >= 3.0`，`FUSE_USE_VERSION` 25→31，
  移除硬编码 `PKG_CONFIG_PATH` export。
- `0002-src-afuse.c.patch` — FUSE3 高层 API 移植：
  `fuse_main` 尾参、`fuse_operations` 回调签名（fi/flags）、`fuse_fill_dir_t` flags、
  `utime`→`utimens`（utimensat）、删除 `ftruncate`/`fgetattr` 成员、
  头文件 `<fuse3/fuse.h>`/`<fuse3/fuse_opt.h>`。

## 依赖版本

- libfuse/3.18.2（Conan 制品仓，FUSE 3.x）

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify afuse 0.5.0   # G0-G4 + L2/L4/L5 全 PASS
python3 scripts/ohc-run.py finish afuse 0.5.0 published  # 9 步收尾完成
```

test_package 实质测试：afuse 二进制执行、参数解析、真实挂载尝试到达 FUSE 层。
`open("/dev/fuse")` 返回 Permission denied 为鸿蒙沙箱平台限制（无 FUSE 设备访问权）。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/afuse | automounter 守护进程（可执行） |
| bin/afuse-avahissh | 辅助 shell 脚本 |

## 注意事项

- 运行时挂载依赖 `/dev/fuse`，鸿蒙沙箱无该设备访问权 → 挂载尝试在
  `libfuse fuse_mount → open("/dev/fuse")` 处失败（Permission denied），属平台限制。
- conandata.yml 中 ghfast.top 镜像在本沙箱不可达，注释说明勿回退到该镜像。
---

**编译结束**: 2026-08-07 18:57
**最终状态**: published
