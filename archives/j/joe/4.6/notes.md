# joe 4.6 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-06-03
- 目标平台: aarch64-unknown-linux-ohos (OpenHarmony)
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 链接器: GNU ld.bfd 2.45 (不使用 ld.lld，因 libxml2 依赖问题)
- 依赖: ncurses 6.5 (静态链接 libncurses.a)
- 状态: built

---

## 编译步骤（实际执行顺序）

### 1. 初始化
```bash
SKILL_ROOT="$(dirname "$(find ~/.opendesk -name "SKILL.md" -path "*openharmony-compile-agent*")")"
python3 $SKILL_ROOT/scripts/ohc-run.py init-build joe 4.6 --url=... --no-download
```
> 注: SSL 证书问题导致自动下载失败，手动 `curl -k` 下载后用 `--no-download`

### 2. 源码预处理与补丁

**补丁 1: config.guess (E072)**
- 旧版 config.guess (2013年) 不识别 OHOS 平台
- 且其内部 `mktemp ./confXXXXXX` 在 HMDFS 上有权限问题
- 解决: 替换为简化版脚本（28行），直接输出 `aarch64-unknown-linux-ohos`

**补丁 2: config.sub (E072)**
- 缺少 OHOS OS 白名单，三处修改:
  1. `maybe_os` 行添加 `linux-ohos*` (~行118)
  2. `ohos-linux` case block (~行129，在 android-linux 之后)
  3. `kernel-os` 白名单添加 `-linux-ohos*` (~行1372)

**补丁 3: configure (E064 + E011)**
- 修改:
  1. mktemp 路径从 `./confXXXXXX` 改为 `${TMPDIR:-$HOME/tmp}/confXXXXXX`
  2. umask 从 `077` 改为 `022`（HMDFS setgid + umask 077 导致临时目录不可写）
- 注: 原方案在 configure 中添加 sign-elf 钩子，已改为交叉编译模式跳过 conftest 执行

**补丁 4: joe/path.c (PSCAN-FS-001)**
- `/tmp/` 硬编码 → OHOS 上 /tmp 只读
- 添加 `#ifdef __OHOS__` 守卫: `_PATH_TMP` 设为 `/data/local/tmp/`

> 注: umask 077→022 修复已合并到补丁 0003 (configure) 中，不再单独处理 config.status

### 3. Configure
```bash
cd $BUILD_SRC_DIR
LDFLAGS="-L$DEFAULT_PREFIX/lib -fuse-ld=bfd" ./configure --prefix=$DEFAULT_PREFIX
```
> 注: configure 自动运行 config.status 时因 HMDFS umask 问题失败，需手动运行 `./config.status`

### 4. 编译
```bash
make -j1
```
成功编译 joe 二进制 (2164672 bytes)

### 5. DESTDIR 安装
```bash
make install DESTDIR=$TEST_PREFIX
```
安装到 staging 目录，5个二进制/符号链接 + 10个配置文件 + 4个数据目录 + 文档

### 6. make check
```bash
make check
```
joe 无自动化测试套件，全部模块输出 "Nothing to be done for 'check'"

### 7. 预编译包制作
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package joe 4.6
```
生成: joe-4.6-ohos-aarch64.tar.gz (5780KB) + debug tar.gz (500KB)

### 8. 本地安装
```bash
make install  # 不带 DESTDIR
$DEFAULT_PREFIX/bin/joe --help  # → "Joe's Own Editor v4.6"
```

### 9. 验证门禁
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py verify-build joe 4.6
```
G1-G4 全 PASS

---

## 遇到的问题与解决方案

| # | 问题 | 根因 | 知识图谱 | 解决方案 |
|---|------|------|----------|----------|
| 1 | config.guess 不识别 OHOS | 2013年旧版不支持 | E072 | 替换为简化版脚本（直接输出三元组） |
| 2 | config.sub 不验证 linux-ohos | 缺少 OS 白名单 | E072 | 添加 3 处 ohos 模式 |
| 3 | configure conftest 无法执行 | OHOS 安全策略限制未签名 ELF 执行 | E064 | 使用跨编译模式（--build != --host）跳过 conftest |
| 4 | config.status 临时目录不可写 | HMDFS umask 077 + setgid | E011 | 修改 umask 为 022 |
| 5 | ld.lld 加载 libxml2.so.16 失败 | OHOS ld.lld wrapper 依赖 libxml2 | 无现存条目 | 使用 `-fuse-ld=bfd` |
| 6 | joe/path.c 硬编码 /tmp/ | OHOS /tmp 只读 | PSCAN-FS-001 | __OHOS__ 守卫改用 /data/local/tmp/ |
| 7 | SSL 证书下载失败 | SourceForge SSL chain 问题 | 无 | 手动 curl -k 下载 |

