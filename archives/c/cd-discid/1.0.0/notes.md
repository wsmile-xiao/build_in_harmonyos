# cd-discid 1.0.0 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure/autotools）
- 编译日期: 2026-08-23
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，target aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

```bash
# 探索阶段（Step 2）
source .build-context-cd-discid-1.0.0 && cd $BUILD_SRC_DIR
make CC=clang -j1                          # 编译 cd-discid（唯一产物，无库）
make install DESTDIR=$TEST_PREFIX INSTALL='busybox install -c'   # staging 验证
# make check → "No rule to make target 'check'"：上游无测试目标，如实记录
```

- `linux/cdrom.h` 在 OHOS 工具链中存在，`#if defined(linux)` 分支直接命中，无需补丁。
- 二进制真实运行验证（无 CD-ROM 设备环境）：
  - `cd-discid`（无参数）→ 默认 /dev/cdrom，open: No such file or directory，exit 1
  - `cd-discid a b c`（参数过多）→ Usage: cd-discid [devicename]，exit 1
  - `cd-discid /dev/nonexistent` → open 错误消息，exit 1

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make install` 失败 `make: /usr/bin/install: No such file or directory` | 上游 Makefile 硬编码 `INSTALL=/usr/bin/install -c`，OHOS 无此工具 | 探索阶段用 `INSTALL='busybox install -c'`；Conan 配方 `package()` 中直接 copy 产物（上游 install 还含 `-o 0` root chown，OHOS 非 root 下同样不可用） |
| 2 | conan-init 生成 autotools 模板 | 检测到 autotools 构建系统，但实际是纯 Makefile 工程 | 重写 conanfile.py 为 raw Makefile 模式：`make -j1 CC=<cc>`，CC 从 `tools.build:compiler_executables` conf 获取（R33） |

## 源码修改

无源码修改、无补丁（0 patches）。

## 依赖版本

无外部依赖（仅 libc + ioctl）。

## 验证结果

```bash
# conan-verify / finish 内嵌 W3 conan create 结果见 .ci-result.json（禁止手写）
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/cd-discid | 命令行可执行文件 |
| share/man/man1/cd-discid.1 | man 手册 |

## 注意事项

- **上游无测试**：Makefile 仅 all/clean/install/tarball 四个目标，无 `check` 目标、无测试套件、无测试文件。不能编造测试输出。test_package 用真实运行行为验证替代（R34）：执行二进制并校验 Usage/open 错误路径输出格式与退出码。
- 上游 README 示例输出需要真实 CD-ROM 硬件，沙箱无 CD 设备，无法产生完整 discid 输出——如实记录，不伪造。
---

**编译结束**: 2026-08-23 14:41
**最终状态**: built
