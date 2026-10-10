# xli 1.17.0-20061110 适配笔记

## 编译环境
- 构建系统: makefile（上游为 Imake；OHOS SDK/CI 无 imake/xmkmf → 用发行快照自带的 Makefile.std 直编）
- 编译日期: 2026-10-04
- 编译器: clang/clang++（conan profile ohos-aarch64：clang 15、aarch64-linux-ohos、musl libc）
- 状态: built

## 编译步骤

1. `conan create` 拉取源码（openSUSE/xli 快照 commit `79edc902e82970411542a0fa7dc38ce1edcae2ec`）并解压；
2. `generate()`：GnuToolchain 注入编译器与基础标志（R33：不裸用 `$CC`/`$CFLAGS`）；
3. `build()`：无补丁（patches/ 为空）→ 直接 `make -f Makefile.std -j1 all`，CFLAGS/LIBS 由 Conan 依赖图展开
   （-I/-L/-l 来自 libx11/libxext/libjpeg/libpng/zlib）：

   ```bash
   make -f Makefile.std -j1 all CC='clang' \
     CFLAGS='-O2 -DHAS_MEMCPY -Drindex=strrchr <依赖 -I>' \
     LIBS='<依赖 -L> <依赖 -l> -lm'
   ```

4. `package()`：拷 `bin/xli`、`bin/xlito`、`share/man/man1/*.man`；
5. 验证：`conan create`（G0-G4 + L2/L4/L5）+ `test_package` 消费者脚本。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make` 入口即死（找不到 Makefile） | 上游 Imakefile 需 imake/xmkmf 生成 Makefile，OHOS SDK/CI 均无该工具（制品仓无对应包） | 改用发行快照自带的 `Makefile.std`（上游文档给出的非 imake 路径）直编 |
| 2 | 链接报 `undefined reference to 'rindex'` | OHOS musl libc 未提供 BSD 遗留 `rindex()`（`index/bcopy/bzero/bcmp` 实测存在） | 编译期最小替换 `-Drindex=strrchr`；不启用上游 `-DSYSV`（会牵出同样缺失的 F_FREESP/stropts.h/poll） |
| 3 | bcopy/bzero 走 libc 兼容符号 | 老代码使用 BSD 内存函数 | `-DHAS_MEMCPY` 让上游走 memcpy/memset |
| 4 | `Makefile.std` 的 install 目标只装 xli | 上游 install 目标未覆盖 xlito | `package()` 显式补装 xlito 与 man 手册 |
| 5 | 源码站点不可用 | 上游 pantransit.reptiles.org 已下线（HTTP 404） | 取 openSUSE fork 保存的 2006-11-10 发行快照，sha256 固定（`60043c23…`） |
| 6 | 本地沙箱下载需镜像 | conandata 手写镜像前缀违反 R39/PF7 | conandata 仅保留官方 URL；镜像回退由 CI（build_and_test 预下载）/E017 自动处理 |

## 源码修改

无补丁（`patches/` 为空）：两项平台适配均为编译期特性宏（`-DHAS_MEMCPY`、`-Drindex=strrchr`），
属 POSIX/特性等价替换，不是平台条件编译（未使用 `__OHOS__` 等平台宏），符合 R8/R1 口径。

## 依赖版本

- `libx11/6.4.0`、`libxext/6.4.0`（Xlib.h / XShm.h 直接包含）
- `libjpeg/10`、`libpng/1.6.58`、`zlib/1.3.1.1`（图像编解码：jpeg.c / png.c / zio.c）

## 上游测试清点与鸿蒙特有测试（R51 三步法）

- **清点**：上游无 `test/` 目录，`Imakefile` 与 `Makefile.std` 均无 `check`/`test` 目标（135 个文件全量清点）→ 上游测试 N=0，不存在「上游用例未跑」问题；
- **本包测试 N′=1**：`test_package/test_xli_consumer.sh` 真实调用被测二进制（`xlito` 选项往返转换 + `xli -help` 启动/选项解析），逐项校验退出码与输出；
- **边界**：CI 无 X 显示，图形渲染路径仅启动级覆盖，像素级需真机 X 环境（R40：需人工确认适配完整性）；
- **结果**：N′/N′ = 1/1 通过（`conan create` 内 test_package 实跑，rc=0）。

## 验证结果

```bash
# 干净环境复现（与 CI 同源）
conan create . --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# → G0-G4 全绿 + L2 冒烟 / L4 安全扫描 / L5 产物基线；test_package rc=0（xlito 往返转换 + xli -help）
```

W3 本地 CI 模拟（`setup.sh` + `build_and_test.sh`，含 JC/L0/KC 门禁）`exit_code=0`（见 `.ci-result.json`）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `packaging/xli-1.17.0-20061110-ohos-aarch64.tar.gz` | 509 KiB | 预编译包（`bin/xli`、`bin/xlito`、man 手册） |

## 注意事项

- 上游 Imake 构建路径在本工具链下不可用，配方固定使用 `Makefile.std`；两条路径的编译单元与选项等价；
- 图形显示依赖真机 X 环境，CI 覆盖「启动 + 格式转换」路径；R40 人工确认项已在软件级 README 标注；
- `commands.json` 位于软件级目录（`archives/x/xli/commands.json`），CLI 类型 `tool`，版本与 `versions.ref` 对齐。
---

**编译结束**: 2026-10-04 11:21
**最终状态**: built
