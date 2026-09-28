# gcc-12-cross 12.4.0 — OHOS 非 PIE 可执行 stdout COPY 重定位崩溃（路径 B 草稿）

## 真实错误
用 GCC 12.4.0 交叉编译的 OHOS 可执行程序，调用 fprintf/fputs/fwrite/fprintf(stdout, ...)
家族时运行 SIGSEGV(-11)；`min-printf`（printf 直接调用，无 FILE* 参数）正常。
`llvm-readelf -r` 显示 GCC 产出链接对 `stdout` 数据符号生成 `R_AARCH64_COPY` 拷贝重定位；
同源用系统 clang（默认 PIE）产物为 `R_AARCH64_GLOB_DAT` 且运行正常。

## 根因
OHOS 平台默认 clang 产出 PIE（ET_DYN）；GCC 12.4.0 默认输出 ET_EXEC（非 PIE）。
非 PIE 静态可执行对动态符号（libc 的 stdout/stderr 数据符号）采用 COPY 重定位
（拷贝符号值到可执行文件 .bss），OHOS 加载器在访问这类 COPY 重定位符号时崩溃。
凡以 FILE* 形式引用 stdout（fprintf/fputs/fwrite 等）的调用路径全部中招；
printf 内部引用在 libc 内完成，不触发可执行文件内 COPY 重定位，因此正常。

## 修复
- 测试/消费者程序编译链接统一加 `-fPIC -pie`（与平台 clang 默认 PIE 对齐），
  链接器改用 GOT 间接（R_AARCH64_GLOB_DAT），不再产生 COPY 重定位。
- 实测：`min-fprintf.c` 默认编译运行 RC=139(SIGSEGV)；加 `-fPIC -pie` 后 RC=0 输出正常；
  `gcc.c-torture/execute` fprintf 家族（fprintf-1/fprintf-chk-1/vfprintf-1 等）加 `-fPIC -pie`
  后全部通过（torture 全量 3414/3450，失败均为有效目标门控/平台限制，见 test-report.md）。
- gcc-12-cross 配方（test_package/test_ohos.c、torture 运行器、消费者用例）均按
  `-fPIC -pie` 编译链接；manifest.yaml 的 source_transforms/knowledge_gained 记录该结论。

## 验证
- 命令：`xgcc-sign -w -O0 -fPIC -pie min-fprintf.c -o min-fprintf-picpie` → 运行 RC=0
- 对照：`xgcc-sign -w -O0 min-fprintf.c` → 运行 RC=139（Signal 11）
- 重定位对比：PIE 产物 `R_AARCH64_GLOB_DAT stdout`；非 PIE 产物 `R_AARCH64_COPY stdout`

## 适用边界
- 适用范围：OHOS aarch64 上使用 GCC（交叉或原生）编译并链接引用 libc stdout/stderr
  数据符号（FILE* 参数）的可执行/测试/消费者程序的任何库
- 边界/反例：纯库型包（仅 .a/.so、无被运行的可执行）、不使用 FILE* 数据符号的
  程序（如仅 printf 字面量）不受影响；clang 链无需处理（默认 PIE）
- 关联：gcc-14 先例仅解决 host 生成器 PIE（gcc_cv_c_no_fpie=no），未覆盖最终输出可执行
  COPY 重定位问题——本条目为新增差异

## 查重差异
- 四范围查重（正式 doc/、图谱 graph/、草稿 drafts/、index.tsv）：未命中
- E005/E234 为通用 -fPIC/--with-pic（共享/静态库方向），不覆盖 OHOS 加载器 COPY 重定位崩溃机理