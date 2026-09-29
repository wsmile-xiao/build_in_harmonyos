# sysklogd

系统日志守护进程 `syslogd` 与内核日志守护进程 `klogd`，上游为 troglobit/sysklogd。

## 交付内容

- `sbin/syslogd`：系统日志收集与转发守护进程
- `sbin/klogd`：内核日志读取守护进程
- 包内文件共 10 个（本表**不逐条列举**：清单以 `1.5.1/reports/test-report.md` 里对已打包目录 `find <pkg> -type f` 的实测读数为准，避免此处出现未经核对的第二套口径）

## 软件信息

- **上游源码**: https://github.com/troglobit/sysklogd
- **官方发布 tarball**: https://www.infodrom.org/projects/sysklogd/download/sysklogd-1.5.1.tar.gz
  （`sha256 5166c185ae23c92e8b9feee66a6e3d0bc944bf673112f53e3ecf62e08ce7c201`，90011 B，由真实下载计算并与 `1.5.1/conandata.yml` 声明值核对一致）
- **分类**: 系统工具 / 日志
- **许可证**: GPL-2.0（以上游为准）

## 鸿蒙适配要点

| 要点 | 说明 |
|------|------|
| 构建系统 | **纯 Makefile，不是 autotools**：上游 tarball 内不存在 `configure`/`configure.ac`/`Makefile.am`（实测），故不走 `Autotools` 辅助类 |
| 依赖 | 无 Conan 依赖（`preflight_check.sh sysklogd/1.5.1` 报"无依赖需要检查"，RC=0）；只用 libc 与内核 uapi 头 |
| `-DSYSV` | **不可丢**：丢了 `sys/msgbuf.h` 支路不成立，`syslogd` 编译不过 |
| klogd 系统调用 | musl 派生 sysroot 不提供 glibc 时代的 `_syscallN()` 便捷宏（`sys/syscall.h` 只给号码不给生成器），而上游 `klogd.c` 用 `#if !defined(__GLIBC__)` 自造 syscall ⇒ 改走 libc 已有的 `klogctl()`，**功能不裁剪**（不是 `-DNO_SYSLOG` 那类关功能方案）。机制已抽为知识库草稿 `knowledge/drafts/DRAFT-sysklogd-1.5.1-syscalln-macro-missing-defers-to-link`，关联 Issue #3300 |
| 补丁形态 | 6 条补丁全部声明在 `1.5.1/conandata.yml` 并在 `build()` 中真实应用；一律做**能力判定**而非平台判定，新增行不含 `__OHOS__` 类平台宏（R8/PF5） |
| 安装 | 上游 `install_exec` 把 `syslogd` 与 `klogd` 两个目标硬绑在同一条规则里 ⇒ 配方在 `package()` 内手工安装到 `sbin/`，与 `package_info` 暴露的 `bindirs` 一致 |
| 运行期 | `klogd` 读取内核日志受 `CAP_SYSLOG` 与编译期固定的 pid 文件路径限制 ⇒ 相应消费者断言记 **SKIP** 而非通过（见 `1.5.1/reports/test-report.md`） |

## 已知限制

1. `klogd` 的运行期内核日志读取**未在本平台真机验证**（`CAP_SYSLOG` 前提不成立），该断言按 SKIP 处理，不并入通过数。
2. `conan-verify` 的 `G4` 属**降级 PASS**（`scripts/ohc/conan_verify.py:737` 仍按旧的三层缓存结构取 package ID，在 conan 2.29.1 下打印"无法找到程序包 ID"却记 PASS、L2/L4/L5 跳过）⇒ 本包**不把 G4 当独立产物证据**，改由手工补验：包内 10 个文件、`syslogd 55744 B`、`klogd 43392 B`、`ELF arm64 dynamic not stripped`、包内 `syslogd -v` RC=0。
3. 上游 `make test` 的产物含内核模块 `oops.ko`，本设备无外部模块构建树（`ls /lib/modules` RC=1、无 `/usr/src`）⇒ 不可编译亦不可加载。

## 版本目录

- `1.5.1/` —— 当前交付版本（配方、补丁、`test_package`、`notes.md`、`reports/`）
