# proftmb

ProfTMB — Profile fed HMM（隐马尔可夫模型）预测器，从蛋白质序列预测革兰氏阴性菌
外膜 β 桶（transmembrane beta barrels）的跨膜区。输入 PSI-BLAST 位置特异打分矩阵
（PSSM），输出逐残基四态预测（i/o/u/d）与整体统计。

- 上游：http://rostlab.org/ （Ubuntu 源 proftmb 1.1.12-11build2）
- 构建系统：autoconf 2.67 + automake
- 许可证：GPL-3.0-or-later

## 鸿蒙适配要点

1. **依赖栈**：直接依赖 opt/3.19（`AC_CHECK_LIB(opt)`）与 gsl/2.8（运行期
   libgsl.so.28 / libgslcblas.so.0）。configure 用 AC_CHECK_LIB/AC_CHECK_HEADER
   探测依赖，而 AutotoolsToolchain 不下发依赖 -I/-L，配方在 build() 显式拼接
   CPPFLAGS/LDFLAGS。
2. **上游 Makefile 三连修**：① src/Makefile 泄漏 `dnl` 注释行（missing separator），
   configure 后剥除；② 直接调用 `help2man` 而非 `$(HELP2MAN)`，OHOS 无该工具，
   PATH 前置 no-op wrapper 生成最小 man 页（E289）；③ toybox sed 不支持
   `--in-place`，顶层 install 规则改临时文件方案（E010）。
3. **HMDFS 兼容**：toybox sort/cat 对 `-` 参数报 Permission denied、WorkBuddy
   safe-bin rm shim shebang 损坏，configure 注入 shell 函数包装。
4. **OHOS musl 不跟随符号链接（E050）**：gsl 安装 libgsl.so.28 -> libgsl.so.28.0.0
   软链，运行期报 Error loading shared library；配方把实体 .so 摊平拷入
   `<pkg>/lib` 并 patchelf 设 `RUNPATH=$ORIGIN/../lib`。
5. **ELF 签名（E077）**：HMDFS 拒绝 execve 未签名 ELF。配方用 binary-sign-tool
   `sign -selfSign 1` 自签名；工具链链接期已插入空 .codesign 段导致 sign 报
   already exists，须先 `objcopy --remove-section=.codesign`；签名产物丢失可执行位，
   须 chmod 恢复。顺序必须是 patchelf → 签名（strip/patchelf 会破坏 codesign 哈希）。
6. **消费者调用姿势**：上游 options 文件把 `-d` 硬编码为 `//share/proftmb`，且
   不带 @options 时 -s/-t 默认空串会把数据目录当 arch 文件打开（ReadMap: Reached
   EOF without an ENDRECORD）。必须 `proftmb @options -d <datadir> -q <pssm> -o <prefix>`。

## 测试

上游无自动化测试套件（Makefile.am 无 check 目标/TESTS/check_PROGRAMS）。
test_package 提供 3 个具名 HarmonyOS 消费者用例（test.sh 驱动）：

- HC-1：`proftmb --version` 端到端 exec（验证签名可执行 + 加载器闭包）
- HC-2：`@options` 全模型数据对上游样例 example.Q 完整跑通预测流程
- HC-3：预测输出与上游参考输出逐字节 cmp 一致
