# usleep 20160311.094456 适配笔记

## 编译环境
- 构建系统: makefile（上游手写 Makefile，无 configure）
- 编译日期: 2026-09-23
- 编译器: OHOS LLVM clang 15（`/data/service/hnp/bin/clang` → aarch64-unknown-linux-ohos-clang 包装脚本）
- 构建机: x86_64 runner 交叉编译，目标 aarch64-linux-ohos
- 状态: built（conan-verify + W3 本地 conan create 通过；CI 合并发布后置 published）

## 源码与版本
- 上游 https://github.com/cpeuvrel/usleep-aur 共 2 个提交，无 release、无 tag。
- 版本 `20160311.094456` = master 头提交 `4f880a7a4cd4e0064f10ddc84dda1716c0b99803`
  的 **committer** 时间戳 `2016-03-11T09:44:56Z`（author 时间戳为 09:43:18，不对应），
  由 GitHub commits API 的 `commit.committer.date` 核对。
- `conandata.yml` 用官方 `https://github.com/cpeuvrel/usleep-aur/archive/<sha>.tar.gz`（R39），
  sha256 `86d1c4f76d99a888497f7148f9acc2637c8016e826f399fb2eeb4179e5ed1a67` 为本地下载实测。
- 版本键必须加引号：`20160311.094456:` 不加引号时 `yaml.safe_load` 解析为 float
  （实测 `type=float`，`"20160311.094456" in sources` 为 False），
  `self.conan_data["sources"][self.version]` 会 KeyError。

## 编译步骤

手工打通（init-build 源码目录内）：

```bash
make CC=/data/service/hnp/bin/clang
# /data/service/hnp/bin/clang -Wall -Wextra -O2 -o usleep usleep.c   （零警告）
make install PREFIX=$TEST_PREFIX/bin
```

配方 `build()`：从 `tools.build:compiler_executables` 取 C 编译器（R33），
在源码目录执行 `make -j1 CC="<cc>" usleep`（上游 Makefile 写死 `CC = gcc`、无 VPATH，
命令行覆盖 CC，保留上游 CFLAGS）；`package()` 把 `usleep` 拷到 `bin/`、`LICENSE` 拷到 `licenses/`。

产物（readelf）：ELF64 AArch64，`Type: DYN`（PIE），`interpreter /lib/ld-musl-aarch64.so.1`，
`NEEDED libc.so`，`GNU_RELRO` + `BIND_NOW`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 把 manifest 构建系统写成 `autotools`，`software`/`build_system` 留 `{software}`/`{BUILD_SYSTEM}` 占位 | init-build 未识别纯 Makefile 项目；conan-init 优先读 manifest/环境变量而非源码扫描 | 先手工修正 manifest（`build.system: makefile`）再跑 conan-init，得到 makefile 模板 |
| 2 | conan-init 生成的 `sources` 是扁平 `url/sha256`，test_package 生成库形态 `test.c` + `CMakeLists.txt` | 生成器未按版本键输出，也不区分 application 包 | 手工改为版本键 `sources: {"20160311.094456": {...}}`；test_package 换成执行二进制的 `test_usleep.py` |
| 3 | 版本键 `20160311.094456` 不加引号会被 YAML 解析为 float | YAML 1.1 把 `数字.数字` 当浮点 | 版本键加双引号（conandata.yml 顶部注释说明） |
| 4 | 本地功能验证时 `usleep -5` 阻塞约 71 分钟 | `atoi()` 结果赋给 `unsigned int`，负数回绕成 4294967291 µs（上游既有行为） | 测试不使用负数；计时断言只设下界，每次运行 30 s 超时保护 |
| 5 | x86 runner 上交付的动态二进制无法运行：`qemu-aarch64: Could not open '/lib/ld-musl-aarch64.so.1'` | E544：binfmt `aarch64-binfmt-P`（flags POF）下 runner 没有 OHOS musl 加载器 | 用同源 `.o` 静态重链副本做 qemu 功能验证（见下）；test_package 在异架构主机上把功能层记为 SKIPPED，aarch64 CI worker 上必跑 |

## 源码修改

无（0 个补丁）。

## 依赖版本

- Conan 依赖：无（`requirements()` 为空）。
- 任务单列出的 `git (make)` 是上游 PKGBUILD 用 `git+git://` 拉源码的 AUR 打包期依赖；
  Conan 通过官方 archive tarball 取源码，不需要 git，W0 无需发布检查的 Conan 依赖。
- 运行时仅依赖 libc（`NEEDED libc.so`）。

## 上游测试清点（R51）

| 项目 | 结果 |
|------|------|
| 源码树文件 | 6 个：`usleep.c` `Makefile` `PKGBUILD` `.SRCINFO` `LICENSE` `.gitignore` |
| tests/ 等测试目录 | 0 个（`find -type d -name 'test*' -o -name 'check*'` 结果为 0） |
| Makefile 目标 | `usleep` / `install` / `clean`（另有 `.PHONY` 声明的 `mrproper`，无规则） |
| `make -n check` / `make -n test` | `No rule to make target 'check'` / `'test'` |
| ctest / pytest 注册 | 无 CMake、无 Python，0 项 |
| 上游测试用例数 N | **0**，可运行数 N′ = 0 |

上游确无测试，由 test_package 补全 9 项真实功能测试（见下）。

## 验证结果

```bash
# 1) test_usleep.py 对交付的动态二进制（x86 runner）
[ok] A1 ELF64 little-endian EM_AARCH64 image
[ok] A2 position-independent executable (ET_DYN)
[ok] A3 PT_INTERP is /lib/ld-musl-aarch64.so.1
[skip] F1-F6 not run: this x86_64 host cannot execute the aarch64 OHOS image
RESULT: artifact checks 3/3 passed, functional checks 0/6 run (SKIPPED)

# 2) E544 同源静态重链副本（与交付物相同的 -Wall -Wextra -O2 编译 usleep.o，再 -static 链接），
#    经 binfmt qemu-aarch64 实跑 test_usleep.py 的 F1-F6
[ok] F1 usleep [no argument] in 0.014 s
[ok] F2 usleep 0 [0 microseconds] in 0.012 s
[ok] F3 usleep 300000 [300000 microseconds] in 0.319 s
[ok] F4 usleep 1200000 [1200000 microseconds (>= 1 s)] in 1.236 s
[ok] F5 usleep abc [non-numeric argument, atoi() -> 0] in 0.015 s
[ok] F6 usleep 250000 extra [extra argument ignored] in 0.267 s
# （该副本是静态可执行文件，A2/A3 按设计不适用，报 fail 属预期）

# 3) L1e 模拟：二进制路径不存在 → A1-A3 与 F1-F6 全部 fail，exit 1
```

**如实说明**：x86 runner 上功能层只在同源静态重链副本上实跑过，**不等于交付的动态产物已实跑**；
交付产物的 F1-F6 由 aarch64 CI worker 上的 test_package 执行（该主机上功能层不允许 SKIP）。

## 注意事项

- `usleep` 的参数单位是微秒；负数参数会回绕成极长睡眠（上游行为，未修改）。
- POSIX.1-2001 允许 `usleep()` 对 ≥ 1 000 000 µs 返回 EINVAL；musl 通过 nanosleep 实现、接受 ≥ 1 s，
  F4（1 200 000 µs）在静态副本上实测睡眠 1.236 s。
---

**编译结束**: 2026-09-23 17:51
**最终状态**: built
