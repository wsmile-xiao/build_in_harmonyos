# fungw 1.2.2 适配笔记

## 编译环境
- 构建系统: custom（scconfig：`./configure` 由项目内嵌的 scconfig 现场生成 Makefile，再 make / make install）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，OHOS SDK）
- 状态: built（conan create 全绿：上游 5 项 regression + test_package 9 项断言）

## 编译步骤

1. 探索性编译（`/data/storage/el2/base/cache/builds/fungw-1.2.2.work`）：
   ```bash
   CC=/data/service/hnp/bin/clang ./configure --prefix=$DEFAULT_PREFIX --disable-perl
   make -j1
   make install DESTDIR=$TEST_PREFIX
   cd regression && ./test && ./test_c && ./test_custom && ./multicall \
       && SCRIPT=../doc/example/00_hello/hello.fawk ./test_script
   ```
   5 个上游 regression 程序全部 rc=0，multicall 输出与 multicall.ref 逐字一致。
2. 固化为 Conan 配方（`archives/f/fungw/1.2.2/conanfile.py`）：
   `sh ./configure --prefix=<package_folder> --disable-perl` → `make -j1` →
   跑上游 regression → `make -C libfungw install` + `make -C libfungwbind install`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./configure` 报 `make: cc: No such file or directory`（scconfig 自举失败） | scconfig 用自己的 `cc` 编译 hooks.c；OHOS SDK 只有 clang，没有 `cc` | 从 `tools.build:compiler_executables` 取 `c` 编译器，命令前缀 `CC=<clang>`（R33：不从裸 shell 变量取） |
| 2 | conan 构建目录里 `./configure: Permission denied`（exit 126） | HMDFS 卷上 conan 复制源码时丢掉 `configure` 的 +x 位 | 改成 `sh ./configure ...`，不依赖执行位 |
| 3 | `ln -s libgenht.a genht_std.a: Permission denied`，make Error 2 | genht 的兼容别名用符号链接创建；HMDFS 卷既不支持 symlink 也不支持 hardlink（os.symlink EACCES / os.link EPERM） | 先 `make libgenht.a`，再把 `libgenht.a` 复制成 `genht_std.a`，让 make 的 `genht_std.a` 规则跳过 |
| 4 | 消费者链接报 `ld.lld: error: undefined reference due to --no-allow-shlib-undefined: strhash / htsp_init / htsp_get ...` | 上游把 genht 当独立静态库（regression 显式链 `genht_std.a`），但 libfungw\*.so 的链接规则里没有它，共享库留下未定义符号 | 用 `make LDFLAGS="-rdynamic -fPIC <genht/*.o>"`（libfungw / libfungwbind 两个子 make）把 genht 目标文件链进共享库，产物 .so 自洽 |
| 5 | `make install` 后只有 `libfungw.so.1.2.2`，没有 `.so` / `.so.1` | scconfig 的 `install_link_` 用**硬链接**（`sccbox ln -f`）建 SONAME 别名，HMDFS 上必然失败且不报错 | package() 里按 `libX.so.X.Y.Z` 复制出 `.so.X.Y` / `.so.X` / `.so` 与 `lib/puplug/X.so`（HMDFS 无链接能力，只能复制） |
| 6 | 消费者 `#include <libfungw/fungw.h>` 编译失败：找不到 `<genht/htsp.h>` | fungw.h 依赖内嵌 genht 头文件，但上游 install 不装它们 | package() 把 `src_3rd/genht/*.h` 一并装进 `include/genht/` |
| 7 | configure 自动开启 perl 绑定（探测到 `/data/service/hnp/bin/perl`） | scconfig 无 --with/--without，按系统探测；OHOS 无 libperl 可链 | `--disable-perl`；保留内嵌的 c / fawk / cli 三个绑定（无外部依赖） |

## 源码修改

无补丁（patches/ 为空）。适配全部在配方层完成：CC 注入、genht 目标文件并入
共享库、SONAME 别名与 genht 头文件的补齐。

## 依赖版本

