# wrapsrv 1.0.0 适配笔记

## 编译环境
- 构建系统: makefile（单文件 C，无 configure/autotools）
- 编译日期: 2026-10-01
- 编译器: clang 15（`/opt/lpk-fixed/clang`，target `aarch64-linux-ohos`），CI 侧为 `/data/service/hnp/bin/clang`
- 状态: built（`commands.json` 声明 `binary=false`，故制品上传前只能是 `built`，
  与 `manifest.yaml` 的 `status: built` 一致；R29 / R52。制品上传后由发布流水线改 `published`）
- 依赖: 无外部依赖（纯 C，仅需 libc）

## 上游信息
- 仓库: https://github.com/farsightsec/wrapsrv
- 发行 tag 名本身就是 `tags/v1.0.0`（该仓库用 `refs/tags/tags/...` 布局）
- 源码 URL: `https://github.com/farsightsec/wrapsrv/archive/refs/tags/tags/v1.0.0.tar.gz`
- sha256: `df317fe09be9e00816453676114cdb7573420b7e1082eec1a74f780421520b23`
- 解包根目录: `wrapsrv-tags-v1.0.0`
- 许可证: Apache-2.0（`COPYRIGHT` + `LICENSE`）
- 功能: 按 DNS SRV 记录（RFC 2782）做加权优先级选择，把命令行里的 `%h` / `%p`
  替换成目标主机名与端口后执行；用于给本身不支持 SRV 的命令加上 SRV 能力。

## 编译步骤（配方等价命令）
```bash
tar xzf v1.0.0.tar.gz && cd wrapsrv-tags-v1.0.0
patch -p1 < patches/0001-replace-ns_name_ntop-with-portable-wire-name-renderer.patch
make CC=<conan tools.build:compiler_executables.c> LDFLAGS=
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ld.lld-15: error: undefined symbol: ns_name_ntop` | 上游 `wrapsrv.c` 调用 BIND 的 `ns_name_ntop()` 做「wire 格式域名 → 文本域名」转换。OHOS 的 musl libc **在 `<arpa/nameser.h>` 里声明了它，但没有实现**（实测 `llvm-nm` 扫 `libc.a`：`ns_initparse`、`ns_parserr`、`ns_name_uncompress`、`dn_expand`、`dn_skipname`、`res_query`、`res_init` 都在，唯独没有 `ns_name_ntop`；OHOS 只有 `ns_name_uncompress()` 这一族）。glibc/macOS 自带 BIND libresolv 所以上游没遇到过 | 补丁 0001 在树内实现一个只依赖 RFC 1035 线格式本身的 `wire_name_ntop()`，替换调用点。不含任何平台宏（PF5/R8 合规），在 glibc 上语义等价 |
| 2 | `make` 默认目标会因 `LDFLAGS = -lresolv` 链接失败 | OHOS **完全没有 libresolv**（sysroot `find -name '*resolv*'` 为空）；resolver 全部在 libc 里 | 配方里 `make CC=<cc> LDFLAGS=` 覆盖掉；不丢功能，因为 `res_query()`/`ns_parserr()` 本来就是 libc 符号 |
| 3 | 上游 Makefile 写死 `CC = gcc` | 无 configure，构建期无法探测交叉编译器 | 配方从 `self.conf["tools.build:compiler_executables"]["c"]` 取编译器再传给 make（R33，不裸用 `${CC}`） |
| 4 | 上游无 `--version` / `--help` | `usage()` 只在 `argc < 3` 时触发，所有路径都 `exit(EXIT_FAILURE)` | 不伪造版本选项；测试改为断言 usage 文本 + 退出码（L2 smoke 会 warn，不阻塞） |

### 补丁 0001 要点
```c
static int
wire_name_ntop(const unsigned char *name, char *buf, size_t buflen) { ... }
```
- 逐 label 走长度字节，超过 `NS_MAXLABEL` 报错；
- 遇到 `0xc0` 压缩指针时按「指向更早位置」校验并跳转（同时天然给出循环上界），
  这是 RFC 1035 对压缩指针的唯一约束；
