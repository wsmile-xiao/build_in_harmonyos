# chiark-utils 8.0.1 适配笔记

## 编译环境
- 构建系统: makefile(裸 Makefile,无 configure)
- 编译日期: 2026-09-08
- 编译器: clang 15(/data/service/hnp/bin/clang,经 make CC= 注入)
- 状态: built(conan create 成功,含 test_package)

## 编译步骤

无 configure 步骤。conanfile.py 的 build() 直接驱动上游 cprogs/Makefile:

```bash
cd cprogs && make CC="/data/service/hnp/bin/clang" \
  CMDLINE_CPPFLAGS='<各依赖包 include 路径>' \
  CMDLINE_CFLAGS='-Dgettext(x)=x' \
  CMDLINE_LDFLAGS='<各依赖包 lib 路径>' -j1
```

依赖路径经上游原生钩子 CMDLINE_CPPFLAGS/CMDLINE_LDFLAGS 注入(settings.make 支持),
不修改 Makefile 本身。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create 报 Error -11(SIGSEGV),无任何编译输出 | generate() 中 save_script("conanbuild") 与 Conan 自身聚合启动脚本同名,conanbuild.sh 变成 source 自己 -> 无限递归栈溢出 | 删除自定义 env 脚本;编译器在 build() 里从 self.conf 读出后直接拼进 make 命令行 |
| 2 | summer/watershed/prefork* 等 5 程序编译失败:`_()` 宏隐式声明 | OHOS musl 的 <libintl.h> 是空壳头,不声明 gettext();上游 `#define _(x) gettext(x)` 展开成隐式函数 | CMDLINE_CFLAGS 注入恒等宏 `-D'gettext(x)=x'`(英文消息,与 musl 默认一致),零源码补丁 |
| 3 | xbatmon-simple 编译失败: X11/Xlib.h:44 找不到 X11/X.h | xorgproto 被传递依赖以 visible=False 引用,其 include 目录不进 cpp_info 聚合,裸 Makefile 直连注入拿不到 | requirements() 显式 `requires("xorgproto/2025.1", force=True)` |
| 4 | package() 打包后 bin/ 为空 | basic_layout 下裸 Makefile 在 source_folder 原地编译(源码被 Conan 复制到 build 根目录),产物不在 build-release/ | package() 从 self.source_folder/cprogs 取产物 |
| 5 | CMDLINE_CFLAGS 含 `(` 报 sh syntax error | make 变量经外层 shell 展开时引号被剥掉,-D'gettext(x)=x' 的括号裸露 | 嵌套引号: 外层双引号 + 内层单引号,让单引号存活到 make recipe 行 |
| 6 | libxmu/1.3.1 裸引用在远端找不到 | 依赖包必须以 plain name/version(无 user/channel)构建发布才能被下游裸引用解析 | libxmu 以裸引用本地 conan create 进缓存;后经 W3 实证 libxmu 根本未发布制品仓(见产物清单说明),按 R36 剔除其唯一消费者 xduplic-copier 并用 make 命令行 PROGRAMS 覆盖 |

## 源码修改

无补丁(patches_applied: [])。所有适配均通过 Conan 配方层完成:
gettext 恒等宏、依赖路径注入、程序清单裁剪决策均不改上游源文件。

上游 acctdump 的条件构建(sys/acct.h 探测)在 OHOS 上天然可用,保留了上游机制。

## 依赖版本

- nettle/3.10.2.1(已发布)
- gmp/6.3.0(已发布)
- libx11/1.8.13(已发布)
- libxmu/1.3.1(配方在 main,本次以裸引用本地验证)
- libuv/1.52.1(已发布)
- xorgproto/2025.1(已发布)

## 产物清单(bin/ 10 + sbin/ 2)

readbuffer writebuffer with-lock-ex xbatmon-simple summer watershed
rcopy-repeatedly prefork-interp cgi-fcgi-interp acctdump + sbin: trivsoundd really

`xduplic-copier` 已剔除: 它是唯一需要 libxmu/1.3.1 的程序, 而 libxmu 虽然
PR 已合入 main(0c88831c90, 2026-09-04), 但制品仓 `conan list "libxmu/*" -r=ohpcd`
返回 0 条配方 —— 真未发布(同期合入的 libxi/libxext/boost1.84-wave 均已在仓,
排除流水线全局故障)。按 R36 剔除该程序, 待 libxmu 发布后在 8.0.1.1 补回。
libxmu 未出现在依赖列表中(不在 requirements())。

`acctdump` 由 make 命令行 PROGRAMS 覆盖显式包含 —— 命令行赋值会抑制上游
Makefile 的条件 `PROGRAMS+=acctdump`, 故必须显式列出(它无需外部依赖, 实测可构建)。

`really` 上游为 SUID 安装(-m 4774);OHOS 打包按普通二进制处理,不设 SUID 位。
软件级 commands.json 已按 R38 创建(archives/c/chiark-utils/commands.json)。

## 验证结果

```bash
# conan create 全流程通过(含 test_package)
# test() 真实执行(R34):
#   with-lock-ex -w test.lock sh -c 'cat lockproof.txt'  => locked-ok,锁真实生效
#   echo sumfile.txt | summer => 校验和输出含文件名与哈希列
# 冒烟: 12 个二进制全部可执行并输出 usage/预期行为
# file: ELF arm64, dynamic (/lib/ld-musl-aarch64.so.1)
```

## 上游测试申报(R51)

上游无 make check 目标(cprogs/Makefile 无 test/check 规则)。唯一测试
cprogs/really.testcases 为 Perl 驱动的 setuid 用例,需 root、/etc/inittab、
/etc/rc.local、专用用户 testac —— CI/worker 无 Perl 工具链且无 root,
不可运行,已在 test_package/MANIFEST.yml 如实申报。
---

**编译结束**: 2026-09-08 16:01
**最终状态**: built
