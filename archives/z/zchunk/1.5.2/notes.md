# zchunk 1.5.2 适配笔记

## 编译环境
- 构建系统: meson（vendored meson 1.11.2 进程内调用）
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4（OHOS aarch64，profile ohos-aarch64）
- 状态: built（conan-verify 全门禁通过）

## 编译步骤

conan create 全自动流程（-pr:h/-pr:b ohos-aarch64，--build=missing）：

1. source()：下载官方 tarball（sha256 校验）+ vendored meson 1.11.2 解压到 meson-vendor/
2. generate()：MesonToolchain（native file，含绝对 llvm-ar/llvm-ranlib 注入）+ PkgConfigDeps（聚合 .pc 到 generators 目录）
3. build()：vendored meson setup（--prefix=/ --native-file conan_meson_native.ini，项目选项 with-zstd/with-curl/with-openssl=enabled, tests=true, docs=false, default_library=static）→ ninja -j1 → meson test（上游测试）→ meson install --destdir
4. test_package：CMake 消费者程序链接 libzck，真实调用 API 断言

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 真机/CI PATH 无 meson，远端无 meson 工具包 | 上游用 meson 构建 | vendored meson 1.11.2（conandata 记 sha256），build() 经 python3 -c 进程内 sys.path 注入调 mesonmain.main()（astroterm/1.0.9、libdvdnav/7.0.0 已验证方案） |
| 2 | dependency('libzstd') 报 not found | 配方未声明 PkgConfigDeps，无 .pc 可查 | generate() 增加 PkgConfigDeps，build() 的 PKG_CONFIG_PATH 指向 generators 目录 |
| 3 | openssl/3.5.6.1.2 与图中 3.5.6.1 冲突 | curl/8.15.0.1 钉版 openssl/3.5.6.1 | 本配方改钉 openssl/3.5.6.1 对齐 |
| 4 | meson argp 探针失败后强依赖 argp-standalone | OHOS musl 无 argp.h/argp 库 | conan argp-standalone/1.4.1 经 pkg-config 名 'argp-standalone' 命中 |
| 5 | 消费者测试首 chunk size=0 | buzhash 自动分块天然产生空首 chunk | 测试跳过空 chunk 找首个非空（与上游 read_single_chunk.c 直接读 chunk 1 的口径一致） |
| 6 | zck_set_ioption(ZCK_COMP_TYPE) 返回 false | 未进写入模式前不可设压缩参数 | 改用上游工具同款流程 zck_init_write/zck_init_read |
| 7 | /tmp 不可写致 mkstemp 失败 | OHOS 设备 /tmp 受限（E002） | 测试临时文件改用 TMPDIR，退回当前目录 |

## 上游测试五维账本（诚实口径）

- `N_static = 37`：test/meson.build 的 test() 注册数（22 无条件 + 15 仅小端机注册；aarch64 小端全部命中；zstd 版本相关分支只影响期望 SHA 常量，不影响注册数）
- `N_registered = 37`（meson 实际注册，与静态数一致）
- `N_executed = 37`：Ok 36 + Expected Fail 1（invalid_input_checksum 类用例，上游故意断言错误处理路径）
- 未执行 = 0；失败 = 0；跳过 = 0
- `N_consumer = 1`（test_zchunk，conan create 内实际编译运行通过）：zck_init_write→zck_write→zck_close→zck_init_read→分块数/尺寸==payload/回读数据 memcmp/压缩生效（comp<raw）/digest 非空

测试命令（build() 内真实执行）：vendored meson `test -v -C <build> --timeout-multiplier=16 --no-rebuild --print-errorlogs`
日志尾部汇总：`Ok: 36 / Expected Fail: 1 / Fail: 0`（meson-logs/testlog.txt）

## 源码修改

无补丁（conandata.yml patches 为空；上游源码零修改）。

## 依赖版本

- zstd/1.5.7.1（ohpcd 已发布）
- openssl/3.5.6.1（与 curl/8.15.0.1 钉版对齐，避免图中版本冲突）
- curl/8.15.0.1（zckdl 下载器）
- argp-standalone/1.4.1（musl 无 argp）
- 传递：zlib/1.3.1.1（curl 引入）

## 验证结果

```bash
ohc-run.py conan-verify zchunk 1.5.2   # G0/G1/G2/G3/G4 + L2/L4/L5 全 PASS
ohc-run.py finish zchunk 1.5.2 built   # W3 本地 CI 模拟通过，.ci-result.json exit_code=0
```

## 路径 A/B 判断

- 路径 A 主体如上。
- 路径 B 判断：不成立。候选主题「vendored meson 进程内调用」已在 astroterm/1.0.9、libdvdnav/7.0.0 落库（查重命中，无新增价值）；「PkgConfigDeps + PKG_CONFIG_PATH 对接 meson dependency()」为既有 E 条目覆盖的通用做法；空首 chunk 为 zchunk 单库特性，无跨仓库复用价值。按纯路径 A 交付。

## 对话记录

- 2026-09-18 01:44 GLM-54 领坑（zchunk 1.5.2，平台任务 12346 已在主号名下 assigned）；建 worktree feat/zchunk-1.5.2
- 01:5x W0 依赖预检（zstd/openssl/curl/argp-standalone 均已发布）；lang-preflight c（meson，主体 100%）
- 02:0x-03:0x 配方编写与迭代 9 轮 conan-verify（问题 1-7 依次定位修复）
- 03:0x conan-verify 全 PASS

---
**编译结束**: 2026-09-18 03:05
**最终状态**: built
---

**编译结束**: 2026-09-18 03:10
**最终状态**: built