- 末尾分隔点去掉，根域名输出 `.`，返回值与 BIND 的 `ns_name_ntop()` 语义一致；
- 缓冲区按 `buflen` 逐段检查（实际判据是 `len + 2 * label + 2 > buflen` 即失败，
  系数 2 是给 `.` 与 `\` 的最坏转义留位），不会溢出
  `target_name()` 里的 `char buf[NS_MAXDNAME]`。

> SRV rdata 的 target 按 RFC 1035 §4.1.4 / RFC 2782 **不允许压缩**，所以真实场景走的是
> 非压缩分支；压缩分支属于防御性实现（上游把 `ns_rr_rdata()` 的裸指针直接当
> `ns_name *` 传入，本身也没有可用的报文基址）。

## 依赖版本
- 无（`requires` / `tool_requires` 均为空）

## 上游测试清点（R51 申报）
- **上游测试数：0（上游确无测试）**
- 清点证据（纯净上游 tarball 解包后）：
  - 文件清单（9 个）：`.gitignore` `COPYRIGHT` `LICENSE` `Makefile` `README.md`
    `list.h` `wrapsrv.1` `wrapsrv.c` `wrapsrv.docbook`
  - 无 `tests/` `test/` 目录（`find -type d -iname '*test*'` 命中 0）
  - Makefile 目标只有 `all: $(BIN) $(DOC)`、`$(BIN)`、`$(MAN)`、`clean`、`install`
    —— **既无 `check` 也无 `test`**
  - `$(MAN)` 目标跑 `docbook2x-man`，是文档生成（且依赖 tarball 里没有的
    docbook2x 工具链）；`install` 往 `$(DESTDIR)$(PREFIX)/bin` 写文件，需要
    人工指定前缀
- **结论：N=0 成立**。

## 验证结果（本地真实执行 + CI 执行）

`test_package/test_wrapsrv.sh` 在交付二进制上执行，**TOTAL=27 PASS=27 FAIL=0**
（`conan create` 实测输出）。

断言数数法（可复核，非人读）：
`grep -cE '^\s*(t|check) "' test_package/test_wrapsrv.sh` → `t()` 10 处 + `check()` 17 处 = **27**；
下表分组数由 `awk` 按脚本内 `# ── N. …` 节注释归组数出，`2+7+3+2+2+4+5+2 = 27`，与总数自洽。

| 组 | 断言数 | 内容 |
|----|--------|------|
| 0 | 2 | `wrapsrv` 在 PATH 上且可执行 |
| 1 | 7 | 无参 / 单参 / `--help` 均 exit 1 + usage 文本逐字匹配（3 次退出码断言 + 4 次文本断言） |
| 2 | 3 | 单条 SRV：`HOST=primary.example.com PORT=8080` 精确 stdout、exit 0、无占位符残留 |
| 3 | 2 | 行内替换 `x%hy%pz` → `xprimary.example.comy8080z` |
| 4 | 2 | RFC 2782 优先级：应答中 priority-20 记录排在**前面**，仍必须先选 priority-10 |
| 5 | 4 | 命令 exit 1 时按优先级回退到 backup（两次尝试、顺序正确、退出码透传 1） |
| 6 | 5 | NXDOMAIN（rcode 3）与空应答段两条负向路径，均不执行命令（2 次退出码断言 + 3 次诊断/未执行断言） |
| 7 | 2 | 不挂桩、真实 libc resolver 查询 `.invalid` 域名必须失败且有诊断输出 |

### DNS 传输层为什么挂桩（重要，非"假测试"）
`wrapsrv` 的功能 = 「查一次 DNS SRV → 选记录 → 替换 `%h`/`%p` → 执行命令」。
查询那一步在 CI 上不可复现：worker 没有可达 resolver，且非 root 无法在 53 端口
起权威 DNS。因此 `res_stub.c` 被编译成 `LD_PRELOAD` 对象，**只**替换
`res_init()` / `res_query()`，返回逐字节正确的 RFC 1035 应答。`res_query()` 之后
的全部代码都是交付的上游代码：

- `ns_initparse()` / `ns_parserr()` 解析（libc 真实实现）
- SRV rdata 遍历 + `target_name()` → **本 PR 补丁新增的 `wire_name_ntop()`**
- RFC 2782 优先级 + 权重选择（`next_tuple()`）
- `subst_cmd()` 的 `%h`/`%p` 替换
- `do_cmd()` → `system()` 真实执行被替换后的命令行，并透传其退出码

