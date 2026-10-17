# libtermkey 0.22 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-09-01
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码：https://www.leonerd.org.uk/code/libtermkey/libtermkey-0.22.tar.gz
2. 解压源码：tar -xzf libtermkey-0.22.tar.gz
3. 设置环境变量：
   - PREFIX=/storage/Users/currentUser/usr/local
   - PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig
4. 编译：make PREFIX=$PREFIX PKG_CONFIG_PATH=$PKG_CONFIG_PATH
5. 测试：make test（全部通过，17个测试文件，433个测试）
6. 安装到 staging：make install PREFIX=$PREFIX DESTDIR=$TEST_PREFIX
7. 安装到本地：make install PREFIX=$PREFIX

> **conan 配方构建方式（v2）**：上游 Makefile 依赖 libtool，而 CI worker 无 libtool
> （CI 实测 `make: libtool: No such file or directory`）。配方改为**手动编译**：
> 用 conan 提供的 clang 直接编译 termkey.c / driver-csi.c / driver-ti.c（
> `-fPIC -O2 -Wall -std=c99 -I<unibilium include> -DHAVE_UNIBILIUM`），
> 再用 llvm-ar 归档为 libtermkey.a（shared=False 默认），不依赖 make/libtool。
> 与本仓库 libXext 手动编译先例一致。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pkg-config 未找到 unibilium | PKG_CONFIG_PATH 未设置 | 设置 PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig |

## 源码修改

无补丁，源码无需修改即可编译。

## 依赖版本

- unibilium: 2.1.2
- libtool: 2.4.7
- clang: 15.0.4

## 验证结果

```bash
# 测试结果
make test
All tests successful.
Files=17, Tests=433,  3 wallclock secs
Result: PASS

# pkg-config 验证
pkg-config --modversion termkey
0.22

# 功能验证
TermKey *tk = termkey_new(0, TERMKEY_FLAG_SPACESYMBOL);
✅ Successfully created TermKey instance
Buffer size: 256
Flags: 40
```

## 交付物

> 注：以下为本地 `make install`（libtool 默认）产物；Conan 配方 `default_options.shared=False`，
> conan 包默认仅包含静态库。如需动态库请以 `-o shared=True` 构建。

| 文件 | 大小 | 说明 |
|------|------|------|
| libtermkey.a | 56K | 静态库（conan 默认产物）|
| libtermkey.so.1.14.2 | 134K | 动态库（仅 shared=True 时进包）|
| termkey.h | 7.3K | 头文件 |
| termkey.pc | - | pkg-config 文件（pkg_config_name=termkey）|
| man/*.gz | - | 手册页 |

## 注意事项

- libtermkey 使用 unibilium 作为终端数据库（而非 ncurses）
- 编译需要设置正确的 PKG_CONFIG_PATH（unibilium 的 .pc）
- 无可执行二进制文件（纯库）
- 测试全部通过，无警告
- **CI 环境说明（P3-2）**：本地 W3 预下载阶段缺 `curl`（报 3 次 try 失败后降级用 conan 内置下载器成功兜底），属 CI 基础设施缺失，不影响配方正确性；远端 CI worker 需保证 `curl` 可用。
---

**编译结束**: 2026-09-01 02:11
**最终状态**: built
