# DRAFT-paperjam-1.2.2-disable-ld-preload-embed-dt-rpath-tmp-vendored
> OHOS上停用LD_PRELOAD改用内嵌DT_RPATH解析传递依赖并修复只读tmp与vendored定位，6/6验证通过真机证据门禁
## 问题特征（真实日志片段/标记）
- `Error relocating .../tmp/paperjam.signed: _ZN10QPDFWriterC1ER4QPDFPKc: symbol not found` 等8个QPDF符号缺失，5/6用例rc=127，伴随stale_runtime_library诊断
- `Error loading shared library libjpeg.so.62: (needed by .../conan-home/p/qpdfbc80d597299a2/p/lib/libqpdf.so.30.3.2)`，LD_PRELOAD=qpdf:jpegs与jpeg:qpdf两种顺序均复现，test.sh无RESULT行
- `clang-15: error: no such file or directory: '.../conan-home/p/paper502a43aab7021/e/vendored/paper.c'`
- `ERROR: paperjam/1.2.2 (test package): Error in test() method` / `ConanException: test.sh produced no RESULT line — harness broken`
- 成功态：`=== test_package summary: 6/6 passed, 0 failed ===` / `RESULT: 6 passed, 0 failed` / `HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"bash test.sh","discovered":6,"passedCount":6}`
- `HMBS_UPSTREAM_TEST_RESULT={"status": "no_tests", "framework": "make", "command": "make check (upstream provides no check/test target)", "discovered": 0, "executed": 0}`
- 平台能力：`HMBS_PLATFORM_CAPABILITIES={"shell":"/bin/sh","tmpdir":".../runtime/paperjam-1.2.2/tmp","jobs":1,"chmod":0,"local_mktemp":1}`，裸`mktemp -d`写只读/tmp触发readonly_tmp
## 根因
- OHOS musl loader忽略LD_LIBRARY_PATH，且不从LD_PRELOAD其余条目解析被预载库自身的DT_NEEDED：预载libqpdf必死于其DT_NEEDED libjpeg.so.62，与顺序无关，属跨库通用工具链/平台差异，需内嵌DT_RPATH（--disable-new-dtags，OHOS musl仅认DT_RPATH，gssdp先例）才是可行路径，前两轮测试进程被LD_PRELOAD先杀死根本没执行到RPATH解析。
- 配方树不完整：工作树仅有一个conandata.yml且引用不存在补丁，真机evidence incomplete；libpaper/1.1.28仅为legacy归档不可conan安装，paperjam仅用paperinfo/paperpswidth/paperpsheight三符号，故用vendored/paper.h+paper.c内置纸张表编成libpaper.a供-lpaper链接。
- Conan2中exports_sources落在export_sources_folder而非recipe_folder(e/)，配方按recipe_folder/vendored定位致e/vendored/paper.c根本不存在。
- test()用env=None丢弃VirtualRunEnv且裸mktemp -d写只读/tmp，DISCOVERED=5与6处report不一致。
- MANIFEST中upstream_check_command/upstream_test_command非空（含make check）被清单器判为上游存在测试，诚实no_tests/0被拒；upstream_test_audit为扁平字符串无法机解析。实测paperjam-1.2.2.tar.gz顶层仅cmds.cc/paperjam.cc/parse.cc等无tests目录、无*test*源码，Makefile目标仅all/paperjam/paperjam.1/paperjam.1.html/clean/install/release，无check/test目标、无configure，确实无测试。
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. 补全配方树（archives/p/paperjam/1.2.2/conanfile.py）：仅构建`make paperjam`二进制跳过需a2x的手册页，CPPFLAGS/LDLIBS注入qpdf与shim路径，R33从conf取编译器；conandata.yml去掉悬空patches节仅留官方URL+实测sha256；新增vendored/paper.h+paper.c（ISO/US纸张表PS点值）。
2. vendored改用export_sources_folder定位：将exports属性改为exports+显式export_sources()用copy()把vendored/paper.c和paper.h拷入export_sources_folder/vendored，build()按export_sources_folder→source_folder→recipe_folder顺序探测，缺失抛明确定位错误。
3. 内嵌DT_RPATH并停用LD_PRELOAD（核心）：主conanfile build()新增rpath_flags（-Wl,--disable-new-dtags + -Wl,-rpath各依赖libdir）同时经LDFLAGS和LDLIBS传入make，确保plain-Makefile两种变量约定都被吃进链接行，使二进制自带DT_RPATH解析qpdf及传递libjpeg；test_package/conanfile.py删除LD_PRELOAD设置，_runtime_preload改为返回空存根，新增llvm-readelf/readelf -d诊断NEEDED/RPATH；test.sh顶部unset LD_PRELOAD防继承外层预载。
4. 只读tmp与计数修复（test_package/test.sh + conanfile.py + MANIFEST.yml）：test.sh改POSIX sh、用`mktemp -d ${TMPDIR}/paperjam.XXXXXX`并回退，加ldd诊断，DISCOVERED 5→6；conanfile.py的self.run改env=None为env=conanrun保留runenv；MANIFEST assertion_count 5→6。
5. no_tests结构化审计去误判：test_package/MANIFEST.yml的upstream_check_command与upstream_test_command改为空串，upstream_test_audit改写为结构化映射（source_tarball/source_sha256/top_level_files/scanned_for/scan_result/make_check_output/reason，osmctools/sipcalc同款）；test_package/conanfile.py上游标记改为framework:none/command空串。
6. 验证：真机preflight应见readelf -d含DT_RPATH，`RESULT: 6 passed, 0 failed`与6/6 passed，HMBS_UPSTREAM_TEST_RESULT status no_tests带结构化审计放行。
## 禁止策略
- 禁止用LD_PRELOAD解析被预载库自身的DT_NEEDED传递依赖（含调整leaf-first顺序重试）：两轮预检qpdf-first与jpeg-first均报同一libjpeg.so.62错误，机制本身不可用；违者触发`Error loading shared library .*needed by.*\.so`且无RESULT行。
- 禁止配方按recipe_folder读取exports_sources文件、禁止test.sh裸`mktemp -d`写/tmp、禁止MANIFEST以非空check命令+扁平审计申报no_tests。
- 环境类：SSH网关熔断（Connection timed out during banner exchange）不得误判为下载超时改conandata镜像；不得在Windows上强行处理libXext/libxext大小写碰撞存量dirty。
## 与相近条目的边界（查重）
- 本条目零命中查重：现有库无“OHOS预载库自身DT_NEEDED无法经LD_PRELOAD解析须内嵌DT_RPATH”为跨库通用解法条目，gssdp仅为单库RPATH先例未抽象为预载传递依赖停用准则。
- readonly_tmp/export_sources_folder/no_tests结构化审计等通用证据门禁策略均未被现有知识覆盖：lzop/wraplinux的no_tests误判教训、faiss的export_sources_folder+copy()模式、osmctools/sipcalc结构化审计在本条目首次合流为同一paperjam证据链，不与单点tmp或单点RPATH条目重复。
## 适用判断
- 当OHOS上出现`Error loading shared library <leaf> (needed by <preloaded>.so)`且主二进制可嵌入DT_RPATH指向conan依赖libdir时适用本条目，直接停用LD_PRELOAD改RPATH。
- 当配方自带vendored/shim需在build()编译、Conan2用exports_sources机制时，按export_sources_folder优先探测适用。
- 当test脚本需写tmp且平台tmpdir只读、或上游tarball经find *test*零命中+Makefile无check/test目标需申报no_tests时，同步适用TMPDIR模板与命令置空+结构化审计；若RPATH无法嵌入则走fallback静态链接/随包bundle叶库。