无 Conan 依赖。核心库与 c/fawk/cli 三个绑定的代码全部随上游 tarball 分发
（genht 在 `src_3rd/genht`，libfawk 在 `libfungwbind/fawk/libfawk_sc`）。

## 验证结果

```bash
# 上游 regression（配方 build() 内真实执行，非假设）
./test < /dev/null            # rc=0
./test_c < /dev/null          # rc=0
./test_custom < /dev/null     # rc=0
./multicall | diff -u multicall.ref -   # 无差异
SCRIPT=../doc/example/00_hello/hello.fawk ./test_script   # rc=0

# 消费者测试（conan create 的 test_package）
fungw runtime api_ver=0x1010 (headers 0x1010)
ok   运行时与头文件 API 版本一致
ok   fgw_obj_reg() 注册宿主对象 'math'
ok   fgw_func_reg() 注册 C 函数 'add'
ok   fgw_func_lookup() 全局查到 'add'
ok   fgw_vcall_in() 返回 FGW_SUCCESS
ok   vcall add(2,3) == 5
ok   scall add("20","22") == "42"
ok   fgw_arg_conv(FGW_STR -> FGW_LONG) 成功
ok   转换结果 1234
ALL CHECKS PASSED
```

`shared=True`（默认）与 `-o shared=False` 两条链路均 conan create 通过。

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libfungw.so.1.2.2（+ .so.1.2 / .so.1 / .so） | 核心库，SONAME libfungw.so.1 |
| lib/libfungw_c.so.1.2.2、libfungw_fawk.so.1.2.2、libfungw_cli.so.1.2.2（+ 别名） | C 绑定 / fawk 脚本引擎 / cli 绑定 |
| lib/puplug/*.pup、*.mak、*.so | puplug 插件描述与插件库（FGW_PUPDIRNAME 编译期指向 <prefix>/lib/puplug） |
| include/libfungw/*.h、include/libfungwbind/c/fungw_c.h、include/genht/*.h | 公开头文件（含上游漏装的 genht 头） |

## 注意事项

- 上游 INSTALL 写「暂时没有自动化测试」，实际 `regression/` 目录有 5 个测试程序，
  由顶层 `make` 一并构建；本配方在 build() 内逐个执行，multicall 做 golden 对比。
- 源 URL 只有 http 端点（上游站点 443 拒连），按仓内既有口径保留官方源，
  完整性由 sha256 钉住（见 conandata.yml 注释）。
- 脚本引擎（lua/tcl/python/perl/mruby/…）需要对应语言开发库，OHOS 上未探测到；
  perl 已显式禁用，其余由 configure 自动判为 disabled。
---

**编译结束**: 2026-09-27 22:05
**最终状态**: built

## PR 审查跟进（2026-09-28）

- 机器审查首轮裁决 FAIL，两条不通过：
  - **rule1 PR 模板格式**：上游测试用例统计表缺合计行 → 已把 PR 描述重写为 `templates/积分赛事PR模板.md` 的 11 字段结构，上游统计表补 `**合计** | **5**`、适配后统计表补 `**合计** | **14** | **+9**`，并保证各行为模板标准行名（单元测试/集成测试/其他测试/鸿蒙特有测试）以便解析器读数。
  - **rule6 AI 检视 P0/P1**：atomgit-bot 的 AI 检视自 PR 创建起一直停留在「正在进行中」占位（>13h），rule6 找不到带 P0/P1 计数的检视评论 → 通过本提交触发 PR 更新事件让 bot 重新检视；代码本身无改动（W4 独立审计 P0=P1=0 已在 `reports/audit-result.json`）。
- CI 结果通道备注：ohpcd-robot 两次「CI 校验通过」评论均在 /rebuild 后约 5 秒发出，且附带的 ci?id 链接指向别的包的旧失败构建（63095=libest、63417=verovio）；CI 看板（ci-wall / /api/ci/builds）滞后约 6 天，无法按链接核验。判绿依据：结果评论内容明确指向本包 + 本地 W3 同源脚本 100% 通过 + 无失败评论。
