# DRAFT-ndpi-5-ac-config-files-generated-header-install
> AC_CONFIG_FILES生成的公共头未被install时在package中补装通过真机编译门禁
## 问题特征（真实日志片段/标记）
- attempt 15310退化为v2:compile:compiler_error，真机test_package编译失败，上游make check已2/2通过但消费者编译仍失败。
- 真机stderr尾部：/storage/Users/currentUser/preflight/clients/77a3724f29e8/conan-home/p/b/ndpi71a6a5d58b31c/p/include/ndpi/ndpi_main.h:32:10: fatal error: 'ndpi_define.h' file not found
- 后续CMake/make链：1 error generated. / make[2]: *** [CMakeFiles/test_ndpi.dir/build.make:79: CMakeFiles/test_ndpi.dir/test.c.obj] Error 1 / make[1]: *** [CMakeFiles/Makefile2:87: CMakeFiles/test_ndpi.dir/all] Error 2
- attempt 15550解决v2:compile:compiler_error，gateOutcome为passed，原问题消失且真机门禁全部通过，本轮只改工作树未提交：给package()补了生成头安装。
## 根因
- configure.ac含AC_CONFIG_FILES src/include/ndpi_define.h与AC_CONFIG_HEADERS src/include/ndpi_config.h，前者是公共头，后者是构建私有头。
- 上游src/lib/Makefile.in的install规则只find $(top_srcdir)/src/include/*.h，仅拷贝源树头文件。
- ndpi_define.h由AC_CONFIG_FILES在top_builddir生成，源树src/include目录仅有ndpi_define.h.in而无ndpi_define.h，故包内缺失。
- ndpi_main.h无条件#include "ndpi_define.h"同目录quote-include，包消费者必因缺头编译失败，与上游make check是否通过无关。
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. 在archives/n/ndpi/5/conanfile.py新增_install_generated_headers()：优先取build树src/include/ndpi_define.h，若不存在则walk构建树兜底查找ndpi_define.h，找不到则抛错中断打包。
2. 将找到的ndpi_define.h拷贝到package/include/ndpi/ndpi_define.h，保证与ndpi_main.h同目录可被quote-include。
3. 在package()末尾调用该方法；ndpi_config.h保持构建私有不发布，仅补装消费者必需的ndpi_define.h。
4. 在archives/n/ndpi/5/notes.md登记该问题与方案，留存真机stderr、AC_CONFIG_FILES证据与Makefile.in install证据。
5. 真机用conan create复检：确认上游make check executed 2 passed 2且test_package不再报ndpi_define.h file not found。
## 禁止策略
- 禁止放任'missing ndpi_define.h'继续打包：模式'ndpi_define\.h' file not found出现即意味着消费者quote-include必失败，不得以忽略缺头或仅发布top_srcdir头文件的方式放行，否则test_package报file not found，真机compile门禁以compiler_error不通过。
- 仅补装ndpi_define.h，不发布构建私有的ndpi_config.h。
## 与相近条目的边界（查重）
- 类别性成立：15550胶囊给出autotools生成公共头缺失的通用根因与package()补装方案，可复用于同类配方，本条即沉淀该通用方法。
- 增量性成立：查重命中无生成头install遗漏条目，既有readonly_tmp/compiler_error条目阶段与根因均不同，不覆盖本场景；上游测试硬编码/tmp重定向条目解决的是make check阶段readonly_tmp，本条解决的是test_package阶段compile缺头，两者阶段、报错签名与修复位置均不同。
## 适用判断
- 适用：autotools配方out-of-source构建且AC_CONFIG_FILES生成公共头但install规则只拷贝top_srcdir头文件时；关键词compile_error、hmbs_repair_method、ac_config_files、generated_header。
- 判定：configure.ac含AC_CONFIG_FILES生成头、源树仅有.h.in、install规则仅find top_srcdir、消费者报同目录生成头file not found。
- 注意：不得虚构制品版本对应关系；找不到生成头必须抛错而非静默通过；不发布构建私有头。