即：**打补丁的那段代码是被真实执行并断言到的**（断言值 `primary.example.com`
只能由正确的 wire→text 转换产生）。另外第 7 组断言完全不打桩，走真实 libc resolver。

### 取证与结论

| 事实 | 证据 |
|------|------|
| 源 URL 与 sha256 与配方一致 | 本地下载 `.../archive/refs/tags/tags/v1.0.0.tar.gz` 实测 `df317fe0…520b23`；经 `codeload.github.com` 与经 `gh-proxy.com` 代理下载三者字节完全相同 |
| 补丁确有必要（非装饰） | 不打补丁直接 `clang ... -o wrapsrv wrapsrv.c` → `ld.lld-15: error: undefined symbol: ns_name_ntop`，无二进制产出；打补丁后 exit 0 |
| 补丁不引入平台宏 | `patches/*.patch` 新增行无 `__OHOS__`（PF5 通过）；新函数只用 RFC 1035 线格式与 `memcpy` |
| 上游告警开关保持开启 | 编译行实测 `-O2 -g -Wall -Wextra -Werror`，零告警 |
| `-lresolv` 确无必要 | sysroot 内 `find -name '*resolv*'` 为空；去掉后 `res_query`/`ns_parserr` 仍由 libc 解析（实测链接通过、运行通过） |
| 产物为 aarch64 ELF 可执行文件 | `llvm-nm` + 直接执行验证；`package()` 交付 `bin/wrapsrv` 与 `share/man/man1/wrapsrv.1` |
| 非空壳测试（变异验证 5 项全部被杀死） | 对照组 `TOTAL=27 PASS=27 FAIL=0`；①删掉 `bin/wrapsrv` → **23 项断言失败，exit 1**；②应答 target 改名 `primary.example.com`→`evil.example.org` → **4 项失败**（`single-srv-stdout` 实测输出 `HOST=evil.example.org PORT=8080`）；③应答端口 `8080`→`1234` → **2 项失败**（`inline-substitution-stdout` 实测 `xprimary.example.comy1234z`）；④把 priority-10 记录改成 priority-30（破坏 RFC 2782 顺序） → **3 项失败**（`priority-order-lowest-prio-first` 实测选出 `backup.example.com:9090`）；⑤把应答 rdlength 改成 4 → **9 项失败**，`single-srv-exit` exit 1（SRV 记录因 `len > 3*NS_INT16SZ` 不成立被跳过）。断言均为精确字节比对与退出码比对，无法用"文件存在/非空"蒙混 |

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Makefile 构建，package_type=application，无 requires；覆盖 CC 与 LDFLAGS |
| conandata.yml | 官方 GitHub tag tarball + sha256，补丁列表 |
| manifest.yaml | 版本级元数据 + 知识沉淀 + 补丁分类 |
| patches/0001-*.patch | `ns_name_ntop` → 树内 RFC 1035 线格式域名渲染器 |
| test_package/test_wrapsrv.sh | 27 项断言的真实功能测试 |
| test_package/res_stub.c | 测试用 DNS 传输层桩（不进入安装产物） |
| test_package/MANIFEST.yml | 上游测试声明（R51）+ 补全测试说明 |
| commands.json | R38 工具声明（软件级，type=tool） |

## 注意事项
- 上游 tag 名带 `tags/` 前缀，`strip_root=True` 仍能正确处理 `wrapsrv-tags-v1.0.0` 根目录。
- 上游 `wrapsrv.1` 是仓库里预先生成的 roff man page（不是 docbook2x 生成物），
  配方直接随包交付，**不**调用 `docbook2x-man`（CI 无该工具链）。
- 无 `--version` 选项，`conan-verify` 的 L2 smoke test 会 warn，不阻塞。
- 补丁不是 OHOS 专属：任何不提供 BIND `ns_name_ntop` 的 libc（musl 系）都需要它，
  glibc 上语义完全等价。

## 编译结束
**最终状态**: built（与 `manifest.yaml` 的 `status: built` 及 MR 描述 补充说明 7 一致；
`binary=false` 表示制品尚未上传，发布流水线上传后才改 `published`）
