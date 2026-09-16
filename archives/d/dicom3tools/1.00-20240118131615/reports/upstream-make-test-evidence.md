# 上游 make test 输出留档

> 逐字留档：本文件为原始日志的**直接复制**，未加工；下方分隔标记之后即为原始内容。

| 属性 | 值 |
| --- | --- |
| 原始文件 | `upstream-make-test.log` |
| 字节数 | 89079 |
| 行数 | 1076 |
| sha256 | `9f45c2e34368018c6f0764a2dfddcbc329913bee7c878dc57012eafe01d44b12` |
| 采集命令 | `make IMAKE_DEFINES="-DStripCmd=true -DAnsiCCmd=clang -DCPlusPlusCmd=clang++" test` |
| 采集时间 | 2026-09-11（设备本地时间） |

<!-- BEGIN VERBATIM LOG -->
testing in ./appsrc...
make[1]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc'
testing in ./appsrc/acrnema...
make[2]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/acrnema'
mkdir: cannot create directory ‘//tmp/test.create.ut.sh.65040’: Read-only file system
./test.create.ut.sh starting
./test.create.ut.sh[60]: can't create /tmp/test.create.ut.sh.65040/ut.ile.nm: No such file or directory
Comparing ut.ile.nm
cmp: ../../test/appsrc/acrnema/ut.ile.nm: No such file or directory
cmp: /tmp/test.create.ut.sh.65040/ut.ile.nm: No such file or directory
./test.create.ut.sh[64]: can't create /tmp/test.create.ut.sh.65040/ut.ile.nm.andump: No such file or directory
Diffs for ut.ile.nm.andump
diff: ../../test/appsrc/acrnema/ut.ile.nm.andump: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ile.nm.andump: No such file or directory
./test.create.ut.sh[66]: can't create /tmp/test.create.ut.sh.65040/ut.ile.nm.dcdump: No such file or directory
Diffs for ut.ile.nm.dcdump
diff: ../../test/appsrc/acrnema/ut.ile.nm.dcdump: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ile.nm.dcdump: No such file or directory
./test.create.ut.sh[68]: can't create /tmp/test.create.ut.sh.65040/ut.ile.nm.odx: No such file or directory
Diffs for ut.ile.nm.odx
diff: ../../test/appsrc/acrnema/ut.ile.nm.odx: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ile.nm.odx: No such file or directory
./test.create.ut.sh[70]: can't create /tmp/test.create.ut.sh.65040/ut.ile.nm.odc: No such file or directory
Diffs for ut.ile.nm.odc
diff: ../../test/appsrc/acrnema/ut.ile.nm.odc: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ile.nm.odc: No such file or directory
./test.create.ut.sh[74]: can't create /tmp/test.create.ut.sh.65040/ut.ile.nm.cp.ile.nm.dccp: No such file or directory
Comparing ut.ile.nm.cp.ile.nm
cmp: ../../test/appsrc/acrnema/ut.ile.nm.cp.ile.nm: No such file or directory
cmp: /tmp/test.create.ut.sh.65040/ut.ile.nm.cp.ile.nm: No such file or directory
Diffs for ut.ile.nm.cp.ile.nm.dccp
diff: ../../test/appsrc/acrnema/ut.ile.nm.cp.ile.nm.dccp: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ile.nm.cp.ile.nm.dccp: No such file or directory
./test.create.ut.sh[77]: can't create /tmp/test.create.ut.sh.65040/ut.ile.nm.cp.ile.nm.andump: No such file or directory
Diffs for ut.ile.nm.cp.ile.nm.andump
diff: ../../test/appsrc/acrnema/ut.ile.nm.cp.ile.nm.andump: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ile.nm.cp.ile.nm.andump: No such file or directory
./test.create.ut.sh[79]: can't create /tmp/test.create.ut.sh.65040/ut.ile.nm.cp.ile.nm.dcdump: No such file or directory
Diffs for ut.ile.nm.cp.ile.nm.dcdump
diff: ../../test/appsrc/acrnema/ut.ile.nm.cp.ile.nm.dcdump: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ile.nm.cp.ile.nm.dcdump: No such file or directory
./test.create.ut.sh[81]: can't create /tmp/test.create.ut.sh.65040/ut.ile.nm.cp.ile.nm.odx: No such file or directory
Diffs for ut.ile.nm.cp.ile.nm.odx
diff: ../../test/appsrc/acrnema/ut.ile.nm.cp.ile.nm.odx: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ile.nm.cp.ile.nm.odx: No such file or directory
./test.create.ut.sh[83]: can't create /tmp/test.create.ut.sh.65040/ut.ile.nm.cp.ile.nm.odc: No such file or directory
Diffs for ut.ile.nm.cp.ile.nm.odc
diff: ../../test/appsrc/acrnema/ut.ile.nm.cp.ile.nm.odc: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ile.nm.cp.ile.nm.odc: No such file or directory
./test.create.ut.sh[86]: can't create /tmp/test.create.ut.sh.65040/ut.ile.nm.cp.ele.nm.dccp: No such file or directory
Comparing ut.ile.nm.cp.ele.nm
cmp: ../../test/appsrc/acrnema/ut.ile.nm.cp.ele.nm: No such file or directory
cmp: /tmp/test.create.ut.sh.65040/ut.ile.nm.cp.ele.nm: No such file or directory
Diffs for ut.ile.nm.cp.ele.nm.dccp
diff: ../../test/appsrc/acrnema/ut.ile.nm.cp.ele.nm.dccp: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ile.nm.cp.ele.nm.dccp: No such file or directory
./test.create.ut.sh[89]: can't create /tmp/test.create.ut.sh.65040/ut.ile.nm.cp.ele.nm.andump: No such file or directory
Diffs for ut.ile.nm.cp.ele.nm.andump
diff: ../../test/appsrc/acrnema/ut.ile.nm.cp.ele.nm.andump: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ile.nm.cp.ele.nm.andump: No such file or directory
./test.create.ut.sh[91]: can't create /tmp/test.create.ut.sh.65040/ut.ile.nm.cp.ele.nm.dcdump: No such file or directory
Diffs for ut.ile.nm.cp.ele.nm.dcdump
diff: ../../test/appsrc/acrnema/ut.ile.nm.cp.ele.nm.dcdump: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ile.nm.cp.ele.nm.dcdump: No such file or directory
./test.create.ut.sh[93]: can't create /tmp/test.create.ut.sh.65040/ut.ile.nm.cp.ele.nm.odx: No such file or directory
Diffs for ut.ile.nm.cp.ele.nm.odx
diff: ../../test/appsrc/acrnema/ut.ile.nm.cp.ele.nm.odx: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ile.nm.cp.ele.nm.odx: No such file or directory
./test.create.ut.sh[95]: can't create /tmp/test.create.ut.sh.65040/ut.ile.nm.cp.ele.nm.odc: No such file or directory
Diffs for ut.ile.nm.cp.ele.nm.odc
diff: ../../test/appsrc/acrnema/ut.ile.nm.cp.ele.nm.odc: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ile.nm.cp.ele.nm.odc: No such file or directory
./test.create.ut.sh[103]: can't create /tmp/test.create.ut.sh.65040/ut.ele.nm: No such file or directory
Comparing ut.ele.nm
cmp: ../../test/appsrc/acrnema/ut.ele.nm: No such file or directory
cmp: /tmp/test.create.ut.sh.65040/ut.ele.nm: No such file or directory
./test.create.ut.sh[107]: can't create /tmp/test.create.ut.sh.65040/ut.ele.nm.andump: No such file or directory
Diffs for ut.ele.nm.andump
diff: ../../test/appsrc/acrnema/ut.ele.nm.andump: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ele.nm.andump: No such file or directory
./test.create.ut.sh[109]: can't create /tmp/test.create.ut.sh.65040/ut.ele.nm.dcdump: No such file or directory
Diffs for ut.ele.nm.dcdump
diff: ../../test/appsrc/acrnema/ut.ele.nm.dcdump: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ele.nm.dcdump: No such file or directory
./test.create.ut.sh[111]: can't create /tmp/test.create.ut.sh.65040/ut.ele.nm.odx: No such file or directory
Diffs for ut.ele.nm.odx
diff: ../../test/appsrc/acrnema/ut.ele.nm.odx: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ele.nm.odx: No such file or directory
./test.create.ut.sh[113]: can't create /tmp/test.create.ut.sh.65040/ut.ele.nm.odc: No such file or directory
Diffs for ut.ele.nm.odc
diff: ../../test/appsrc/acrnema/ut.ele.nm.odc: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ele.nm.odc: No such file or directory
./test.create.ut.sh[116]: can't create /tmp/test.create.ut.sh.65040/ut.ele.nm.cp.ile.nm.dccp: No such file or directory
Comparing ut.ele.nm.cp.ile.nm
cmp: ../../test/appsrc/acrnema/ut.ele.nm.cp.ile.nm: No such file or directory
cmp: /tmp/test.create.ut.sh.65040/ut.ele.nm.cp.ile.nm: No such file or directory
Diffs for ut.ele.nm.cp.ile.nm.dccp
diff: ../../test/appsrc/acrnema/ut.ele.nm.cp.ile.nm.dccp: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ele.nm.cp.ile.nm.dccp: No such file or directory
./test.create.ut.sh[119]: can't create /tmp/test.create.ut.sh.65040/ut.ele.nm.cp.ile.nm.andump: No such file or directory
Diffs for ut.ele.nm.cp.ile.nm.andump
diff: ../../test/appsrc/acrnema/ut.ele.nm.cp.ile.nm.andump: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ele.nm.cp.ile.nm.andump: No such file or directory
./test.create.ut.sh[121]: can't create /tmp/test.create.ut.sh.65040/ut.ele.nm.cp.ile.nm.dcdump: No such file or directory
Diffs for ut.ele.nm.cp.ile.nm.dcdump
diff: ../../test/appsrc/acrnema/ut.ele.nm.cp.ile.nm.dcdump: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ele.nm.cp.ile.nm.dcdump: No such file or directory
./test.create.ut.sh[123]: can't create /tmp/test.create.ut.sh.65040/ut.ele.nm.cp.ile.nm.odx: No such file or directory
Diffs for ut.ele.nm.cp.ile.nm.odx
diff: ../../test/appsrc/acrnema/ut.ele.nm.cp.ile.nm.odx: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ele.nm.cp.ile.nm.odx: No such file or directory
./test.create.ut.sh[125]: can't create /tmp/test.create.ut.sh.65040/ut.ele.nm.cp.ile.nm.odc: No such file or directory
Diffs for ut.ele.nm.cp.ile.nm.odc
diff: ../../test/appsrc/acrnema/ut.ele.nm.cp.ile.nm.odc: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ele.nm.cp.ile.nm.odc: No such file or directory
./test.create.ut.sh[128]: can't create /tmp/test.create.ut.sh.65040/ut.ele.nm.cp.ele.nm.dccp: No such file or directory
Comparing ut.ele.nm.cp.ele.nm
cmp: ../../test/appsrc/acrnema/ut.ele.nm.cp.ele.nm: No such file or directory
cmp: /tmp/test.create.ut.sh.65040/ut.ele.nm.cp.ele.nm: No such file or directory
Diffs for ut.ele.nm.cp.ele.nm.dccp
diff: ../../test/appsrc/acrnema/ut.ele.nm.cp.ele.nm.dccp: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ele.nm.cp.ele.nm.dccp: No such file or directory
./test.create.ut.sh[131]: can't create /tmp/test.create.ut.sh.65040/ut.ele.nm.cp.ele.nm.andump: No such file or directory
Diffs for ut.ele.nm.cp.ele.nm.andump
diff: ../../test/appsrc/acrnema/ut.ele.nm.cp.ele.nm.andump: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ele.nm.cp.ele.nm.andump: No such file or directory
./test.create.ut.sh[133]: can't create /tmp/test.create.ut.sh.65040/ut.ele.nm.cp.ele.nm.dcdump: No such file or directory
Diffs for ut.ele.nm.cp.ele.nm.dcdump
diff: ../../test/appsrc/acrnema/ut.ele.nm.cp.ele.nm.dcdump: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ele.nm.cp.ele.nm.dcdump: No such file or directory
./test.create.ut.sh[135]: can't create /tmp/test.create.ut.sh.65040/ut.ele.nm.cp.ele.nm.odx: No such file or directory
Diffs for ut.ele.nm.cp.ele.nm.odx
diff: ../../test/appsrc/acrnema/ut.ele.nm.cp.ele.nm.odx: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ele.nm.cp.ele.nm.odx: No such file or directory
./test.create.ut.sh[137]: can't create /tmp/test.create.ut.sh.65040/ut.ele.nm.cp.ele.nm.odc: No such file or directory
Diffs for ut.ele.nm.cp.ele.nm.odc
diff: ../../test/appsrc/acrnema/ut.ele.nm.cp.ele.nm.odc: No such file or directory
diff: /tmp/test.create.ut.sh.65040/ut.ele.nm.cp.ele.nm.odc: No such file or directory
./test.create.ut.sh finished
mkdir: cannot create directory ‘//tmp/test.create.private.un.sh.65081’: Read-only file system
./test.create.private.un.sh starting
./test.create.private.un.sh[64]: can't create /tmp/test.create.private.un.sh.65081/private.ile.nm: No such file or directory
Comparing private.ile.nm
cmp: ../../test/appsrc/acrnema/private.ile.nm: No such file or directory
cmp: /tmp/test.create.private.un.sh.65081/private.ile.nm: No such file or directory
./test.create.private.un.sh[68]: can't create /tmp/test.create.private.un.sh.65081/private.ile.nm.andump: No such file or directory
Diffs for private.ile.nm.andump
diff: ../../test/appsrc/acrnema/private.ile.nm.andump: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ile.nm.andump: No such file or directory
./test.create.private.un.sh[70]: can't create /tmp/test.create.private.un.sh.65081/private.ile.nm.dcdump: No such file or directory
Diffs for private.ile.nm.dcdump
diff: ../../test/appsrc/acrnema/private.ile.nm.dcdump: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ile.nm.dcdump: No such file or directory
./test.create.private.un.sh[72]: can't create /tmp/test.create.private.un.sh.65081/private.ile.nm.odx: No such file or directory
Diffs for private.ile.nm.odx
diff: ../../test/appsrc/acrnema/private.ile.nm.odx: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ile.nm.odx: No such file or directory
./test.create.private.un.sh[74]: can't create /tmp/test.create.private.un.sh.65081/private.ile.nm.odc: No such file or directory
Diffs for private.ile.nm.odc
diff: ../../test/appsrc/acrnema/private.ile.nm.odc: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ile.nm.odc: No such file or directory
./test.create.private.un.sh[78]: can't create /tmp/test.create.private.un.sh.65081/private.ile.nm.cp.ile.nm.dccp: No such file or directory
Comparing private.ile.nm.cp.ile.nm
cmp: ../../test/appsrc/acrnema/private.ile.nm.cp.ile.nm: No such file or directory
cmp: /tmp/test.create.private.un.sh.65081/private.ile.nm.cp.ile.nm: No such file or directory
Diffs for private.ile.nm.cp.ile.nm.dccp
diff: ../../test/appsrc/acrnema/private.ile.nm.cp.ile.nm.dccp: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ile.nm.cp.ile.nm.dccp: No such file or directory
./test.create.private.un.sh[81]: can't create /tmp/test.create.private.un.sh.65081/private.ile.nm.cp.ile.nm.andump: No such file or directory
Diffs for private.ile.nm.cp.ile.nm.andump
diff: ../../test/appsrc/acrnema/private.ile.nm.cp.ile.nm.andump: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ile.nm.cp.ile.nm.andump: No such file or directory
./test.create.private.un.sh[83]: can't create /tmp/test.create.private.un.sh.65081/private.ile.nm.cp.ile.nm.dcdump: No such file or directory
Diffs for private.ile.nm.cp.ile.nm.dcdump
diff: ../../test/appsrc/acrnema/private.ile.nm.cp.ile.nm.dcdump: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ile.nm.cp.ile.nm.dcdump: No such file or directory
./test.create.private.un.sh[85]: can't create /tmp/test.create.private.un.sh.65081/private.ile.nm.cp.ile.nm.odx: No such file or directory
Diffs for private.ile.nm.cp.ile.nm.odx
diff: ../../test/appsrc/acrnema/private.ile.nm.cp.ile.nm.odx: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ile.nm.cp.ile.nm.odx: No such file or directory
./test.create.private.un.sh[87]: can't create /tmp/test.create.private.un.sh.65081/private.ile.nm.cp.ile.nm.odc: No such file or directory
Diffs for private.ile.nm.cp.ile.nm.odc
diff: ../../test/appsrc/acrnema/private.ile.nm.cp.ile.nm.odc: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ile.nm.cp.ile.nm.odc: No such file or directory
./test.create.private.un.sh[90]: can't create /tmp/test.create.private.un.sh.65081/private.ile.nm.cp.ele.nm.dccp: No such file or directory
Comparing private.ile.nm.cp.ele.nm
cmp: ../../test/appsrc/acrnema/private.ile.nm.cp.ele.nm: No such file or directory
cmp: /tmp/test.create.private.un.sh.65081/private.ile.nm.cp.ele.nm: No such file or directory
Diffs for private.ile.nm.cp.ele.nm.dccp
diff: ../../test/appsrc/acrnema/private.ile.nm.cp.ele.nm.dccp: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ile.nm.cp.ele.nm.dccp: No such file or directory
./test.create.private.un.sh[93]: can't create /tmp/test.create.private.un.sh.65081/private.ile.nm.cp.ele.nm.andump: No such file or directory
Diffs for private.ile.nm.cp.ele.nm.andump
diff: ../../test/appsrc/acrnema/private.ile.nm.cp.ele.nm.andump: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ile.nm.cp.ele.nm.andump: No such file or directory
./test.create.private.un.sh[95]: can't create /tmp/test.create.private.un.sh.65081/private.ile.nm.cp.ele.nm.dcdump: No such file or directory
Diffs for private.ile.nm.cp.ele.nm.dcdump
diff: ../../test/appsrc/acrnema/private.ile.nm.cp.ele.nm.dcdump: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ile.nm.cp.ele.nm.dcdump: No such file or directory
./test.create.private.un.sh[97]: can't create /tmp/test.create.private.un.sh.65081/private.ile.nm.cp.ele.nm.odx: No such file or directory
Diffs for private.ile.nm.cp.ele.nm.odx
diff: ../../test/appsrc/acrnema/private.ile.nm.cp.ele.nm.odx: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ile.nm.cp.ele.nm.odx: No such file or directory
./test.create.private.un.sh[99]: can't create /tmp/test.create.private.un.sh.65081/private.ile.nm.cp.ele.nm.odc: No such file or directory
Diffs for private.ile.nm.cp.ele.nm.odc
diff: ../../test/appsrc/acrnema/private.ile.nm.cp.ele.nm.odc: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ile.nm.cp.ele.nm.odc: No such file or directory
./test.create.private.un.sh[111]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm: No such file or directory
Comparing private.ele.nm
cmp: ../../test/appsrc/acrnema/private.ele.nm: No such file or directory
cmp: /tmp/test.create.private.un.sh.65081/private.ele.nm: No such file or directory
./test.create.private.un.sh[115]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.andump: No such file or directory
Diffs for private.ele.nm.andump
diff: ../../test/appsrc/acrnema/private.ele.nm.andump: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.andump: No such file or directory
./test.create.private.un.sh[117]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.dcdump: No such file or directory
Diffs for private.ele.nm.dcdump
diff: ../../test/appsrc/acrnema/private.ele.nm.dcdump: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.dcdump: No such file or directory
./test.create.private.un.sh[119]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.odx: No such file or directory
Diffs for private.ele.nm.odx
diff: ../../test/appsrc/acrnema/private.ele.nm.odx: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.odx: No such file or directory
./test.create.private.un.sh[121]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.odc: No such file or directory
Diffs for private.ele.nm.odc
diff: ../../test/appsrc/acrnema/private.ele.nm.odc: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.odc: No such file or directory
./test.create.private.un.sh[124]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.cp.ile.nm.dccp: No such file or directory
Comparing private.ele.nm.cp.ile.nm
cmp: ../../test/appsrc/acrnema/private.ele.nm.cp.ile.nm: No such file or directory
cmp: /tmp/test.create.private.un.sh.65081/private.ele.nm.cp.ile.nm: No such file or directory
Diffs for private.ele.nm.cp.ile.nm.dccp
diff: ../../test/appsrc/acrnema/private.ele.nm.cp.ile.nm.dccp: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.cp.ile.nm.dccp: No such file or directory
./test.create.private.un.sh[127]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.cp.ile.nm.andump: No such file or directory
Diffs for private.ele.nm.cp.ile.nm.andump
diff: ../../test/appsrc/acrnema/private.ele.nm.cp.ile.nm.andump: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.cp.ile.nm.andump: No such file or directory
./test.create.private.un.sh[129]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.cp.ile.nm.dcdump: No such file or directory
Diffs for private.ele.nm.cp.ile.nm.dcdump
diff: ../../test/appsrc/acrnema/private.ele.nm.cp.ile.nm.dcdump: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.cp.ile.nm.dcdump: No such file or directory
./test.create.private.un.sh[131]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.cp.ile.nm.odx: No such file or directory
Diffs for private.ele.nm.cp.ile.nm.odx
diff: ../../test/appsrc/acrnema/private.ele.nm.cp.ile.nm.odx: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.cp.ile.nm.odx: No such file or directory
./test.create.private.un.sh[133]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.cp.ile.nm.odc: No such file or directory
Diffs for private.ele.nm.cp.ile.nm.odc
diff: ../../test/appsrc/acrnema/private.ele.nm.cp.ile.nm.odc: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.cp.ile.nm.odc: No such file or directory
./test.create.private.un.sh[136]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.cp.ele.nm.dccp: No such file or directory
Comparing private.ele.nm.cp.ele.nm
cmp: ../../test/appsrc/acrnema/private.ele.nm.cp.ele.nm: No such file or directory
cmp: /tmp/test.create.private.un.sh.65081/private.ele.nm.cp.ele.nm: No such file or directory
Diffs for private.ele.nm.cp.ele.nm.dccp
diff: ../../test/appsrc/acrnema/private.ele.nm.cp.ele.nm.dccp: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.cp.ele.nm.dccp: No such file or directory
./test.create.private.un.sh[139]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.cp.ele.nm.andump: No such file or directory
Diffs for private.ele.nm.cp.ele.nm.andump
diff: ../../test/appsrc/acrnema/private.ele.nm.cp.ele.nm.andump: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.cp.ele.nm.andump: No such file or directory
./test.create.private.un.sh[141]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.cp.ele.nm.dcdump: No such file or directory
Diffs for private.ele.nm.cp.ele.nm.dcdump
diff: ../../test/appsrc/acrnema/private.ele.nm.cp.ele.nm.dcdump: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.cp.ele.nm.dcdump: No such file or directory
./test.create.private.un.sh[143]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.cp.ele.nm.odx: No such file or directory
Diffs for private.ele.nm.cp.ele.nm.odx
diff: ../../test/appsrc/acrnema/private.ele.nm.cp.ele.nm.odx: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.cp.ele.nm.odx: No such file or directory
./test.create.private.un.sh[145]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.cp.ele.nm.odc: No such file or directory
Diffs for private.ele.nm.cp.ele.nm.odc
diff: ../../test/appsrc/acrnema/private.ele.nm.cp.ele.nm.odc: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.cp.ele.nm.odc: No such file or directory
./test.create.private.un.sh[157]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.un: No such file or directory
Comparing private.ele.nm.un
cmp: ../../test/appsrc/acrnema/private.ele.nm.un: No such file or directory
cmp: /tmp/test.create.private.un.sh.65081/private.ele.nm.un: No such file or directory
./test.create.private.un.sh[161]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.un.andump: No such file or directory
Diffs for private.ele.nm.un.andump
diff: ../../test/appsrc/acrnema/private.ele.nm.un.andump: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.un.andump: No such file or directory
./test.create.private.un.sh[163]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.un.dcdump: No such file or directory
Diffs for private.ele.nm.un.dcdump
diff: ../../test/appsrc/acrnema/private.ele.nm.un.dcdump: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.un.dcdump: No such file or directory
./test.create.private.un.sh[165]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.un.odx: No such file or directory
Diffs for private.ele.nm.un.odx
diff: ../../test/appsrc/acrnema/private.ele.nm.un.odx: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.un.odx: No such file or directory
./test.create.private.un.sh[167]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.un.odc: No such file or directory
Diffs for private.ele.nm.un.odc
diff: ../../test/appsrc/acrnema/private.ele.nm.un.odc: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.un.odc: No such file or directory
./test.create.private.un.sh[170]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.un.cp.ile.nm.dccp: No such file or directory
Comparing private.ele.nm.un.cp.ile.nm
cmp: ../../test/appsrc/acrnema/private.ele.nm.un.cp.ile.nm: No such file or directory
cmp: /tmp/test.create.private.un.sh.65081/private.ele.nm.un.cp.ile.nm: No such file or directory
Diffs for private.ele.nm.un.cp.ile.nm.dccp
diff: ../../test/appsrc/acrnema/private.ele.nm.un.cp.ile.nm.dccp: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.un.cp.ile.nm.dccp: No such file or directory
./test.create.private.un.sh[173]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.un.cp.ile.nm.andump: No such file or directory
Diffs for private.ele.nm.un.cp.ile.nm.andump
diff: ../../test/appsrc/acrnema/private.ele.nm.un.cp.ile.nm.andump: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.un.cp.ile.nm.andump: No such file or directory
./test.create.private.un.sh[175]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.un.cp.ile.nm.dcdump: No such file or directory
Diffs for private.ele.nm.un.cp.ile.nm.dcdump
diff: ../../test/appsrc/acrnema/private.ele.nm.un.cp.ile.nm.dcdump: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.un.cp.ile.nm.dcdump: No such file or directory
./test.create.private.un.sh[177]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.un.cp.ile.nm.odx: No such file or directory
Diffs for private.ele.nm.un.cp.ile.nm.odx
diff: ../../test/appsrc/acrnema/private.ele.nm.un.cp.ile.nm.odx: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.un.cp.ile.nm.odx: No such file or directory
./test.create.private.un.sh[179]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.un.cp.ile.nm.odc: No such file or directory
Diffs for private.ele.nm.un.cp.ile.nm.odc
diff: ../../test/appsrc/acrnema/private.ele.nm.un.cp.ile.nm.odc: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.un.cp.ile.nm.odc: No such file or directory
./test.create.private.un.sh[182]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.un.cp.ele.nm.dccp: No such file or directory
Comparing private.ele.nm.un.cp.ele.nm
cmp: ../../test/appsrc/acrnema/private.ele.nm.un.cp.ele.nm: No such file or directory
cmp: /tmp/test.create.private.un.sh.65081/private.ele.nm.un.cp.ele.nm: No such file or directory
Diffs for private.ele.nm.un.cp.ele.nm.dccp
diff: ../../test/appsrc/acrnema/private.ele.nm.un.cp.ele.nm.dccp: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.un.cp.ele.nm.dccp: No such file or directory
./test.create.private.un.sh[185]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.un.cp.ele.nm.andump: No such file or directory
Diffs for private.ele.nm.un.cp.ele.nm.andump
diff: ../../test/appsrc/acrnema/private.ele.nm.un.cp.ele.nm.andump: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.un.cp.ele.nm.andump: No such file or directory
./test.create.private.un.sh[187]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.un.cp.ele.nm.dcdump: No such file or directory
Diffs for private.ele.nm.un.cp.ele.nm.dcdump
diff: ../../test/appsrc/acrnema/private.ele.nm.un.cp.ele.nm.dcdump: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.un.cp.ele.nm.dcdump: No such file or directory
./test.create.private.un.sh[189]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.un.cp.ele.nm.odx: No such file or directory
Diffs for private.ele.nm.un.cp.ele.nm.odx
diff: ../../test/appsrc/acrnema/private.ele.nm.un.cp.ele.nm.odx: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.un.cp.ele.nm.odx: No such file or directory
./test.create.private.un.sh[191]: can't create /tmp/test.create.private.un.sh.65081/private.ele.nm.un.cp.ele.nm.odc: No such file or directory
Diffs for private.ele.nm.un.cp.ele.nm.odc
diff: ../../test/appsrc/acrnema/private.ele.nm.un.cp.ele.nm.odc: No such file or directory
diff: /tmp/test.create.private.un.sh.65081/private.ele.nm.un.cp.ele.nm.odc: No such file or directory
./test.create.private.un.sh finished
../.././support/testapp: no such image directory as "../.././images/dicom"
Usage: ../.././support/testapp testlist appname options imagedir testlogdir create|compare dump|cp|todc|ancp|filter
make[2]: *** [makefile:282: test] Error 1
make[2]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/acrnema'
testing in ./appsrc/dcdisp...
make[2]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dcdisp'
../.././support/testapp: no such image directory as "../.././images/acrnema"
Usage: ../.././support/testapp testlist appname options imagedir testlogdir create|compare dump|cp|todc|ancp|filter
make[2]: *** [makefile:222: test] Error 1
make[2]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dcdisp'
testing in ./appsrc/dcfile...
make[2]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dcfile'
../.././support/testapp: no such image directory as "../.././images/acrnema"
Usage: ../.././support/testapp testlist appname options imagedir testlogdir create|compare dump|cp|todc|ancp|filter
make[2]: *** [makefile:1827: testdchist] Error 1
make[2]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dcfile'
testing in ./appsrc/dcintro...
make[2]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dcintro'
test in ./appsrc/dcintro done
make[2]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dcintro'
testing in ./appsrc/misc...
make[2]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/misc'
./binpatch.test.sh ../.././test/./appsrc/misc compare
./binpatch.test.sh[42]: can't create /tmp/binpatch.test.sh.65157.src: Read-only file system
binpatch 1  16 l
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.1.16.l.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.1.16.l.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.1.16.l.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.1.16.l.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.1.16.l.dst.od: No such file or directory
binpatch 1  16 b
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.1.16.b.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.1.16.b.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.1.16.b.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.1.16.b.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.1.16.b.dst.od: No such file or directory
binpatch 2  16 l
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.2.16.l.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.2.16.l.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.2.16.l.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.2.16.l.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.2.16.l.dst.od: No such file or directory
binpatch 2  16 b
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.2.16.b.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.2.16.b.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.2.16.b.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.2.16.b.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.2.16.b.dst.od: No such file or directory
binpatch 3  16 l
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.3.16.l.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.3.16.l.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.3.16.l.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.3.16.l.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.3.16.l.dst.od: No such file or directory
binpatch 3  16 b
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.3.16.b.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.3.16.b.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.3.16.b.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.3.16.b.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.3.16.b.dst.od: No such file or directory
binpatch 4  16 l
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.4.16.l.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.4.16.l.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.4.16.l.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.4.16.l.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.4.16.l.dst.od: No such file or directory
binpatch 4  16 b
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.4.16.b.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.4.16.b.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.4.16.b.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.4.16.b.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.4.16.b.dst.od: No such file or directory
binpatch 1  -16 l
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.1.-16.l.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.1.-16.l.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.1.-16.l.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.1.-16.l.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.1.-16.l.dst.od: No such file or directory
binpatch 1  -16 b
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.1.-16.b.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.1.-16.b.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.1.-16.b.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.1.-16.b.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.1.-16.b.dst.od: No such file or directory
binpatch 2  -16 l
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.2.-16.l.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.2.-16.l.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.2.-16.l.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.2.-16.l.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.2.-16.l.dst.od: No such file or directory
binpatch 2  -16 b
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.2.-16.b.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.2.-16.b.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.2.-16.b.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.2.-16.b.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.2.-16.b.dst.od: No such file or directory
binpatch 3  -16 l
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.3.-16.l.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.3.-16.l.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.3.-16.l.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.3.-16.l.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.3.-16.l.dst.od: No such file or directory
binpatch 3  -16 b
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.3.-16.b.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.3.-16.b.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.3.-16.b.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.3.-16.b.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.3.-16.b.dst.od: No such file or directory
binpatch 4  -16 l
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.4.-16.l.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.4.-16.l.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.4.-16.l.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.4.-16.l.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.4.-16.l.dst.od: No such file or directory
binpatch 4  -16 b
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.4.-16.b.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.4.-16.b.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.4.-16.b.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.4.-16.b.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.4.-16.b.dst.od: No such file or directory
binpatch 1  0x7f l
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.1.0x7f.l.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.1.0x7f.l.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.1.0x7f.l.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.1.0x7f.l.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.1.0x7f.l.dst.od: No such file or directory
binpatch 1  0x7f b
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.1.0x7f.b.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.1.0x7f.b.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.1.0x7f.b.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.1.0x7f.b.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.1.0x7f.b.dst.od: No such file or directory
binpatch 1  0xff l
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.1.0xff.l.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.1.0xff.l.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.1.0xff.l.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.1.0xff.l.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.1.0xff.l.dst.od: No such file or directory
binpatch 1  0xff b
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.1.0xff.b.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.1.0xff.b.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.1.0xff.b.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.1.0xff.b.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.1.0xff.b.dst.od: No such file or directory
binpatch 1  0x7fff l
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.1.0x7fff.l.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.1.0x7fff.l.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.1.0x7fff.l.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.1.0x7fff.l.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.1.0x7fff.l.dst.od: No such file or directory
binpatch 1  0x7fff b
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.1.0x7fff.b.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.1.0x7fff.b.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.1.0x7fff.b.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.1.0x7fff.b.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.1.0x7fff.b.dst.od: No such file or directory
binpatch 2  0x7fff l
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.2.0x7fff.l.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.2.0x7fff.l.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.2.0x7fff.l.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.2.0x7fff.l.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.2.0x7fff.l.dst.od: No such file or directory
binpatch 2  0x7fff b
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.2.0x7fff.b.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.2.0x7fff.b.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.2.0x7fff.b.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.2.0x7fff.b.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.2.0x7fff.b.dst.od: No such file or directory
binpatch 3  0x7fff l
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.3.0x7fff.l.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.3.0x7fff.l.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.3.0x7fff.l.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.3.0x7fff.l.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.3.0x7fff.l.dst.od: No such file or directory
binpatch 3  0x7fff b
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.3.0x7fff.b.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.3.0x7fff.b.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.3.0x7fff.b.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.3.0x7fff.b.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.3.0x7fff.b.dst.od: No such file or directory
binpatch 4  0x7fff l
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.4.0x7fff.l.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.4.0x7fff.l.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.4.0x7fff.l.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.4.0x7fff.l.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.4.0x7fff.l.dst.od: No such file or directory
binpatch 4  0x7fff b
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.4.0x7fff.b.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.4.0x7fff.b.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.4.0x7fff.b.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.4.0x7fff.b.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.4.0x7fff.b.dst.od: No such file or directory
binpatch 1  0xffff l
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.1.0xffff.l.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.1.0xffff.l.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.1.0xffff.l.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.1.0xffff.l.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.1.0xffff.l.dst.od: No such file or directory
binpatch 1  0xffff b
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.1.0xffff.b.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.1.0xffff.b.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.1.0xffff.b.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.1.0xffff.b.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.1.0xffff.b.dst.od: No such file or directory
binpatch 2  0xffff l
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.2.0xffff.l.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.2.0xffff.l.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.2.0xffff.l.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.2.0xffff.l.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.2.0xffff.l.dst.od: No such file or directory
binpatch 2  0xffff b
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.2.0xffff.b.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.2.0xffff.b.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.2.0xffff.b.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.2.0xffff.b.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.2.0xffff.b.dst.od: No such file or directory
binpatch 3  0xffff l
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.3.0xffff.l.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.3.0xffff.l.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.3.0xffff.l.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.3.0xffff.l.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.3.0xffff.l.dst.od: No such file or directory
binpatch 3  0xffff b
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.3.0xffff.b.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.3.0xffff.b.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.3.0xffff.b.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.3.0xffff.b.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.3.0xffff.b.dst.od: No such file or directory
binpatch 4  0xffff l
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.4.0xffff.l.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.4.0xffff.l.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.4.0xffff.l.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.4.0xffff.l.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.4.0xffff.l.dst.od: No such file or directory
binpatch 4  0xffff b
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.4.0xffff.b.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.4.0xffff.b.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.4.0xffff.b.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.4.0xffff.b.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.4.0xffff.b.dst.od: No such file or directory
binpatch 4  0x7fffff l
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.4.0x7fffff.l.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.4.0x7fffff.l.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.4.0x7fffff.l.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.4.0x7fffff.l.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.4.0x7fffff.l.dst.od: No such file or directory
binpatch 4  0x7fffff b
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.4.0x7fffff.b.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.4.0x7fffff.b.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.4.0x7fffff.b.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.4.0x7fffff.b.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.4.0x7fffff.b.dst.od: No such file or directory
binpatch 4  0xffffff l
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.4.0xffffff.l.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.4.0xffffff.l.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.4.0xffffff.l.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.4.0xffffff.l.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.4.0xffffff.l.dst.od: No such file or directory
binpatch 4  0xffffff b
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.4.0xffffff.b.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.4.0xffffff.b.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.4.0xffffff.b.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.4.0xffffff.b.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.4.0xffffff.b.dst.od: No such file or directory
binpatch 4  0x7fffffff l
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.4.0x7fffffff.l.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.4.0x7fffffff.l.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.4.0x7fffffff.l.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.4.0x7fffffff.l.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.4.0x7fffffff.l.dst.od: No such file or directory
binpatch 4  0x7fffffff b
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.4.0x7fffffff.b.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.4.0x7fffffff.b.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.4.0x7fffffff.b.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.4.0x7fffffff.b.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.4.0x7fffffff.b.dst.od: No such file or directory
binpatch 4  0xffffffff l
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.4.0xffffffff.l.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.4.0xffffffff.l.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.4.0xffffffff.l.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.4.0xffffffff.l.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.4.0xffffffff.l.dst.od: No such file or directory
binpatch 4  0xffffffff b
Abort - File open for read failed - "/tmp/binpatch.test.sh.65157.src"
Abort - File open for write failed - "/tmp/binpatch.test.sh.65157.4.0xffffffff.b.dst"
Usage: ./binpatch [-if|-input-file inputfile] [-of|-output-file outputfile] [-v|-verbose] [-r offset length string padvalue] [-i offset length integervalue l|b] [inputfile[outputfile]] <inputfile >outputfile
./binpatch.test.sh[109]: can't create /tmp/binpatch.test.sh.65157.4.0xffffffff.b.dst.od: Read-only file system
binpatch:     nothing stored  to compare binary
rm: /tmp/binpatch.test.sh.65157.4.0xffffffff.b.dst: No such file or directory
binpatch:     nothing stored  to compare od
./binpatch.test.sh[109]: cat: /tmp/binpatch.test.sh.65157.4.0xffffffff.b.dst.od: No such file or directory
rm: /tmp/binpatch.test.sh.65157.4.0xffffffff.b.dst.od: No such file or directory
test in ./appsrc/misc done
make[2]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/misc'
testing in ./appsrc/simple...
make[2]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/simple'
testing in ./appsrc/simple/ge9800...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/simple/ge9800'
../../.././support/testapp: no such image directory as "../../.././images/ge9800"
Usage: ../../.././support/testapp testlist appname options imagedir testlogdir create|compare dump|cp|todc|ancp|filter
make[3]: *** [makefile:244: test] Error 1
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/simple/ge9800'
testing in ./appsrc/simple/genesis...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/simple/genesis'
../../.././support/testapp: no such image directory as "../../.././images/genesis"
Usage: ../../.././support/testapp testlist appname options imagedir testlogdir create|compare dump|cp|todc|ancp|filter
make[3]: *** [makefile:222: test] Error 1
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/simple/genesis'
testing in ./appsrc/simple/pace...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/simple/pace'
../../.././support/testapp: no such image directory as "../../.././images/pace"
Usage: ../../.././support/testapp testlist appname options imagedir testlogdir create|compare dump|cp|todc|ancp|filter
make[3]: *** [makefile:222: test] Error 1
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/simple/pace'
testing in ./appsrc/simple/signa...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/simple/signa'
../../.././support/testapp: no such image directory as "../../.././images/signa"
Usage: ../../.././support/testapp testlist appname options imagedir testlogdir create|compare dump|cp|todc|ancp|filter
make[3]: *** [makefile:222: test] Error 1
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/simple/signa'
testing in ./appsrc/simple/somatom...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/simple/somatom'
../../.././support/testapp: no such image directory as "../../.././images/somatom"
Usage: ../../.././support/testapp testlist appname options imagedir testlogdir create|compare dump|cp|todc|ancp|filter
make[3]: *** [makefile:222: test] Error 1
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/simple/somatom'
testing in ./appsrc/simple/sytec...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/simple/sytec'
../../.././support/testapp: no such image directory as "../../.././images/sytec"
Usage: ../../.././support/testapp testlist appname options imagedir testlogdir create|compare dump|cp|todc|ancp|filter
make[3]: *** [makefile:222: test] Error 1
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/simple/sytec'
testing in ./appsrc/simple/vision...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/simple/vision'
../../.././support/testapp: no such image directory as "../../.././images/vision"
Usage: ../../.././support/testapp testlist appname options imagedir testlogdir create|compare dump|cp|todc|ancp|filter
make[3]: *** [makefile:222: test] Error 1
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/simple/vision'
make[2]: *** [Makefile:224: test] Error 2
make[2]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/simple'
testing in ./appsrc/dconvert...
make[2]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert'
testing in ./appsrc/dconvert/support...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/support'
test in ./appsrc/dconvert/support done
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/support'
testing in ./appsrc/dconvert/xxxx...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/xxxx'
test in ./appsrc/dconvert/xxxx done
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/xxxx'
testing in ./appsrc/dconvert/pace...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/pace'
../../.././support/testapp: no such image directory as "../../.././images/pace"
Usage: ../../.././support/testapp testlist appname options imagedir testlogdir create|compare dump|cp|todc|ancp|filter
make[3]: *** [makefile:256: test] Error 1
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/pace'
testing in ./appsrc/dconvert/imtn...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/imtn'
../../.././support/testapp: no such image directory as "../../.././images/imatron"
Usage: ../../.././support/testapp testlist appname options imagedir testlogdir create|compare dump|cp|todc|ancp|filter
make[3]: *** [makefile:246: test] Error 1
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/imtn'
testing in ./appsrc/dconvert/gen...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/gen'
./testy2k.sh ../../.././images/genesis ../../.././test/./appsrc/dconvert/gen compare
./testy2k.sh: no such image directory as "../../.././images/genesis" or test.ct or test.mr missing
Usage: ./testy2k.sh testlogdir create|compare
make[3]: *** [makefile:256: test] Error 1
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/gen'
testing in ./appsrc/dconvert/gaw...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/gaw'
../../.././support/testapp: no such image directory as "../../.././images/genaw/ct"
Usage: ../../.././support/testapp testlist appname options imagedir testlogdir create|compare dump|cp|todc|ancp|filter
make[3]: *** [makefile:246: test] Error 1
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/gaw'
testing in ./appsrc/dconvert/shim...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/shim'
../../.././support/testapp: no such image directory as "../../.././images/shimadzu"
Usage: ../../.././support/testapp testlist appname options imagedir testlogdir create|compare dump|cp|todc|ancp|filter
make[3]: *** [makefile:246: test] Error 1
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/shim'
testing in ./appsrc/dconvert/somp...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/somp'
../../.././support/testapp: no such image directory as "../../.././images/somplus"
Usage: ../../.././support/testapp testlist appname options imagedir testlogdir create|compare dump|cp|todc|ancp|filter
make[3]: *** [makefile:246: test] Error 1
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/somp'
testing in ./appsrc/dconvert/himr...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/himr'
../../.././support/testapp: no such image directory as "../../.././images/himr"
Usage: ../../.././support/testapp testlist appname options imagedir testlogdir create|compare dump|cp|todc|ancp|filter
make[3]: *** [makefile:256: test] Error 1
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/himr'
testing in ./appsrc/dconvert/pq...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/pq'
../../.././support/testapp: no such image directory as "../../.././images/pq"
Usage: ../../.././support/testapp testlist appname options imagedir testlogdir create|compare dump|cp|todc|ancp|filter
make[3]: *** [makefile:270: test] Error 1
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/pq'
testing in ./appsrc/dconvert/toshiba...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/toshiba'
test in ./appsrc/dconvert/toshiba done
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/toshiba'
testing in ./appsrc/dconvert/signa...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/signa'
Makefile:192: *** multiple target patterns.  Stop.
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/signa'
testing in ./appsrc/dconvert/ge9800...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/ge9800'
../../.././support/testapp: no such image directory as "../../.././images/ge9800"
Usage: ../../.././support/testapp testlist appname options imagedir testlogdir create|compare dump|cp|todc|ancp|filter
make[3]: *** [makefile:246: test] Error 1
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert/ge9800'
make[2]: *** [Makefile:224: test] Error 2
make[2]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc/dconvert'
make[1]: *** [Makefile:224: test] Error 2
make[1]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/appsrc'
testing in ./config...
make[1]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/config'
test in ./config done
make[1]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/config'
testing in ./libsrc...
make[1]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc'
testing in ./libsrc/standard...
make[2]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/standard'
testing in ./libsrc/standard/elmdict...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/standard/elmdict'
test in ./libsrc/standard/elmdict done
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/standard/elmdict'
testing in ./libsrc/standard/module...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/standard/module'
test in ./libsrc/standard/module done
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/standard/module'
testing in ./libsrc/standard/iodcomp...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/standard/iodcomp'
test in ./libsrc/standard/iodcomp done
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/standard/iodcomp'
testing in ./libsrc/standard/strval...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/standard/strval'
test in ./libsrc/standard/strval done
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/standard/strval'
make[2]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/standard'
testing in ./libsrc/include...
make[2]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/include'
testing in ./libsrc/include/dcdisp...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/include/dcdisp'
test in ./libsrc/include/dcdisp done
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/include/dcdisp'
testing in ./libsrc/include/dconvert...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/include/dconvert'
test in ./libsrc/include/dconvert done
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/include/dconvert'
testing in ./libsrc/include/dctool...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/include/dctool'
test in ./libsrc/include/dctool done
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/include/dctool'
testing in ./libsrc/include/generic...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/include/generic'
test in ./libsrc/include/generic done
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/include/generic'
testing in ./libsrc/include/locale...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/include/locale'
test in ./libsrc/include/locale done
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/include/locale'
testing in ./libsrc/include/ourdisp...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/include/ourdisp'
test in ./libsrc/include/ourdisp done
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/include/ourdisp'
testing in ./libsrc/include/pixeldat...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/include/pixeldat'
test in ./libsrc/include/pixeldat done
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/include/pixeldat'
make[2]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/include'
testing in ./libsrc/lib...
make[2]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/lib'
test in ./libsrc/lib done
make[2]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/lib'
testing in ./libsrc/src...
make[2]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src'
testing in ./libsrc/src/dcdisp...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dcdisp'
test in ./libsrc/src/dcdisp done
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dcdisp'
testing in ./libsrc/src/dctool...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dctool'
test in ./libsrc/src/dctool done
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dctool'
testing in ./libsrc/src/generic...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/generic'
test in ./libsrc/src/generic done
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/generic'
testing in ./libsrc/src/locale...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/locale'
test in ./libsrc/src/locale done
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/locale'
testing in ./libsrc/src/ourdisp...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/ourdisp'
test in ./libsrc/src/ourdisp done
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/ourdisp'
testing in ./libsrc/src/dconvert...
make[3]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert'
testing in ./libsrc/src/dconvert/support...
make[4]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert/support'
test in ./libsrc/src/dconvert/support done
make[4]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert/support'
testing in ./libsrc/src/dconvert/pace...
make[4]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert/pace'
test in ./libsrc/src/dconvert/pace done
make[4]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert/pace'
testing in ./libsrc/src/dconvert/xxxx...
make[4]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert/xxxx'
test in ./libsrc/src/dconvert/xxxx done
make[4]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert/xxxx'
testing in ./libsrc/src/dconvert/imtn...
make[4]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert/imtn'
test in ./libsrc/src/dconvert/imtn done
make[4]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert/imtn'
testing in ./libsrc/src/dconvert/gen...
make[4]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert/gen'
test in ./libsrc/src/dconvert/gen done
make[4]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert/gen'
testing in ./libsrc/src/dconvert/gaw...
make[4]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert/gaw'
test in ./libsrc/src/dconvert/gaw done
make[4]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert/gaw'
testing in ./libsrc/src/dconvert/shim...
make[4]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert/shim'
test in ./libsrc/src/dconvert/shim done
make[4]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert/shim'
testing in ./libsrc/src/dconvert/somp...
make[4]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert/somp'
test in ./libsrc/src/dconvert/somp done
make[4]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert/somp'
testing in ./libsrc/src/dconvert/himr...
make[4]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert/himr'
test in ./libsrc/src/dconvert/himr done
make[4]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert/himr'
testing in ./libsrc/src/dconvert/pq...
make[4]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert/pq'
test in ./libsrc/src/dconvert/pq done
make[4]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert/pq'
testing in ./libsrc/src/dconvert/signa...
make[4]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert/signa'
test in ./libsrc/src/dconvert/signa done
make[4]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert/signa'
testing in ./libsrc/src/dconvert/ge9800...
make[4]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert/ge9800'
test in ./libsrc/src/dconvert/ge9800 done
make[4]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert/ge9800'
make[3]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src/dconvert'
make[2]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/src'
testing in ./libsrc/support...
make[2]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/support'
test in ./libsrc/support done
make[2]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/support'
testing in ./libsrc/docs...
make[2]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/docs'
test in ./libsrc/docs done
make[2]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc/docs'
make[1]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/libsrc'
testing in ./support...
make[1]: Entering directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/support'
test in ./support done
make[1]: Leaving directory '/storage/Users/currentUser/tmp/dicom3tools-1.00-20240118131615/src/work/support'
<!-- END VERBATIM LOG -->
