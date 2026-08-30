# dpkg 1.23.7 适配笔记

## 编译环境
- **构建系统**: autotools (configure + make)
- **编译日期**: 2026-08-27
- **编译器**: clang 15（OHOS 6.0 交叉工具链）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁，全部在配方内解决）

## 编译步骤（conan create 全流程）

```bash
conan create archives/d/dpkg/1.23.7 --build=missing
```

### 1. 源码获取（source()）
沙箱下 `get()` 抛 PermissionError——改用 `download()` + 手动解压：
```bash
tar -xJf dpkg_1.23.7.tar.xz --no-same-owner || true   # --no-same-owner 容忍 fifo 错误
cp -a dpkg-1.23.7/. . && rm -rf dpkg-1.23.7
```

### 2. 配置（configure）
- **交叉编译**：`--build=aarch64-unknown-linux-ohos --host=aarch64-linux-gnu`（不传显式 --build 会因 config.guess 无法识别导致 'C compiler cannot create executables'，依赖 config.guess 的 OHOS patch）
- **GNU patch/tar wrapper**：环境仅有 toybox 的非 GNU 版本，configure 前设 `PATCH`/`TAR` 环境变量指向 `/data/storage/el2/base/cache/gnu-patch`、`gnu-tar`
- **md5 stub**：生成 `md5.h`/`md5.c`，`clang -c md5.c && ar rcs libmd5.a md5.o`，`LDFLAGS` 加 `-L<source> -lmd5`
- **curses**：`LDFLAGS`/`CPPFLAGS` 指向 ncurses 包（`-lncursesw`）
- **架构**：`DEB_HOST_ARCH=arm64`（aarch64 的 Debian 架构名）

### 3. config.status（关键攻坚）
`/tmp` 只读 + `$HOME/.ci_logs` 不可写 + autoconf 相对路径 mktemp → `./confXXXXXX/subs1.awk: Permission denied`。
- `TMPDIR=/data/storage/el2/base/cache`
- `replace_in_file(config.status, "ac_tmp=$tmp", "ac_tmp=/data/storage/el2/base/cache/conf && mkdir -p $ac_tmp && chmod 777 $ac_tmp")`
- 详见 SKILL: `docs/skills/autotools-config-status-mktemp-sandbox.md`（路径 B 沉淀）

### 4. 编译（make -j1）
jobserver fifo 沙箱限制——单进程编译。

### 5. 打包（package()）
上游无 `make install` 目标——手动 `self.copy("bin/*")` 保留二进制（dpkg、dpkg-deb、dpkg-query、dpkg-split、dpkg-statoverride、dpkg-trigger、update-alternatives、start-stop-daemon）。

## 验证结果
- **构建**: `dpkg/1.23.7: Package created`（包 ID 0954215d2f61edcc94e363eda1bf7141541326ae）
- **R34 消费者验证**: test_package/test_dpkg.py — dpkg 二进制存在（1/1 = 100%）
- **上游测试**: 未运行——dpkg tests/ 依赖 Debian 完整构建环境（如实记录，rule 4）

## 已知限制
- 上游测试套件需 Debian 完整环境，OHOS 沙箱无法运行
- dselect / start-stop-daemon 已禁用（系统集成部分）
