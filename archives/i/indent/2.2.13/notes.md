# indent 2.2.13 适配笔记（GLM-32，2026-09-15 夜跑）

## 编译环境

- 构建系统: autotools（自带 configure；config/config.sub 为 2.x 重构版）
- 编译日期: 2026-09-15
- 编译器: clang/clang++（OHOS 15.0.4，aarch64）
- 状态: built（探索全流程验证：configure/make/install/regression 全过；
  conan-verify 于配方完成后执行）
- Conan 2.29.1（OHOS 适配版），profile ci/conan/profiles/ohos-aarch64

## 编译步骤（探索实测，固化为配方）

```bash
./configure --prefix=<pkg> \
  --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos \
  --disable-nls
make -j1 MAKEINFO=true
cd regression && sh ./TEST    # 上游回归套件：125 用例全过
```

## 踩坑与解决（时间线）

1. **`OS 'ohos' not recognized`**：config/config.sub 的 KERNEL-OS 列表
   无 ohos（与 osip/mifluz 同族）。解决：os 验证段加 `ohos* |`、
   kernel-os 段加 `linux-ohos*`（0003 补丁，+2/-2）。
2. **`subs1.awk: Permission denied`**（E011）：configure/config.status 的
   umask 077 临时目录在 HMDFS 不可写 → umask 022（0004 补丁）。
3. **`undefined symbol: bindtextdomain/textdomain`**：OHOS musl 无
   libintl，`--disable-nls` 只停链接不消引用——src/indent.c 的
   bindtextdomain/textdomain 两行调用无编译守卫（上游 indent.h 已给
   _(X) 定义 ENABLE_NLS/非 NLS 两分支，唯漏这两行）。解决：+2 行
   `#if defined (ENABLE_NLS)` 守卫（0005 补丁，风格与同函数的
   HAVE_SETLOCALE 守卫一致）。
4. **`texinfo2man: Error 127`**：man/ 目录的 man 页生成工具
   （编译后立即执行的本地小工具）在 HMDFS 上无法执行（新建二进制
   执行限制族，同 mifluzsearch）。解决：补丁将顶层 Makefile.am 与
   Makefile.in 的 SUBDIRS 去掉 doc/man（0001/0002，文档与 man 页
   非交付物核心；Makefile.in 同步改避免触发 automake 重建，osip
   0004 同教训）。
5. **makeinfo 缺失**：doc 构建以 MAKEINFO=true 占位（doc 已从
   SUBDIRS 移除，此项为双保险）。

5. **`cd: regression: No such file or directory`**（conan create 干净构建）：
   上游 regression/Makefile 是 tarball 自带的静态文件、不在 AC_CONFIG_FILES，
   out-of-tree 构建不会把它生成到构建目录，make all-recursive 递归 cd 必败。
   解决：0001/0002 补丁将 SUBDIRS 收敛为 `src po`（与第 4 条 doc/man 一并处理），
   配方 build() 将 regression/ 原样复制（keep_path=True 保留 input/ 子目录结构）
   进构建目录后执行官方 TEST——`INDENT=../src/indent` 恰好指向构建产物。
6. **TEST 执行需要签名**（E077/§12.14）：构建产物 indent 未签名在设备被拒。
   配方内置 _sign_binary：llvm-objcopy 删 .codesign 占位段 → binary-sign-tool
   selfSign；签名器调用必须 `env -u LD_LIBRARY_PATH`（conan 注入的 SDK
   LD_LIBRARY_PATH 会击毙签名器，exit 127）。签名后 125 用例全过
   （"Regression test successfully completed"）。

**conan-verify**：2026-09-17 03:0x 第 5 轮通过（G0-G4 全绿，前四轮失败即
上述第 5/6 条的定位过程）。CONAN_HOME=~/tmp/ch/home-glm32-indent。

## 上游测试四维账本（与 manifest.yaml / PR 正文 / test_package/MANIFEST.yml 同源）

| 维度 | 数值 | 说明 |
|------|------|------|
| N_static（静态注册） | 125 | regression/input/ 下 125 个用例，由 regression/TEST 脚本驱动（未注册 autotools TESTS 变量，脚本驱动为上游设计） |
| 通过 | 125 | 真机执行 "Regression test successfully completed"（对比 standard/ 期望输出） |
| 失败/跳过 | 0 | make check 的 man 子目录入口阻塞属 HMDFS 执行限制，非测试失败；回归套件已独立完整执行 |
| N_consumer（新增消费者） | 1 | test_package：运行打包后 indent 二进制格式化 sample.c，断言输出含 main()/printf() |

## 路径 B 判断

判断不成立，按纯路径 A 申报。依据：config.sub ohos 识别、umask 022、
ENABLE_NLS 守卫三类修复均为已有知识/归档先例（E011、osip、mifluz 同模式）
的组合应用，无新的跨仓库可复用知识增量。

## 遗留与限制

- doc/（texinfo 文档）与 man 页不在交付范围（SUBDIRS 已裁剪，工具链
  makeinfo/texinfo2man 在 HMDFS 不可用）
- 消费者测试对输出内容断言 main()/printf()；indent 的具体格式化风格
  参数由上游回归套件覆盖
---

**编译结束**: 2026-09-17 03:17
**最终状态**: built
