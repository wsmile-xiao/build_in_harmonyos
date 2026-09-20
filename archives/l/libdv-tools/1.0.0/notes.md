# libdv-tools 1.0.0 适配笔记

## 编译环境
- 构建系统: autotools (configure + make，**不**重新生成 configure)
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 依赖: popt/1.16 (静态), 静态 libdv.a (本包内构建)

## 本包与库包的分工

| 归档 | 交付物 |
|------|--------|
| archives/l/libdv/1.0.0-r8 | libdv.a/.so、libdv/*.h、libdv.pc |
| archives/l/libdv-tools/1.0.0 | bin/encodedv、bin/dubdv、bin/dvconnect |

package() 里删掉 include/ lib/ share/，保证同一个文件只有一个属主。

## 关键问题

| # | 问题 | 根因 | 处理 |
|---|------|------|------|
| 1 | configure 报 "machine `aarch64' not recognized" | 随包 config.sub 是 2005-12-11 版，CPU 表无 aarch64 | 补丁 0002 补 aarch64/arm64 CPU 规则 + linux-ohos* KERNEL-OS 规则（+29 行，不整份替换） |
| 2 | config.guess 报 "cannot guess build type" | 同一份 2005 脚本，且 OHOS 的 uname -s 是 HarmonyOS，case 表无分支命中 | 补丁 0001 插入 *:HarmonyOS:*:* 分支，输出 aarch64-unknown-linux-ohos（+10 行） |
| 3 | 补丁与库包 1.0.0-r8 的 patches 不通用 | 库包那份是针对另一份 config.guess/config.sub 生成的 | 本包按自己下载的上游 tarball 重新生成补丁 |
| 4 | encodedv 无参数段错误（退出码 139） | configure 里 popt 是 AC_CHECK_LIB 探测，缺失只 WARN；没定义 HAVE_LIBPOPT 时工具走空选项表 | requires popt/1.16 + configure 后断言 config.h 里是 `#define HAVE_LIBPOPT`（`/* #undef HAVE_LIBPOPT */` 也含宏名，不能当判据） |
| 5 | config.status 临时目录不可写 | configure 用 umask 077 && mktemp -d ./confXXXXXX，HMDFS 忽略 chmod | build() 里把 configure 两处改成 umask 000 + mkdir -p $TMPDIR/conf$$ |
| 6 | X/GTK/Xv 在鸿蒙不可用 | 默认开启 playdv 的显示后端 | --without-x --disable-gtk --disable-xv |
| 7 | IDCT 汇编不兼容 | 内联汇编只针对 x86 | --disable-asm |
| 8 | 工具运行期找不到 libdv.so | 默认构建 .so，tools 包会删掉 lib/ | --disable-shared --enable-static |

## 构建步骤

1. `get()` 下载 libdv-1.0.0.tar.gz（sha256 已固定）并应用 0001/0002 补丁
2. 改写 configure 里两处临时目录逻辑（strict=False，找不到就跳过）
3. `./configure --disable-shared --enable-static --without-x --disable-gtk --disable-xv --disable-asm`
4. 断言 `config.h` 里有 HAVE_LIBPOPT
5. `make -j2`
6. `make install DESTDIR=<package_folder>`，删除 include/ lib/ share/
7. ELF 自签名（llvm-objcopy 去掉旧 .codesign + binary-sign-tool selfSign）
8. 断言 bin/encodedv、bin/dubdv、bin/dvconnect 都存在

## 验证方式

- `ohc-run.py conan-verify libdv-tools 1.0.0`：G0-G4 / L2 / L4 / L5
- `test_package/test.sh`：encodedv --version/--help（并检查 help 里列出
  --start-frame/--end-frame/--encode-passes 证明 popt 选项表真的接上了）、
  dubdv --help、三个工具无参数调用不得死于信号（popt 缺失时是 139）、
  未知选项必须被拒

## 未决 / 注意

- 上游没有测试套件（make check 为空），test_package 是本包唯一的自动化验证
- dvconnect 需要 IEEE1394 设备，鸿蒙上没有实际用途，但仍然随包交付（上游 bin_PROGRAMS）
- 本包不安装 man 页（share/ 整目录删除，与库包归口一致）