# libstatgrab 0.92.1 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-09-02
- 编译器: clang 15.0.4 (OHOS SDK 26.0.0.18 sysroot, aarch64)
- 状态: built

## 编译步骤

```bash
./configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu \
    --enable-tests --enable-thread-support --prefix=...
make -j1
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: cannot guess build type | OHOS kernel 不被 config.guess(2018) 识别 | 显式 --build/--host=aarch64-unknown-linux-gnu（E007/E160 既有知识） |
| 2 | config.status: can't create ./confXXX/subs1.awk: Permission denied | umask 077 临时目录在 OHOS 受限文件系统写入被拒 | build() 中 sed 替换 umask 077→022（E052/E118 既有知识） |
| 3 | redefinition of 'sysinfo' | OHOS sysroot 的 sys/sysinfo.h 与 linux/sysinfo.h（经 ethtool.h 链）均定义 struct sysinfo | tools.h 中先 include <linux/sysinfo.h> 并 define _LINUX_KERNEL_H，使 sys/sysinfo.h 跳过 struct（同族模式见 E091/E119 sockaddr_storage） |
| 4 | undefined reference: ethtool_cmd_speed | OHOS linux/ethtool.h 缺该内联函数（有 speed/speed_hi 字段） | network_stats.c 增加 __OHOS__ 守卫的本地实现 |
| 5 | test_package: Library 'libstatgrab' not found | cpp_info.libs 声明 "libstatgrab" 与实际 -lstatgrab 不符 | cpp_info.libs = ["statgrab"] |

## 源码修改

- 0001-src-libstatgrab-network_stats.c.patch — ethtool_cmd_speed 本地实现（__OHOS__ 守卫）
- 0002-src-libstatgrab-tools.h.patch — sysinfo 重定义规避（__OHOS__ 守卫）

## 依赖版本

无外部 Conan 依赖（仅系统头文件 + 可选 ncurses）。

## 验证结果

- 上游测试: 12 个独立 API 用例，10/12 通过 (83.3%)；fs_stats 返回 0 项、disk_io_stats /proc/diskstats 权限受限（OHOS 沙箱，非代码缺陷）
- HarmonyOS 专项测试: sg_init/host_info/mem_stats/load_stats/cpu_stats 全部 PASS (exit 0)
- conan create + test_package: 通过 (W3 exit 0)
- 知识路径判定: 依赖项（task_type=依赖项，initial_pr_prefix=【依赖项】）；sysinfo 重定义属 E091/E119 同族模式，无足够独立新增知识价值，路径 B 不成立

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Autotools 配方（R26 静态、--build/--host、umask 022、源码内存适配） |
| conandata.yml | 官方源 + SHA-256 5688aa4a… |
| test_package/ | 实质消费者测试（10 断言） |

## 注意事项

- cpp_info.libs 必须是 "statgrab"（库文件 libstatgrab.a）而非 "libstatgrab"
- /proc/diskstats、/proc/mounts 在 OHOS 沙箱下只读受限，影响 fs/disk_io 测试
---

**编译结束**: 2026-09-02 13:57
**最终状态**: built
