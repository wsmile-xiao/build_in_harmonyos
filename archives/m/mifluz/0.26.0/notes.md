# mifluz 0.26.0 适配笔记（GLM-32，2026-09-15 夜跑）

## 编译环境

- 构建系统: autotools（2001 年configure，自带 config.guess/sub 需升级）
- 编译日期: 2026-09-15
- 编译器: clang/clang++（OHOS 15.0.4，aarch64，C++ 用 -std=gnu++98 语义修复 examples）
- 状态: built（conan-verify 通过，见 reports/conan-verify-report.md）
- Conan 2.29.1（OHOS 适配版），profile ci/conan/profiles/ohos-aarch64

## 编译步骤（探索实测，固化为配方）

```bash
export db_cv_uint8="unsigned char" db_cv_uint16="unsigned short" db_cv_int16="short"
export db_cv_uint32="unsigned int" db_cv_int32="int"
export db_cv_align_t="unsigned long long" db_cv_alignp_t="unsigned long long"
export db_cv_mutex="POSIX/pthreads"
./configure --prefix=<pkg> \
  --enable-static --disable-shared \
  --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos
make -j1 MAKEINFO=true
make check            # 见下方测试账本
```

## 踩坑与解决（时间线）

1. **`cannot run test program while cross compiling`**：configure 含 8 个
   AC_TRY_RUN 探测（db_cv_* 定宽类型/指针对齐/互斥实现）。解决：aarch64
   事实值预设缓存变量（Conan Environment scope=build 注入，与 aldo/0.7.8
   的 os.environ 注入同思路但走 conan 官方机制）。
2. **HMDFS FUSE getcwd 拒绝窗**：设备内存压力时段 getcwd 系统调用间歇失败
   （"Not supported"/"Bad file descriptor"），configure 的 `ac_pwd=\`pwd\``
   与 `ls -di .` 双检查失败报 `working directory cannot be determined`。
   解决：build() 内运行时补丁回退 `$PWD`（aldo/0.7.8 同模式），并配合
   gate.sh 择窗。知识 E386 同族。
3. **clang 15 硬错误两类**（gcc 时代为警告）：
   - `search/WordTree.cc:530` `case NOTOK:`（-1 收窄进 unsigned switch）
     → `case (unsigned int)NOTOK:` 显式转换（0009 补丁）；
   - `examples/example1.cc` 15 处多字节 UTF-8 字符塞入 char 字面量
     → 等值十六进制转义（0008 补丁），行为不变。
4. **makeinfo 缺失**：`mifluz.info` Error 127 → `make MAKEINFO=true` 占位
   （文档非库适配范围）。
5. **上游 config.guess 2001 版无法识别 HarmonyOS 宿主** → 升级 + ohos
   triplet（0001/0003 补丁，aalib 同模式）。

## 上游测试四维账本（与 manifest.yaml / PR 正文 / test_package/MANIFEST.yml 同源）

| 维度 | 数值 | 说明 |
|------|------|------|
| N_static（静态注册） | 15 | autotools TESTS：test/ 13 + search/ 1 + examples/ 1 |
| 通过 | 10 | test/ 独立套件 All 10 tests passed（真机） |
| 上游设计 SKIP | 3 | t_cache/t_largefile/t_env（LONG=yes 才跑，上游默认跳过） |
| 失败 | 2 | t_search、t_example：驱动 mifluzsearch 在 HMDFS getcwd 拒绝窗启动即 Signal 11（WordKeyInfo 初始化路径），证据链：①stderr 先报 `didn't find key description in config` 再崩；②同期 bash 纯 shell 操作同样 getcwd 报错；③osip 同期同故障窗失败、窗口恢复后通过。库本体不受影响 |
| N_consumer（新增消费者） | 1 | test_package/test_mifluz：WordContext/WordList 建库+插入+FindWord 检索断言，1/1 通过 |

## 路径 B 判断

判断不成立，按纯路径 A 申报。依据：交叉编译 AC_TRY_RUN 缓存变量预设、
HMDFS getcwd 回退、clang 15 收窄/字符字面量硬错误三类问题均为已有知识或
通用编译兼容性修复（E011/E386/aldo 先例、C++ 标准行为），无新的跨仓库
可复用知识增量；查重未发现可沉淀的新错误签名。

## 遗留与限制

- doc/（texinfo）以 MAKEINFO=true 占位，非库适配范围
- t_search/t_example 的根治需要上游或平台层修复 getcwd 故障下的启动崩溃，
  本适配以证据链申报环境限制
## 补丁瘦身（GLM-43 接手，2026-09-17）

AI 代码评审拒审本 PR：11 个可审文件 6280 行超出评审上限，95% 体量来自
0001-config.guess.patch（2548 行）与 0003-config.sub.patch（3388 行）的
config 文件全量替换（2012 版 → 2023 版）。改按 gtypist 2.10.1 先例重写为
最小插入补丁：config.guess（原 2012-02-10 版）case 表顶部插入 HarmonyOS
分支输出 aarch64-unknown-linux-ohos（补丁 20 行）；config.sub（原
2012-04-18 版）maybe_os 段加 linux-ohos*、CPU 表加 aarch64（补丁 19 行）。
配方显式传 --build/--host 三元组，两文件补丁仅服务 libtool/automake
内部识别，行为与全量替换等价。conan-verify 重跑 G0-G4 全过。

---

**编译结束**: 2026-09-15 09:54
**最终状态**: built


## 删除 doc 生成产物补丁（GLM-43，2026-09-17 AI 评审意见闭环）

AI 评审（P2）指出 0006-doc-stamp-vti.patch / 0007-doc-version.texi.patch
是 refresh-patch --auto 误捕获的构建树垃圾：把 doc/stamp-vti、version.texi
两条 @set UPDATED 行替换成了 68 行构建机 shell 环境转储（BASH、HOME、
UID、SSH_CLIENT、OHOS SDK LD_LIBRARY_PATH 等），既泄露环境信息又会把
空 @set 与环境行带进手册正文（当前仅 MAKEINFO=true 占位掩盖）。
两个文件均为 make 可再生成的生成产物：整体删除补丁及 conandata.yml
对应声明，恢复上游原状，make 构建时自行重新生成干净 stamp/version。
conan-verify 重跑 G0-G4 全过。
