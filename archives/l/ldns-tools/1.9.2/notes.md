# ldns-tools 1.9.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4
- 依赖: openssl/3.5.6（静态链接）

## 本包与库包的分工

| 归档 | 交付物 |
|------|--------|
| archives/l/ldns | libldns.a / .so、ldns/*.h、ldns.pc |
| archives/l/ldns-tools/1.9.2 | bin/drill、bin/ldns-* 系列 |

`package()` 只调用 `make install-drill install-examples DESTDIR=<pkg>`，
再防御性删掉 `include/ lib/`，保证同一个文件只有一个属主。

## 关键问题

| # | 问题 | 根因 | 处理 |
|---|------|------|------|
| 1 | `configure` 报 `cannot guess build type; you must specify one` | 自带的 `config.guess`（timestamp 2026-05-17）只认 `aarch64:Linux:*` | 补丁 0001 补 `aarch64:HarmonyOS:*` 分支，写成 `echo ...; exit 0` 自终止 |
| 2 | 补 0001 后仍报 `Invalid configuration ... aarch64-harmonyos-linux-gnu` | `config.sub` 不认 ohos 三元组 | 补丁 0002 补 3 处 ohos 规则 |
| 3 | `config.status` 报 `can't create ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 忽略 chmod，`umask 077 && mktemp -d` 建的目录随后不可写 | `build()` 用 `replace_in_file()` 把 `configure` 的两处临时目录创建改成 `umask 000 && mkdir -p $TMPDIR/conf$$` |
| 4 | 聚合 `make install` 把 470+ 个 `ldns_*.3` man3 页也装进来 | ldns 的库/工具分割只存在于安装目标层，聚合 install 会带 `install-manpages` | `package()` 只调用 `install-drill install-examples` |
| 5 | L2 冒烟 | `drill` 是 getopt 不是 getopt_long，`--version`/`--help` 落到未知选项分支 | 同工程 `examples/ldns-version` 忽略 argv 直接打印版本，L2 由它通过，无需补丁 |
| 6 | 新二进制无法执行 | 鸿蒙要求 ELF 带 `.codesign` | `package()` 内 `llvm-objcopy` + `binary-sign-tool` 自签名 |

## 构建步骤

1. `get()` 下载 `ldns-1.9.2.tar.gz`（sha256 `b524fa21...`），`source()` 里打补丁 0001/0002
2. `configure --enable-static --disable-shared --with-drill --with-examples
   --without-pyldns --with-ssl=<openssl/3.5.6>`
3. `make -j2`
4. `make install-drill install-examples DESTDIR=<package_folder>`
5. 删掉 `include/ lib/`，ELF 自签名

## 验证方式

- `ohc-run.py conan-verify ldns-tools 1.9.2`：G0-G4 / L2 / L4 / L5 全绿
- `test_package/test.sh`：构造一个不换行的假源地址做基准，断言
  1. `drill`、`ldns-read-zone`、`ldns-version`、`ldns-keygen`、`ldns-notify` 五个工具都在 PATH 上
  2. `drill -v` 与 `ldns-version` 的输出里带版本号且退出 0
  3. `ldns-read-zone` 能解析内嵌区域文件（SOA、NS 胶水地址、`$ORIGIN` 展开）
  4. 缺失的区域文件必须非 0 退出

## 未决 / 注意

- 上游没有 `make check` 目标，`test_package` 是本包唯一的自动化验证
- `--without-pyldns` 关掉 SWIG 绑定：它们不属于命令行工具，且需要额外工具链
- 工具是静态链接的，`readelf -d` 里不应出现 `libldns.so` / `libssl.so`