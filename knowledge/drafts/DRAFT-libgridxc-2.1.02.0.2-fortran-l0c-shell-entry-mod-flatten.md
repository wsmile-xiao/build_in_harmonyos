# DRAFT-libgridxc-2.1.02.0.2-fortran-l0c-shell-entry-mod-flatten
> 纯Fortran包因L0c后缀白名单报no_test_sources时补充Shell消费者入口并打平.mod
## 问题特征（真实日志片段/标记）
- CI门禁失败：[fail] L0c: No test source files in test_package/，L0 gate: no_test_sources
- ci/conan/build_and_test.sh约355行L0c循环仅匹配c/cpp/cc/cxx/sh/py后缀，排除conanfile.py后空结果
- test_package此前仅含conanfile.py/CMakeLists.txt/MANIFEST.yml/lda_contract.f90/gga_contract.f90，无.sh入口
- 伴随失败域：lda_contract.f90:2:7 error: Cannot parse module file for module 'gridxc': Source file 'gridxc.mod' was not found，主库上游ctest 5/5已通过
- SDK漂移背景：test_package链接曾报ld.lld cannot open Scrt1.o/crti.o/crtbeginS.o与unable to find -lm/-lc，需复用主配方SDK探测
## 根因
- CI-L0c仅统计c/cpp/sh/py，致所有纯Fortran(.f90)包误报no_test_sources，与测试逻辑本身无关，属门禁策略通用可复用类问题
- 上游config/CMakeLists定义module-dir为libgridxc编译器ID-版本并install到include版本子目录，而test_package经CMakeDeps仅-I include，版本子目录不在搜索路径
- 真机SDK版本目录漂移使版本化glob全空，test_package初版_detect_sysroot漏掉harmonybrew clang致--sysroot为空，需从活编译器反查并缺件降级
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. 新增archives/l/libgridxc/2.1.02.0.2/test_package/test.sh，依次运行lda_contract与gga_contract并断言GRIDXC_TEST PASS标记，为真实消费者执行入口
2. 改archives/l/libgridxc/2.1.02.0.2/test_package/conanfile.py：exports_sources追加test.sh，test()先逐个做OHOS签名再用self.run经sh执行该脚本，保留HMBS标记输出
3. 同步archives/l/libgridxc/2.1.02.0.2/test_package/MANIFEST.yml中两条用例command记录，与test.sh一致
4. 主配方archives/l/libgridxc/2.1.02.0.2/conanfile.py的package()在cmake.install后新增_flatten_fortran_modules，将include树下全部*.mod复制打平到include/根目录，保留原版本子目录
5. test_package复用主配方OHOS SDK探测：移植_query_compiler_print/_ohos_sdk_dirs/_ohos_sdk_libdir，补tool_requires flang-ohos/20.1.0，显式设置CMAKE_Fortran_COMPILER与--target/--sysroot/-resource-dir及-L链接标志；本地模拟L0c/L0d/L0e检查通过且conanfile语法解析通过后送真机预检
## 禁止策略
- 禁止占位test.sh或仅过L0c而不打平.mod：test.sh必须是真实执行路径，经self.run调用并断言输出，不得为空脚本或仅echo
- 违例后果：真机仍报no_test_sources或gridxc.mod was not found，匹配forbid模式no_test_sources|gridxc.mod was not found|Cannot parse module file for module gridxc，任务退回修复循环
## 与相近条目的边界（查重）
- 与tmp只读、autotools无formal测试、ICE工具链、poetry布局等相邻条目正交：本条目失败域为Fortran门禁后缀白名单、.mod版本子目录可见性、SDK版本目录漂移，不处理压缩别名、demo改造、签名环境隔离之外的通用编译优化
- SDK探测与低内存-O1/-g0、签名LD_LIBRARY_PATH隔离均为本任务链路中的前置修复，本条目仅收录其在test_package复用模式，不重复收录通用降优化策略
## 适用判断
- 适用：Fortran等非C系语言包因L0c后缀白名单报no_test_sources且已有真实可执行测试时；Fortran库上游将.mod装入编译器版本子目录而消费者报.mod not found时；OHOS Fortran配方需--sysroot/-resource-dir但版本化glob全空时
- 不适用：已有.c/.cpp/.sh/.py真实入口仍报缺测试源时先查exports_sources与MANIFEST同步；C系头文件缺失非.mod路径问题
- 注意：test.sh须真实断言PASS标记，保持上游测试口径不断言篡改；.mod打平仅补包内可见性，不改上游安装逻辑
