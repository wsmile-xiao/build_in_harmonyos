# DRAFT-libnih-1.0.3-ndebug-assert-sideeffect-hoist
> Release -DNDEBUG吞掉assert副作用致autotools代码生成器签名漂移的外移修复
## 问题特征（真实日志片段/标记）
- 生成器签名漂移：真机make check编译tests/marshal_code.c报conflicting types for my_*_marshal，签入头有const而生成点c无const，仅建成28个二进制对41个TESTS。
- 伴生工具链签名：ld.lld另轮报duplicate symbol output_package，defined at main.c与output.c，make nih-dbus-tool失败；make check另轮报sys/socket.h重定义sockaddr_storage，previous at linux/socket.h，test_io.c触发。
- 安装与验证标记：单文件libnih.h安装成功而28头批量经am__base_list报install-nihincludeHEADERS Error 64；修复后可见/bin/sh install-sh -c多头安装成功，且HMBS_UPSTREAM_TEST_RESULT如实报discovered 41 executed 41。
- 通用诊断噪声：多轮机械命中tmpdir/shell/configure failed与只读/tmp等通用诊断，不能作为本签名依据。
## 根因
- 主因是Release带-DNDEBUG把assert编译掉，而nih-dbus-tool/tests/marshal_factory.c的assert(type_to_const)与demarshal_factory.c的assert(nih_strdup/type_to_pointer)把副作用写在assert内，NDEBUG下const转换不执行，导致生成签名与签入头冲突，上游2010默认不断言故未暴露。
- 同包另有三类跨库通用根因并已证伪分离：clang-15默认-fno-common使2010年tentative定义重复；nih/tests/test_io.c无条件同时含linux/socket.h与sys/socket.h在OHOS musl各定义一次sockaddr_storage；设备端install多源限制致Error 64。
- 已证伪：TMPDIR只读、profile编译器沙箱不可达、缺pkgconf与dbus-1点pc、会话总线挂起等均属前序阶段假设，本轮以源码与日志证伪，不沿用。
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. archives/l/libnih/1.0.3/conanfile.py的source新增_fix_factory_ndebug，用replace_in_file把4处副作用移出assert无条件执行，assert只验结果，indent调用同步由int改为char星并断言非空，对齐tarball中char星indent声明。
2. 同文件generate追加tc.extra_cflags加-fcommon，恢复老代码tentative定义合并，解决output_package在main点o与output点o重复。
3. 同文件source新增_guard逻辑直改nih/tests/test_io.c，把linux/socket.h包入仅glibc或uclibc才引入的守卫，musl走sys/socket.h；放弃0002补丁文件路线，因其空行无空格前缀且hunk计数不符致patch stream incomplete。
4. 同文件新增_patch_install_sh，递归遍历build目录全部Makefile，把INSTALL改写为自带install-sh路径，不经make命令行传含空格变量，避免Error 2，安装内容与模式不变。
5. 上游测试按目录逐个make check并对失败目录逐二进制隔离，计数取test-suite点log并恒输出HMBS_UPSTREAM_TEST_RESULT，不删减41项TESTS。
## 禁止策略
- 禁止把副作用保留在assert内或以去NDEBUG掩盖生成器缺陷，须外移后断言校验。
- 禁止以28对41残缺口径标记通过，须41全部编出后按实计数上报，缺口分项记gaps。
- 禁止经make参数传含空格INSTALL覆盖，须改生成文件内变量指向install-sh。
## 与相近条目的边界（查重）
- 机械命中均为tmpdir/shell/configure failed等通用诊断，相邻E165/buildtorrent/darts/ncrack与本任务新失败签名零重叠，现有条目无法覆盖。
- 本条目签名为conflicting types marshal加duplicate symbol加sockaddr_storage重定义，与通用临时目录与三元组识别条目正交；-fcommon与双头守卫与NDEBUG外移与INSTALL改install-sh均为跨库工具链平台缺陷通用解法，已给出适用条件与多轮证伪证据。
## 适用判断
- 适用：2010年前后autotools老项目在clang15报duplicate symbol且为无extern全局tentative定义时；测试或源码同时含两套socket头且报sockaddr_storage重定义且所需符号已由musl提供时；生成器把类型转换或内存分配写在assert内且Release开DNDEBUG致签名漂移时；设备端install单文件成功而多源报64时。
- 慎用：只改计数头与换行不改语义；replace严格匹配须同步上游上下文；仅恢复合并语义不扩大全局优化；不跳过上游测试或删除断言。
