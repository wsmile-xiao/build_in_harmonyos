# tinydns 1.05 适配笔记

## 编译环境
- 构建系统: makefile（非 autotools，无 configure）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.7（/opt/ohos-toolchain/clang，target aarch64-unknown-linux-ohos）
- 状态: published
- 依赖: 无外部依赖（纯 C，仅需 libc）

## 编译步骤
```bash
# 1) 源码解包
tar xzf djbdns-1.05.tar.gz
cd djbdns-1.05

# 2) 应用补丁（补丁头无 a/ b/ 前缀，Conan patch() 默认 strip=0，故用 -p0）
patch -p0 < 0001-error-h-include-errno-h-for-OHOS.patch

# 3) 配置编译器（djbdns 用 conf-cc/conf-ld/conf-home 文件）
echo 'clang -O2 -Wimplicit -Wunused -Wcomment -Wchar-subscripts -Wuninitialized -Wshadow -Wcast-qual -Wcast-align -Wwrite-strings' > conf-cc
echo 'clang' > conf-ld
# conf-home 必须是包私有路径，不能写死 /usr/local（R49/E524、PF6）
echo "$CONAN_PACKAGE_FOLDER/tinydns" > conf-home

# 4) 编译（make prog 构建全部程序，不运行 install）
make prog -j1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ld.lld-15: error: undefined symbol: errno` | 上游 `error.h` 有 `extern int errno;`：该声明把 `errno` 绑定为普通外部符号，与 libc 把 `errno` 实现为 TLS 的事实冲突。OHOS/musl 下表现为「无符号导出」，glibc 下实测同样失败（`ld: errno: TLS definition in libc.so.6 section .tbss mismatches non-TLS reference in buffer.a(buffer_put.o)`）——即**非 OHOS 专属**，任何 TLS errno 的 libc 都会触发 | 补丁移除 `extern int errno;`，在 `error.h` 添加 `#include <errno.h>` |
| 2 | 上游默认目标 `it` 运行 `make install` 需要 root | `it: prog install instcheck`，install 目标执行 `./install` 需要 root 权限 | conanfile 使用 `make prog` 仅构建，不安装；package() 手动拷贝二进制 |
| 3 | 无 configure 脚本，编译器由 conf-cc/conf-ld 控制 | djbdns 自定义构建系统，不支持标准 ./configure | conanfile build() 中动态写入 conf-cc/conf-ld 使用 Conan 提供的交叉编译器（R33） |

## 源码修改（R6 track-edit 已记录）
- `error.h`：移除 `extern int errno;`，添加 `#include <errno.h>`

## 依赖版本
- 无外部依赖（纯 C，仅 libc sockets）

## 上游测试清点（R51 申报）
- **上游测试数：0（上游确无测试）**
- 清点证据（djbdns-1.05 纯净上游解包后）：
  - 目录清单：无 `tests/`、`test/` 目录（`find . -maxdepth 2 -type d -name "test*"` 为空）
  - 无 autotools 测试机制（无 configure.ac / Makefile.am / configure）
  - **Makefile 确实存在 `check` / `instcheck` 目标，但它们不是功能测试用例**（实测）：
    - `Makefile:193` → `check: it instcheck` + `./instcheck`
    - `Makefile:46` → `it: prog install instcheck`
    - `Makefile:529` → `instcheck: load instcheck.o hier.o auto_home.o buffer.a unix.a byte.a`
    - 因此 `make check` 展开为 `make prog` + **`make install`** + `./instcheck`；
      `make install` 执行 `./install` 写入系统前缀 `/usr/local`，**需要 root**，CI 与普通用户均无法运行
    - `instcheck` 源码（`instcheck.c`）只 `stat()` 已安装文件并核对 uid/gid/mode
      （`perm()` + `FATAL "instcheck: fatal: "`），是**安装结果校验器**，不产出可计数的功能测试用例
    - 同目录另有 `cachetest.c`（`cache.h` 的手工调试程序，无 Makefile 规则挂载，不参与 `check`）
      与 `rts.tests`（root/账号前置条件清单文档，非测试代码）
- **结论：上游可运行的功能测试用例数 N=0 成立**，但原因是「唯一的 `check` 目标需 root 且仅校验安装权限，
  无测试套件」，而非「Makefile 无 check 目标」；已按实测更正此前表述。