---

## 源码修改清单

| 文件 | 补丁 | 原因 | 变更量 |
|------|------|------|--------|
| config.guess | 0001 | E072: OHOS 平台识别 | +29/-1554 |
| config.sub | 0002 | E072: OHOS OS 白名单 | +7/-3 |
| configure | 0003 | E064+E011: mktemp路径 + umask 022 | +3/-3 |
| joe/path.c | 0004 | PSCAN-FS-001: /tmp 只读 | +4/-2 |

> config.status 的 umask 修改已合并到补丁 0003 (configure 源码补丁)

---

## 编译关键参数

```bash
# configure 命令
./configure --prefix=/storage/Users/currentUser/usr/local \
  LDFLAGS="-L/storage/Users/currentUser/usr/local/lib -fuse-ld=bfd"

# 为什么 -fuse-ld=bfd:
#   OHOS SDK 的 ld.lld wrapper 依赖 libxml2.so.16，
#   而 libxml2 未预装，导致链接失败。
#   GNU ld.bfd 不依赖 libxml2，可正常工作。

# 为什么需要跨编译模式:
#   OHOS 安全策略限制未签名 ELF 二进制执行，
#   configure 的 conftest 编译后无法执行。
#   通过 --build != --host 强制跨编译模式，跳过 conftest 运行测试。
```

---

## 验证结果

### 二进制信息
```
类型:   ELF executable, 64-bit LSB arm64, static
大小:   2164672 bytes (2116KB)
依赖:   无动态依赖 (ncurses 和 libc 均静态链接)
版本:   Joe's Own Editor v4.6
别名:   jmacs → joe, jstar → joe, jpico → joe, rjoe → joe
```

### 安装文件
```
bin/joe              — 主编辑器二进制
bin/jmacs            → joe (Emacs 模式)
bin/jstar            → joe (WordStar 模式)
bin/jpico            → joe (Pico 模式)
bin/rjoe             → joe (受限模式)
etc/joe/             — 10 个配置文件 (joerc, jmacsrc, jstarrc, jpicorc, rjoerc 等)
share/joe/           — syntax, colors, lang, charmaps 数据文件
share/doc/joe/       — README.md, NEWS.md, ChangeLog, hacking.md
share/man/man1/joe.1 — 英文 man 页面
share/man/ru/man1/joe.1 — 俄语 man 页面
```

---

## 交付物

| 文件 | 大小 | SHA256 |
|------|------|--------|
| joe-4.6-ohos-aarch64.tar.gz | 5780KB (5919131) | 09b3ab60c6b71c86e9349559c82d68f4d43691ee167fe6b45d412328652031b6 |
| joe-4.6-ohos-aarch64-debug.tar.gz | 500KB (500834) | c2954faa537273bb15206491cfb72e715e783d5c06fec64b06e191e6f08a33cf |

源码包 SHA256: `495a0a61f26404070fe8a719d80406dc7f337623788e445b92a9f6de512ab9de`

---

## 注意事项

1. **joe 无 --version 标志**: joe 是终端交互式编辑器，不支持 `--version`，但 `--help` 输出首行包含版本号 "Joe's Own Editor v4.6"
2. **HMDFS setgid 不可移除**: 目录的 setgid 位无法通过 `chmod g-s` 移除（平台限制），需修改 umask 为 022 作为替代方案
3. **configure 自动运行 config.status 会失败**: 因 HMDFS umask 077 问题，需要手动运行 `./config.status`
4. **必须使用 -fuse-ld=bfd**: ld.lld 在 OHOS 上有 libxml2 依赖问题，bfd 可正常工作
5. **config.guess 简化版**: 原版 config.guess 内部 mktemp 在 OHOS 上有权限问题，简化版脚本避免了此问题
6. **ncurses 静态链接**: OHOS 上 ncurses 以静态库 (.a) 安装，joe 链接后已编入二进制，无额外动态依赖

**知识整理**: pending（42 条草稿待 editor 审核）

---

**编译结束**: 2026-08-05 10:06
**最终状态**: built
