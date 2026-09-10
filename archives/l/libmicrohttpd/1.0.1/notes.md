# libmicrohttpd 1.0.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-06
- 编译器: clang/clang++ 15.0.4（OHOS aarch64）
- 状态: built

## 编译步骤

```bash
# 源码: GNU 官方 tarball
#   https://ftp.gnu.org/gnu/libmicrohttpd/libmicrohttpd-1.0.1.tar.gz
#   sha256: a89e09fc9b4de34dde19f4fcb4faaa1ce10299b9908db1132bbfa1de47882b94
./configure --prefix=$DEFAULT_PREFIX --disable-doc
make -j4
make check          # src/microhttpd 45 + src/testcurl 113 = 158 注册项
make install DESTDIR=$TEST_PREFIX   # staging 隔离验证
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 报 "can't create .../dummy.c: Permission denied" (E011) | HMDFS UID 映射 + umask 077 临时目录不可写 | 补丁 0001/0003: config.guess 与 configure 中 umask 077→022 |
| 2 | config.guess/config.sub (2022 版) 无法识别 HarmonyOS (E072) | 三元组 aarch64-unknown-linux-ohos 不被认识 | 补丁 0001/0002: config.guess 增加 HarmonyOS→linux-ohos 分支；config.sub 增加 ohos-linux→linux-ohos 映射、OS 白名单与 kernel-os 白名单 |
| 3 | make install Doc 阶段失败 (makeinfo 缺失, Error 127) | 构建环境无 texinfo | configure --disable-doc（配方中固化） |
| 4 | test_upgrade 并行运行偶发超时 (errno 11 EAGAIN) | 网络 socket 就绪等待超时（偶发/负载相关） | 单跑 3/3 通过 + harness 单测 1/1 通过，非功能缺陷，台账如实记录 |

## 源码修改

- `build-aux/config.guess`: umask 077→022（E011）；新增 `*:HarmonyOS:*:*` 分支 → `MACHINE-unknown-linux-ohos`；LIBC 探测新增 `__OHOS__` → ohos
- `build-aux/config.sub`: 新增 `ohos-linux` → `linux-ohos` 映射；OS 白名单与 `linux-ohos*` kernel-os 白名单（E072）
- `configure`: config.status 临时目录 umask 077→022（E011）

## 测试台账（双口径）

- source_declared_total: 70（src/microhttpd 29 + src/testcurl 40 独立用例 + src/testzzuf 1，perf 基准 2 个不计）
- configured_executable_total: 184（microhttpd 45 + testcurl 113 + testzzuf 26 注册可执行项）
- executed_passed_total: 184（含 testzzuf 26/26）
- testzzuf 恢复: zzuf/0.15 已发布到 ohpcd registry（2026-09-09），conan download 验证 exit 0；
  重新配置 --enable-heavy-tests=basic --enable-asserts（zzuf 工具路径注入），
  编译并运行 testzzuf 26 个可执行变体全部 PASS（详见 r01-zzuf-reconfigure/build/run 日志）
- 全量通过率: 70/70 = 100%；当前配置可执行集合: 184/184 = 100%

## HarmonyOS 专项测试

- `reports/test_mhd_ohos_smoke.c`: MHD_start_daemon + MHD_get_daemon_info(BIND_PORT) + MHD_stop_daemon 生命周期
- 编译运行通过 (exit 0)，输出 `libmicrohttpd version: 1.0.1` / `platform: OHOS` / `RESULT: PASS`

## 依赖

- 核心库无强制外部依赖（HTTPS 可选，默认禁用 gnutls）
- testcurl 测试依赖 libcurl/8.5.0（已发布到 ohpcd，本地部署恢复测试入口）
- testzzuf 依赖 zzuf/0.15（已发布到 ohpcd，2026-09-09 恢复配置并运行 26/26）