## 验证结果（二进制功能测试，本地真实执行 + CI 执行）
`test_package/test_tinydns.sh` 在真实二进制上执行，断言落在真实制品上：

```bash
# 1) tinydns-data 把 .data 编译成真实 CDB
$ printf '&example.com:127.0.0.1\n' > data && tinydns-data
# data.cdb = 2175 字节；CDB magic = 5f08（真实 cdb_make 头）

# 2) tinydns-get 把记录从该 CDB 读回（注意参数顺序是 <type> <name>）
$ tinydns-get a example.com
1 example.com:
62 bytes, 1+0+1+1 records, response, noerror
query: 1 example.com
authority: example.com 259200 NS ns.example.com
additional: ns.example.com 259200 A 127.0.0.1

# 3) 反向参数必须被拒绝（CLI 契约）
$ tinydns-get example.com a
tinydns-get: usage: tinydns-get type name [ip]
# exit=100
```

### 本地取证与结论

| 事实 | 证据 |
|------|------|
| 上游源与配方 sha256 一致 | 下载 `djbdns-1.05.tar.gz` 实测 `3ccd826a…36b48`，与 `manifest.yaml` 登记值相同 |
| `tinydns-get` 参数顺序为 `<type> <name>` | `tinydns-get.c:22` usage 字符串 + 实测反序参数 exit=100 |
| `.data` 中 `=` 只委派区域、**不产生可回查的 A 记录** | 实测 `=example.com:127.0.0.1` 编译后 `tinydns-get a example.com` 无 answer 行；`&` 才有 |
| 缺失域名应无 answer（负向对照） | 实测 `tinydns-get a nosuch-name.invalid` 仅输出 `1 nosuch-name.invalid:` |
| 补丁确有必要（非装饰） | 不打补丁直接 `make prog` → exit=2，报 `ld: errno: TLS definition ... mismatches non-TLS reference in buffer.a(buffer_put.o)`，且 `tinydns`/`tinydns-data`/`tinydns-get` **均未生成**；打补丁后 exit=0，5 个二进制齐备 |
| 测试非空壳（变异验证 3 项全部被杀死） | ① 隐藏 `tinydns-get` → `ERROR: tinydns-get not found on PATH (package incomplete)` exit=1；② 让 CDB 真正持有 `10.0.0.1`（数据源改 `&example.com:10.0.0.1`，`tinydns-data` 真实产出合法 CDB）→ `ERROR: tinydns-get did not return the A record 127.0.0.1 we compiled into the CDB` exit=1；③ 用桩 `tinydns-data` 产出**同尺寸但非 CDB**的 2175 字节垃圾文件 → `ERROR: data.cdb is not a real CDB (magic=4141, want 5f08)` exit=1（证明 magic 断言无法被"文件存在+非空"蒙混） |
| 断言密度 | `test_tinydns.sh` 实测 14 处 `fail` 断言（12 处 `\|\| fail` + 2 处 `if ... fail`），非三两行空壳 |

> 说明：本地取证环境为 WSL2 Ubuntu x86_64（djbdns 1.05 为 K&R C，OHOS 交叉 clang 缺 `sys/mman.h`，
> 故仅用其做行为取证）；**CI 侧仍以 OHOS aarch64 真实产物执行为准**。


## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Makefile 构建配方，package_type=application，无 requires |
| conandata.yml | 官方源（cr.yp.to）+ sha256，补丁列表 |
| test_package/ | R34 实质冒烟（执行 tinydns-data 生成 CDB） |
| commands.json | R38 工具声明（软件级） |
| patches/ | 由 finish refresh-patch --auto 固化源码修改 |

## 注意事项
- 二进制为 PIE ELF（`file` 显示 shared object，OHOS 平台 ET_DYN 可执行，正常）。
- 上游发行物为 djbdns-1.05 套件（含 dnscache, axfrdns, rbldns 等），本包仅交付 tinydns 家族 5 个二进制，构建过程完整构建全套（不裁剪软件功能），仅打包边界限定为 tinydns 组件。
- 无 `--version`/`--help` 选项（djb 程序特性），L2 smoke test 会 warn 但不阻塞。

## 编译结束
**最终状态**: published