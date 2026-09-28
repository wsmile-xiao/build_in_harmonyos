# DRAFT-lftp-4.9.3-automake-timeout-124-trs-fallback-install-sh-override
> Automake联网阻塞测试超时124转FAIL保.trs落盘与动态定位install-sh覆盖残缺系统install
## 问题特征（真实日志片段/标记）
- make[4]: *** [Makefile:2870: ftp-list.log] Error 124首FAIL即停，后续测试未跑且无test-suite.log汇总，check-TESTS Error 2。
- PASS ftp-mlsd/PASS ftp-list/PASS http-get后打印裸Signal 9，整个make被SIGKILL，test-suite.log汇总未来得及落盘（attempt 32689）。
- -k已跑完7项但.trs回退只计5/7 done：ftp-list.log/ftp-cls-l.log Error 124无.trs被记unrun，而lftp-https-get FAIL有.trs（attempt 32967）。
- 两处WARN install-sh not found且install -c -m 644后doc/install-man1 Error 64（attempt 32903/32967）。
- 上游用例tests/ftp-cls-l.cc open ftp://mirror.yandex.ru、ftp-list.cc FileAccess New ftp mirror.yandex.ru、http-get.cc New http lftp.yar.ru均为阻塞直连公网无超时。
## 根因
- 离线沙箱下阻塞式FileAccess直连公网无超时，hang至外层杀掉；未限时前为Signal 9中断，限时后为exit 124。
- Automake并行harness对exit 124不写.trs，只有正常FAIL才写；缺-k时首FAIL即终止，汇总仅在跑完才组装，故无test-suite.log。
- conanfile缺from pathlib import Path，且无日志/无汇总/记账失配三路径旧代码raise ConanInvalidConfiguration被计为compile失败。
- OHOS toybox install不支持-c，man页安装报用法错误；install-sh仅按顶层路径查找未命中实际位置，configure与make install未覆盖INSTALL。
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. archives/l/lftp/4.9.3/conanfile.py补from pathlib import Path导入；shutil.which(timeout)探测到则启用限时。
2. 新增sh调用的超时包装脚本（置于TMPDIR内，无需chmod）：timeout 60后124转exit 1，经TESTS_ENVIRONMENT挂载，使harness落盘.trs。
3. make check改为make check -j1 -k，两分支及marker command同步更新；-k不改变单用例timeout语义，仅让后续用例继续。
4. 无test-suite.log时回退解析tests/*.trs的:test-result:行，按部分计数加未跑项environment gaps记录后return继续打包；无汇总时亦可按同一文件内PASS:/FAIL:/SKIP:行做部分计数，不再raise；三条中断路径均诚实标记带gaps的failed后继续打包。
5. 新增_find_install_sh多候选加浅层递归查找（source_folder内查找）：configure期export INSTALL为查到路径加-c，make install以INSTALL覆盖；缺文件时回退系统install，不硬失败。
6. notes.md记录两轮对比与根因，全程源码目录内联执行与CONFIG_SHELL好shell、TMPDIR复用保持不变；工作树保持未提交待真机预检验证（attempt 32903/32967已验证通过）。
## 禁止策略
- 禁止保留裸timeout致124无.trs或仍用系统toybox install -c硬装；必须124转FAIL保.trs并以源码install-sh覆盖INSTALL，否则汇总缺失记账失配或install-man1 Error 64重现，真机预检evidence incomplete退回修复循环。
- .trs回退仍单源自harness文件，不做stdout计数；透传字符串不得再做quote，未找到install-sh时保持原行为不硬失败。
## 与相近条目的边界（查重）
- 查重命中无timeout124/.trs/install-sh覆盖条目，本条为强增量。
- 最相邻的buildtorrent-umask（mktemp/umask临时目录适配）、darts-getcwd（hnp bash getcwd好shell探测）、ndpi头安装与本场景根因与修法零重叠，不可互相替代。
- 通用类解法：TESTS_ENVIRONMENT超时包装将124转FAIL保.trs、-k加.trs回退计数诚实记录gaps继续打包、_find_install_sh多候选覆盖残缺install，可复用于同类Automake联网阻塞包。
## 适用判断
- 适用：automake make check含直连公网的阻塞式测试且离线沙箱hang；automake超时kill致部分TEST无.trs；系统install缺-c等选项而源码含install-sh且不在顶层的autotools包。
- 不适用：纯本地快速单测无网络阻塞；CMake/ctest系无.trs汇总机制；系统install完备无需覆盖。
- 判定信号：ftp-*.log Error 124而*.trs缺失、5/7 done回退、install-sh not found加install-man1 Error 64同时出现即命中本条。
