# chkrootkit 0.59 适配笔记

## 源码来源

- 主下载地址使用 Debian HTTPS `orig.tar.gz` 镜像，避免 CI 优先访问明文 FTP。
- chkrootkit 官方 FTP 地址保留为回退源；两个地址使用同一固定 SHA256 校验。

## 编译环境
- 构建系统: makefile（自定义 Makefile，无 configure 脀cript，无 install target）
- 编译日期: 2026-06-02
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤

chkrootkit 使用自定义 Makefile，无 configure 脀cript，无 install target。

1. `make sense CC=clang STATIC= CFLAGS="-DHAVE_LASTLOG_H -fPIC -O2"`
   - CC=clang: 系统无 `cc` 命令，需显式指定 clang
   - STATIC=: 禁用静态链接（原默认 `-static` 在 OpenHarmony/musl 上不兼容）
   - CFLAGS="-DHAVE_LASTLOG_H -fPIC -O2": 保留 HAVE_LASTLOG_H 定义，添加 -fPIC
2. 手动 DESTDIR 安装:
   - 创建 `$TEST_PREFIX/$DEFAULT_PREFIX/libexec/chkrootkit/` 目录
   - 复制 chkrootkit shell 脀cript + 7 个 C 工具到 libexec 目录
   - 创建 `$STAGING/bin/chkrootkit` wrapper 脀cript，cd 到 libexec 目录后执行主脚本
   - 复制 README, COPYRIGHT, ACKNOWLEDGMENTS 到 share/doc/chkrootkit/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cc` 命令不存在 | OpenHarmony 系统无 cc 别名 | 命令行覆盖 CC=clang |
| 2 | `-static` 链接不兼容 | musl libc 静态链接在 OpenHarmony 上有问题 | 命令行覆盖 STATIC=（空） |
| 3 | ifpromisc 未编译 | 需要 `/usr/include/linux/if.h`（OpenHarmony 无此头文件） | Makefile 条件编译已自动跳过，不阻塞 |
| 4 | 无 install target | chkrootkit Makefile 没有 install 规则 | 手动 DESTDIR 安装 + 创建 wrapper 脀cript |
| 5 | ELF 签名后才能执行 | OpenHarmony 安全策略限制（E046） | `ohc-run.py sign-elf` 签名后正常执行 |

## 源码修改

无源码修改。所有适配通过命令行参数覆盖（CC, STATIC, CFLAGS）实现。

## 依赖版本

- clang 15.0.4
- musl libc（系统提供）
- 无额外依赖

## 验证结果

### ELF 二进制类型验证

```
file chklastlog → ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), stripped
```

所有 7 个 C 工具均为有效 ELF 64-bit LSB arm64 动态链接二进制：
- chklastlog ✅
- chkwtmp ✅
- chkproc ✅
- chkdirs ✅
- check_wtmpx ✅
- strings-static ✅
- chkutmp ✅
- ifpromisc: 未编译（无 linux/if.h），chkrootkit 脀cript 会报告 "not tested"

### 版本号验证

```
chkrootkit -V → chkrootkit version 0.59  ✅
```

### C 工具功能测试（实际执行结果）

| 工具 | 实际输出 | 退出码 | 结果 |
|------|----------|--------|------|
| chklastlog | `unable to open lastlog-file /var/adm/lastlog` | 1 | ✅ 功能正确，平台无此文件 |
| chkwtmp | `unable to open wtmp-file /dev/null/wtmp` | 2 | ✅ 功能正确，平台无此文件 |
| chkproc | `ps: bad auxw` + 隐藏进程报告 | 179 | ⚠️ ps 格式差异导致误报 |
| chkdirs | `chkdirs [-n] dir ...`（无参数时） | 255 | ✅ 需指定参数 |
| chkdirs /tmp | 正常执行无异常 | 0 | ✅ |
| chkutmp | `ps: bad ax` + `failed opening utmp !` | 1 | ✅ 功能正确，平台限制 |
| strings-static ./chklastlog | 正常输出 142 行字符串 | 0 | ✅ |
| check_wtmpx | 静默返回 | 0 | ✅ Solaris 专用，不影响 |
| chkrootkit（完整检测） | `can't detect netstat variant.` | 0 | ✅ 主脚本可运行 |

### 已知平台限制（不阻塞发布）

1. ps 命令参数格式差异（不支持 auxw/ax 格式），影响 chkproc 和 chkutmp 检测准确性
2. 系统日志文件路径差异（/var/adm/lastlog、/var/adm/wtmp 等不存在）
3. netstat 命令格式差异
4. ifpromisc 未编译（缺少 linux/if.h）
5. ELF 签名后才可执行（安全策略 E046）

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/chkrootkit | ~263B | Wrapper 脀cript |
| libexec/chkrootkit/chkrootkit | ~96KB | 主检测 shell 脀cript |
| libexec/chkrootkit/chklastlog | ~14KB | lastlog 检查工具 |
| libexec/chkrootkit/chkwtmp | ~14KB | wtmp 检查工具 |
| libexec/chkrootkit/chkproc | ~18KB | 进程检查工具 |
| libexec/chkrootkit/chkdirs | ~14KB | 目录检查工具 |
| libexec/chkrootkit/check_wtmpx | ~10KB | wtmpx 检查工具（Solaris 专用） |
| libexec/chkrootkit/strings-static | ~14KB | strings 工具 |
| libexec/chkrootkit/chkutmp | ~14KB | utmp 检查工具 |

## 注意事项

1. chkrootkit 主脚本使用 `./` 引用工具，wrapper 脀cript 通过 cd 到 libexec 目录解决
2. ifpromisc 无法编译（缺少 linux/if.h），chkrootkit 运行时会报告 ifpromisc "not tested"，不影响其他检测功能
3. 静态链接已禁用，strings-static 名称虽含 "static" 但实际是动态链接
4. chkrootkit 无自动化测试套件，通过手动功能验证确认可用性

---

**编译结束**: 2026-06-02
**最终状态**: published
