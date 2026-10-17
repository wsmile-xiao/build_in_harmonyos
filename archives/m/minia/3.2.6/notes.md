# minia 3.2.6 适配记录

- 任务：#8879，分支 `feat/minia-3.2.6`。
- 上游源码：GATB/minia `v3.2.6`，commit `594d6e390841df82a28601ed810662bf0e463c7b`。
- 上游许可：AGPL-3.0-or-later（上游 `LICENSE`）。
- 源码归档的子模块处理参照知识条目 E150：另取 `.gitmodules` 所指向且由 tag gitlink 固定的 GATB core commit `99105b3b491d8dbd43e75ad390239b3279a0a8ab`，并校验 SHA-256。
- 子模块归档缺内容复用 E150，codeload 文件名复用 E276，旧 CMake 最低版本复用 E187。命令行传入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`。
- 真机 clang/libc++ 下固定 GATB core 的 `kff_io.cpp` 使用未声明的 `uint`，并对 `std::streampos` 与 `long` 直接加减产生重载歧义。补丁 `patches/0001-gatb-kff-libcxx-portability.patch` 改为 `unsigned int` 与 `streampos(streamoff)` 辅助函数，不含 `__OHOS__`。
- 本轮新知识不是上述复用项。原生构建预先写入 `CMAKE_SYSTEM_NAME` 时，CMake 把本机 `try_run` 当成交叉编译。成对草稿为 `knowledge/drafts/DRAFT-minia-3.2.6-preset-system-name-false-cross`。配方不再传该变量，只在生成器目录提供 `Platform/HarmonyOS.cmake`。
- 上游 `CMakeLists.txt` 没有 `add_test` 或 `enable_testing`。自动化通过/失败脚本是 `test/simple_test.sh` 的四个场景：X unitig、tip contig、bubble contig、ec contig。配方在构建时执行原脚本，不修改上游测试。`10k_test.sh` 与 `buchnera_test.sh` 没有断言，`test/README` 写明要人工查看。`test_ERR039477.sh` 要从 `ftp://ftp.sra.ebi.ac.uk` 下载 31782747 字节样本，不计入这 4 项。

## 真机验证

- 环境：HarmonyOS AArch64，独立 `CONAN_HOME=~/work/psj/ch-minia`。成功日志 `~/work/psj/minia8879-create-r2.log`，结尾时间 `2026-10-04T08:36:37Z`。
- 成功的 cmake 命令行不含 `CMAKE_SYSTEM_NAME`。`TEST_LFS_WORKS` 为 yes，`Configuring done (172.9s)`，`[100%] Built target minia`。
- 失败对照：`minia8879-create-r2-harmony-cross.log` 带 `-DCMAKE_SYSTEM_NAME=HarmonyOS`，`TEST_LFS_WORKS` 为 no，`Width test failed with result: PLEASE_FILL_OUT-FAILED_TO_RUN`，`CREATE_EXIT:1`。`minia8879-create-linux-cross.log` 带 `-DCMAKE_SYSTEM_NAME=Linux`，同样 `FAILED_TO_RUN` 与 `CREATE_EXIT:1`。
- 上游：`bash simple_test.sh` 打印四行 `PASSED`。X 场景按脚本原文先打印 `NOT EQUAL: 1 sequence(s) in X.solution.fa not in X.contigs.fa`，并写明应随后打印 6；日志下一行是 `  6`。
- 包 ID：`d19813127f0ec2ca84c0b48cbd85080965097448`。完整引用 `minia/3.2.6#3db8171c9969da95965f4cd7e3b899cd:d19813127f0ec2ca84c0b48cbd85080965097448#76f972882838e97e55aa53ed7dc11329`。`CREATE_EXIT:0`。
- 消费者：`test_package` 执行 `python3 test_minia.py`。脚本有 3 条 `assert`（`minia` 在运行环境中、生成 `X.contigs.fa`、以 `>` 开头的行数等于 6）。日志不打印断言计数；任一断言失败都会非零退出。该命令之后 `CREATE_EXIT:0`，因此 3/3 通过。
- 实测配方字节与工作区一致：`conanfile.py` md5 `275d3102356879e6c789ca9cfbd3301b`，补丁 md5 `34220671fcba0acd36372237c7bf60f6`，`test_minia.py` md5 `6db4b32ff53f6833da5b69b627c56508`。
