# dns2tcp 0.5.2 适配笔记

## 编译环境
- 构建系统: autotools (automake-1.11, 需 touch 时间戳防止重新生成)
- 编译日期: 2026-06-15
- 编译器: clang / clang++
- 状态: published
- 构建三联式: aarch64-unknown-linux-ohos
- 动态链接器: /lib/ld-musl-aarch64.so.1

## 编译步骤

1. `source .build-context-dns2tcp-0.5.2` — 加载编译上下文
2. `cd $BUILD_SRC_DIR` — 进入工作副本
3. 修复 config.guess/config.sub (E007) — 替换为 automake-1.17 版本
4. 修复 configure umask 077→022 (E011) — `sed -i 's/umask 077/umask 022/g' configure`
5. 修复 tentative definition (lld duplicate symbol) — extern int debug + #ifdef __OHOS__ 守卫
6. `./configure --prefix=$DEFAULT_PREFIX` — configure 成功，输出 aarch64-unknown-linux-ohos
7. `make -j1` — 编译成功，dns2tcpc + dns2tcpd 生成
8. `make install DESTDIR=$TEST_PREFIX` — staging 安装成功
9. `make check` — 无测试套件，输出 "Nothing to be done"
10. `ohc-run.py package dns2tcp 0.5.2` — 打包成功 (179KB + 74KB debug)
11. `make install` — 安装到 $DEFAULT_PREFIX (用户部署)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识编码 |
|---|------|------|----------|----------|
| 1 | config.guess 无法识别系统类型 | E007: HarmonyOS 不被旧版 config.guess (2009) 识别 | 替换 config.guess/config.sub 为 automake-1.17 版本 (自带 aarch64-unknown-linux-ohos) | E007 |
| 2 | config.status 无法创建临时文件 | E011: HMDFS UID 映射导致 umask 077 创建的临时目录无法写入 | `sed -i 's/umask 077/umask 022/g' configure`，在 configure 运行后还需修复 config.status | E011 |
| 3 | lld 链接报 duplicate symbol: debug | tentative definition `int debug;` 在 common/includes/debug.h 中，多个编译单元共享导致重复定义 | header 中改为 `extern int debug` (#ifdef __OHOS__)，在 common/dns.c 中单独定义 `int debug = 0` (#ifdef __OHOS__) | lld-tentative |

## 源码修改

5 个补丁（均使用 #ifdef __OHOS__ 守卫或 HarmonyOS 专用替换）：

- **0001-common-dns.c.patch**: `extern int debug;` → 在 `#ifdef __OHOS__` 块中定义 `int debug = 0;`，原 tentative definition 保持不变（非 OHOS 时行为不变）
- **0002-common-includes-debug.h.patch**: `int debug;` → 在 `#ifdef __OHOS__` 块中改为 `extern int debug;`，消除 tentative definition
- **0003-config.guess.patch**: 替换为 automake-1.17 版本 (2009→2024)，支持 aarch64-unknown-linux-ohos
- **0004-config.sub.patch**: 同上，替换为 automake-1.17 版本，支持 HarmonyOS 三联式解析
- **0005-configure.patch**: `umask 077` → `umask 022`（两处修改，解决 HMDFS UID 映射问题）

## 依赖版本

- **编译器**: clang (系统自带)
- **构建工具**: autotools (automake-1.11 原版，config.guess/config.sub 替换为 1.17)
- **外部依赖**: 无，仅需标准 C 库 (libc.so) 和 socket API
- **动态链接**: 仅 libc.so，无第三方库依赖

## 验证结果

### dns2tcpc 版本确认
```bash
$ $DEFAULT_PREFIX/bin/dns2tcpc -h
dns2tcp v0.5.2 ( http://www.hsc.fr/ )
Usage : /storage/Users/currentUser/usr/local/bin/dns2tcpc [options] [server]
```

### dns2tcpd 可执行确认
```bash
$ $DEFAULT_PREFIX/bin/dns2tcpd
Usage : /storage/Users/currentUser/usr/local/bin/dns2tcpd [ -i IP ] [ -F ] [ -d debug_level ] [ -f config-file ] [ -p pidfile ]
```

### 二进制格式
```bash
$ file dns2tcpc
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
$ readelf -d dns2tcpc | grep NEEDED
  Shared library: [libc.so]
```

### Staging 安装产物
| 文件 | 大小 |
|------|------|
| bin/dns2tcpc | 67,968 字节 |
| bin/dns2tcpd | 68,032 字节 |
| share/man/man1/dns2tcpc.1 | 2,972 字节 |
| share/man/man1/dns2tcpd.1 | 1,476 字节 |

## 交付物

| 文件 | 大小 | SHA256 | 说明 |
|------|------|--------|------|
| dns2tcp-0.5.2-ohos-aarch64.tar.gz | 179 KB | d41cbefc3ceb2ab0be3552129b494ff9850b9e7b3e5c143d3a9b9dd15f826027 | 预编译发布包 |
| dns2tcp-0.5.2-ohos-aarch64-debug.tar.gz | 74 KB | 8e5b1b7f152ccde55f0b382afaa9a9199d43777d2f234d5ff3ee23c3416e8da1 | 预编译调试包 |
| 源码包 dns2tcp-0.5.2.tar.gz | — | ea9ef59002b86519a43fca320982ae971e2df54cdc54cdb35562c751704278d9 | 原始源码 |

## 注意事项

- dns2tcp 没有 --version 选项，dns2tcpc 通过 --help 输出版本号 "dns2tcp v0.5.2"
- dns2tcp 没有 test suite，make check 为空操作
- 旧版 autotools (automake-1.11)，需 touch 所有 .am/.ac 时间戳防止 make 触发重新生成
- configure 运行后生成的 config.status 也会包含 umask 077，需在 configure 后再次 sed 修复
- tentative definition `int debug;` 是 C 语言历史遗留问题，lld 默认禁止（gcc 允许），需 extern + 单独定义

---
**编译结束**: 2026-06-15 11:56
**最终状态**: published
