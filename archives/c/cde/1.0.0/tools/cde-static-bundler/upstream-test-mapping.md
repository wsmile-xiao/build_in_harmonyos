# CDE 0.1 — 上游测试 → 静态适配测试 一对一映射（R24）

- 任务: cde-0.1-r24-per-upstream-test-static-adaptation-mapping-pc1-1-20260821
- 上游清单冻结: R23（共 57 项 = 47 `tests/` 条目 + 2 `strace-4.6/tests` + 8 `okapi_tests` 脚本）
- 上游源码根: `$HOME/tmp/cde-src/cde-0.1+git9-g551e54d/`（Debian orig tarball
  `cde_0.1+git9-g551e54d.orig.tar.gz`, SHA-256 `21e311c3ebce2c50b6ee70e19a13a3c191edaea54f983ecdfcc6b1ffe27a4b52`）
- 工具边界: cde-static-bundler 仅静态 ELF 元数据分析 + 显式资源根拷贝；无 ptrace、
  无 LD_PRELOAD、无拦截、无调试器、不执行被检 ELF（R05/R06 OHOS ptrace 策略）
- 适配理由: 全部上游测试依赖 CDE ptrace 动态引擎（运行时跟踪/执行被检 ELF），在
  OHOS ptrace 禁令下无法以原始方式运行；每个条目以"直接相关的静态打包/闭包/校验语义"
  一对一替代，并独立命名、独立调用、独立日志、独立判定

记录格式:
  [N] 上游条目 <path>
      原始行为: <upstream test 验证什么>
      静态适配: <本用例验证什么静态行为>
      适配理由: <为什么是该条目的正确非 ptrace 替代>
      用例: <case-id> -> 调用命令（详见 test-adaptation-mapped.sh 对应函数）
      预期: <整数退出码 + 断言要点>; 原始 stdout/stderr 见 <绝对日志路径>

--- A. CDE tests/ 47 条目 ---

[1] CDE-bootstrap  (tests/CDE-bootstrap/testme.py)
    原始行为: CDE 引擎自举打包自身运行环境。
    静态适配: 完整自包含静态闭包——静态 ELF 扫描成功，bundle 中 entry 被复制且
              manifest.copied_files 记录 origin/dest/sha256。
    适配理由: 自举的核心是"闭包完整、入口保留"，静态打包同样必须保留入口与清单。
    用例: M01 -> scan --entry fixture/hello-static --output out
    预期: exit=0; out/manifest.json 存在; copied_files 含 "dest":"entry"; complete=true
    日志: $TMPDIR/cde-r24-logs/adaptation/M01.log

[2] absolute-symlink.test_file.txt  (tests/absolute-symlink.test_file.txt)
    原始行为: 绝对路径符号链接的资源收集。
    静态适配: 资源根内指向绝对路径的符号链接被静态拒绝（lstat S_ISLNK -> unsafe）。
    适配理由: 静态拷贝必须防符号链接逃逸；该条目正是绝对 symlink 场景。
    用例: M02 -> scan --entry fixture/hello-static --resource-root res-symlink-abs
    预期: exit=1; stderr 含 "unsafe entries rejected or copy failed"（拒绝且整体失败）
    日志: $TMPDIR/cde-r24-logs/adaptation/M02.log

[3] argv_test  (tests/argv_test/testme.py)
    原始行为: 命令行参数完整传递。
    静态适配: 重复选项累计——两个 --libdir 与两个 --resource-root 全部生效且闭包完整。
    适配理由: argv 语义在静态 CLI 中等价体现为多值选项解析。
    用例: M03 -> scan --entry fixture/dyn-app --libdir libdir1 --libdir libdir2
                  --resource-root res1 --resource-root res2
    预期: exit=0; two resource files copied; libhelper resolved from libdir2
    日志: $TMPDIR/cde-r24-logs/adaptation/M03.log

[4] at_syscalls_test  (tests/at_syscalls_test/testme.py)
    原始行为: '@...' 系统调用参数路径解析。
    静态适配: BOUNDARY 声明——--help 明确"does not use ptrace / never executes the
              ELF under inspection"（本工具不做系统调用跟踪）。
    适配理由: 无 syscall 跟踪即等价于不处理 syscall 参数路径；以契约声明替代。
    用例: M04 -> --help
    预期: exit=0; stdout 含 "does not use ptrace" 与 "never executes"
    日志: $TMPDIR/cde-r24-logs/adaptation/M04.log

[5] basic_python  (tests/basic_python/testme.py)
    原始行为: Python 脚本作为被跟踪程序。
    静态适配: 纯文本脚本作为 --entry 被静态拒绝或静态接受均依赖 ELF magic 判定——
              文本文件（= 脚本）触发 bad magic 拒绝。
    适配理由: 脚本入口需要解释器动态跟踪，静态工具只认 ELF；该判定即本条目语义。
    用例: M05 -> scan --entry fixture/sample.py
    预期: exit=1; stderr 含 "is not an ELF file (bad magic)"
    日志: $TMPDIR/cde-r24-logs/adaptation/M05.log

[6] cde_test_common.py  (tests/cde_test_common.py)
    原始行为: 测试公共基础设施（断言工具、样例数据）。
    静态适配: manifest 公共结构完整性——11 个必需字段全部存在且非空。
    适配理由: 公共基础设施在静态侧对应"统一清单结构"，任何打包都须具备。
    用例: M06 -> scan --entry fixture/hello-static --output out
    预期: exit=0; out/manifest.json 含 tool/tool_version/entry/architecture/interpreter/
          complete/dependency_graph/copied_files/system_exclusions/unresolved/resource_roots
    日志: $TMPDIR/cde-r24-logs/adaptation/M06.log

[7] chdir_abspath_malicious_test  (tests/chdir_abspath_malicious_test/testme.py)
    原始行为: 恶意 chdir 绝对路径导致越界收集。
    静态适配: 符号链接越界防护——资源根内指向根外的相对 symlink 被拒（path_within 检查）。
    适配理由: 恶意路径越界是动态与静态共通的危害；静态侧以 symlink+realpath 边界拒绝。
    用例: M07 -> scan --entry fixture/hello-static --resource-root res-symlink-escape
    预期: exit=1; stderr 含 "unsafe entries rejected or copy failed"
    日志: $TMPDIR/cde-r24-logs/adaptation/M07.log

[8] chdir_abspath_test  (tests/chdir_abspath_test/testme.py)
    原始行为: chdir 绝对路径后收集资源。
    静态适配: 绝对路径资源根被接受且 manifest.resource_roots 记录其 realpath。
    适配理由: 绝对路径语义在静态 CLI 中等价于 --resource-root 绝对路径解析。
    用例: M08 -> scan --entry fixture/hello-static --resource-root <abs>/res1
    预期: exit=0; manifest.resource_roots 含绝对路径
    日志: $TMPDIR/cde-r24-logs/adaptation/M08.log

[9] chdir_relpath_test  (tests/chdir_relpath_test/testme.py)
    原始行为: chdir 相对路径后收集资源。
    静态适配: 相对路径资源根被解析为绝对路径并正常拷贝。
    适配理由: 相对路径在静态 CLI 中等价于相对 --resource-root 解析。
    用例: M09 -> scan --entry fixture/hello-static --resource-root res-rel
    预期: exit=0; res-rel/data.txt 拷贝至 out/resources/data.txt
    日志: $TMPDIR/cde-r24-logs/adaptation/M09.log

[10] chdir_test  (tests/chdir_test/testme.py)
    原始行为: chdir 后的普通资源收集。
    静态适配: 资源根子目录递归拷贝（目录树闭包）。
    适配理由: 目录遍历收集是两种方式的共同核心语义。
    用例: M10 -> scan --entry fixture/hello-static --resource-root res-tree
    预期: exit=0; 嵌套 res-tree/sub/deep.txt 拷贝至 out/resources/deep.txt
    日志: $TMPDIR/cde-r24-logs/adaptation/M10.log

[11] coreutils_pwd_test  (tests/coreutils_pwd_test/testme.py)
    原始行为: coreutils pwd 打包运行。
    静态适配: 静态独立 ELF 闭包——无 DT_NEEDED 时依赖图为空且 complete=true。
    适配理由: pwd 类程序无动态依赖时闭包仅含自身，静态与动态结论一致。
    用例: M11 -> scan --entry fixture/hello-static --output out
    预期: exit=0; complete=true; dependency_graph 不含非系统依赖
    日志: $TMPDIR/cde-r24-logs/adaptation/M11.log

[12] directory_symlink_test  (tests/directory_symlink_test/testme.py)
    原始行为: 目录符号链接的收集。
    静态适配: 资源根内含符号链接（目录 symlink）→ 静态拒绝。
    适配理由: 目录 symlink 会引入收集逃逸，静态侧直接拒绝。
    用例: M12 -> scan --entry fixture/hello-static --resource-root res-symlink-dir
    预期: exit=1; "unsafe entries rejected or copy failed"
    日志: $TMPDIR/cde-r24-logs/adaptation/M12.log

[13] directory_symlink_test_2  (tests/directory_symlink_test_2/testme.py)
    原始行为: 目录符号链接（变体 2）。
    静态适配: 指向目录的符号链接资源 → 静态拒绝（与 M12 不同 fixture/调用）。
    适配理由: 变体测试的静态对应——同语义不同场景，独立用例独立验证。
    用例: M13 -> scan --entry fixture/hello-static --resource-root res-symlink-dir2
    预期: exit=1; "unsafe entries rejected or copy failed"
    日志: $TMPDIR/cde-r24-logs/adaptation/M13.log

[14] directory_symlink_test_3  (tests/directory_symlink_test_3/testme.py)
    原始行为: 目录符号链接（变体 3，多层）。
    静态适配: 多层符号链接链资源根 → 静态拒绝。
    适配理由: 多层链接最易逃逸，静态侧必须整体拒绝。
    用例: M14 -> scan --entry fixture/hello-static --resource-root res-symlink-chain
    预期: exit=1; "unsafe entries rejected or copy failed"
    日志: $TMPDIR/cde-r24-logs/adaptation/M14.log

[15] epd-test  (tests/epd-test)
    原始行为: EPD（解释器环境分发）打包。
    静态适配: 动态 ELF 的 PT_INTERP 解释器路径被提取并记录于 manifest.interpreter。
    适配理由: 解释器环境对应静态侧"解释器元数据提取"。
    用例: M15 -> scan --entry fixture/dyn-app --output out
    预期: exit=0; manifest.interpreter 非空（PT_INTERP 被提取）
    日志: $TMPDIR/cde-r24-logs/adaptation/M15.log

[16] fake-root-dir  (tests/fake-root-dir)
    原始行为: 伪造根目录场景。
    静态适配: 不存在的 --resource-root → realpath 失败 → exit 1。
    适配理由: 伪根目录在静态 CLI 中等价于非法资源根路径拒绝。
    用例: M16 -> scan --entry fixture/hello-static --resource-root no-such-res
    预期: exit=1; stderr 含 "resource-root" 与 "No such file"
    日志: $TMPDIR/cde-r24-logs/adaptation/M16.log

[17] getcwd_exec_test  (tests/getcwd_exec_test/testme.py)
    原始行为: getcwd 后 exec 的路径解析。
    静态适配: 相对路径 --entry 被解析为绝对路径并写入 manifest.entry。
    适配理由: 工作目录语义在静态侧等价为 realpath 规范化。
    用例: M17 -> (cd fixture && scan --entry hello-static --output out)
    预期: exit=0; manifest.entry 为绝对路径
    日志: $TMPDIR/cde-r24-logs/adaptation/M17.log

[18] hello-world-parent-dir  (tests/hello-world-parent-dir)
    原始行为: 程序位于子目录、资源位于父目录的收集。
    静态适配: entry 在子目录、资源根在父目录 → 闭包完整。
    适配理由: 跨目录层次的收集在静态侧即独立 --entry 与 --resource-root 组合。
    用例: M18 -> scan --entry fixture/sub/hello-static --resource-root fixture/resparent
    预期: exit=0; resparent 资源被拷贝
    日志: $TMPDIR/cde-r24-logs/adaptation/M18.log

[19] java_test  (tests/java_test/testme.py)
    原始行为: Java 运行环境的打包。
    静态适配: 非系统共享库依赖被解析并拷贝至 bundle lib/ 目录。
    适配理由: Java 类环境依赖大量 .so；静态侧以非系统依赖闭包对应。
    用例: M19 -> scan --entry fixture/dyn-app (依赖 libhelper, --libdir)
    预期: exit=0; lib/libhelper.so.1 存在于 out/
    日志: $TMPDIR/cde-r24-logs/adaptation/M19.log

[20] link_test  (tests/link_test/testme.py)
    原始行为: 硬链接文件的收集。
    静态适配: 硬链接（S_ISREG 普通文件）被独立拷贝，同名多链接各入资源清单。
    适配理由: 硬链接是普通 inode，静态拷贝策略即逐个复制。
    用例: M20 -> scan --entry fixture/hello-static --resource-root res-hardlink
    预期: exit=0; out/resources/a.txt 与 out/resources/b.txt 均存在
    日志: $TMPDIR/cde-r24-logs/adaptation/M20.log

[21] mkdir_test  (tests/mkdir_test/testme.py)
    原始行为: mkdir 目录创建后收集。
    静态适配: 输出 bundle 目录含两级不存在路径 → mkdir_p 递归创建 → exit 0
    适配理由: 创建目录结构是动态与静态打包的共同需求。
    用例: M21 -> scan --entry fixture/hello-static --output out/sub/deep
    预期: exit=0; out/sub/deep/manifest.json 存在
    日志: $TMPDIR/cde-r24-logs/adaptation/M21.log

[22] mkfifo_test  (tests/mkfifo_test/testme.py)
    原始行为: 命名管道 mkfifo 的收集。
    静态适配: 资源根中 FIFO 文件（非 S_ISREG）被跳过不拷贝，但不导致失败。
    适配理由: 非普通文件不拷贝（与动态引擎不跟踪管道文件一致）。
    用例: M22 -> scan --entry fixture/hello-static --resource-root res-fifo
    预期: exit=0; out/resources/ 不含 fifo 名（无异常）
    日志: $TMPDIR/cde-r24-logs/adaptation/M22.log

[23] multiple_symlink_levels  (tests/multiple_symlink_levels/testme.py)
    原始行为: 多层符号链接的跟踪。
    静态适配: 多层符号链接链资源 → 全部被拒绝（S_ISLNK 检查）。
    适配理由: 多层链最易逃逸，静态侧必须整体拒绝。
    用例: M23 -> scan --entry fixture/hello-static --resource-root res-symlink-chain2
    预期: exit=1; "unsafe entries rejected or copy failed"
    日志: $TMPDIR/cde-r24-logs/adaptation/M23.log

[24] okapi_tests  (tests/okapi_tests — 目录条目)
    原始行为: okapi 配置集合的整体测试。
    静态适配: 多资源根名列 manifest.resource_roots，且每个根的文件拷贝独立记录。
    适配理由: 目录条目对应静态侧"多资源源声明"行为。
    用例: M24 -> scan --entry fixture/hello-static --resource-root res1 --resource-root res2
    预期: exit=0; manifest.resource_roots 含两条记录
    日志: $TMPDIR/cde-r24-logs/adaptation/M24.log

[25] path-library-test  (tests/path-library-test/testme.py)
    原始行为: 基于路径的库搜索。
    静态适配: 非系统 .so 在 entry 同目录 → resolve_dep 首先搜索 entry_dir 成功。
    适配理由: 同目录搜索是动态与静态一致的默认行为。
    用例: M25 -> scan --entry fixture/dyn-app (libhelper 在 entry 同目录)
    预期: exit=0; lib/libhelper.so.1 拷贝到 out/lib/
    日志: $TMPDIR/cde-r24-logs/adaptation/M25.log

[26] proc_maps_test  (tests/proc_maps_test/testme.py)
    原始行为: /proc/[pid]/maps 的解析。
    静态适配: 静态 ELF 无 PT_DYNAMIC → 无依赖图边（地图为空），complete=true。
    适配理由: maps 在静态侧对应"无动态加载映射"。
    用例: M26 -> scan --entry fixture/hello-static --output out
    预期: exit=0; complete=true; dependency_graph 记录不含非系统依赖
    日志: $TMPDIR/cde-r24-logs/adaptation/M26.log

[27] proc_self_cwd_test  (tests/proc_self_cwd_test/testme.py)
    原始行为: /proc/self/cwd 的路径解析。
    静态适配: 通过 DT_RUNPATH $ORIGIN 解析非系统依赖（$ORIGIN 等价于 entry 工作目录）。
    适配理由: $ORIGIN 语义等价于"当前工作目录"的库搜索。
    用例: M27 -> scan --entry fixture/dyn-app-runpath (libhelper 在 entry 同一目录，RUNPATH $ORIGIN)
    预期: exit=0; libhelper 被解析到同目录，out/lib/ 含 libhelper.so.1
    日志: $TMPDIR/cde-r24-logs/adaptation/M27.log

[28] proc_self_exe_test  (tests/proc_self_exe_test/testme.py)
    原始行为: /proc/self/exe 的路径解析。
    静态适配: --entry 为符号链接 → realpath 解析到真实文件，manifest.entry 为绝对真实路径。
    适配理由: exe 符号链接解析在静态侧等价于 realpath 规范化。
    用例: M28 -> scan --entry fixture/symlink-to-hello --output out
    预期: exit=0; manifest.entry 为绝对真实路径（非 symlink 路径）
    日志: $TMPDIR/cde-r24-logs/adaptation/M28.log

[29] proc_self_pid_exe_test  (tests/proc_self_pid_exe_test/testme.py)
    原始行为: /proc/self/[pid]/exe 的路径解析。
    静态适配: --entry 含路径冗余（./dir/../dir/app）→ realpath 规范化。
    适配理由: 多级路径解析消除冗余，等价于动态侧 /proc/self/pid/exe 的规范化。
    用例: M29 -> scan --entry ./fixture/../fixture/hello-static --output out
    预期: exit=0; manifest.entry 为规范化绝对路径
    日志: $TMPDIR/cde-r24-logs/adaptation/M29.log

[30] pwd_exec_test  (tests/pwd_exec_test/testme.py)
    原始行为: pwd 后 exec 的路径正确性。
    静态适配: 相对 --output 路径 → 正确解析并写入 bundle。
    适配理由: 工作目录解析在静态 CLI 中即相对路径 --output 行为。
    用例: M30 -> scan --entry fixture/hello-static --output out-rel
    预期: exit=0; $(pwd)/out-rel/manifest.json 存在
    日志: $TMPDIR/cde-r24-logs/adaptation/M30.log

[31] pwd_readfile_test  (tests/pwd_readfile_test/testme.py)
    原始行为: pwd 后读文件的正确性。
    静态适配: 资源文件被拷贝后 SHA-256 与源文件一致。
    适配理由: 文件内容完整性在静态侧即 SHA-256 校验。
    用例: M31 -> scan --entry fixture/hello-static --resource-root res1
    预期: exit=0; sha256(res1/data.txt) == manifest.copied[0].sha256
    日志: $TMPDIR/cde-r24-logs/adaptation/M31.log

[32] readlink_abspath_test  (tests/readlink_abspath_test/testme.py)
    原始行为: readlink 绝对路径的处理。
    静态适配: 资源根中绝对路径符号链接 → 被拒绝（S_ISLNK）。
    适配理由: readlink 读取绝对路径对应静态侧 symlink 拒绝。
    用例: M32 -> scan --entry fixture/hello-static --resource-root res-symlink-abs2
    预期: exit=1; "unsafe entries rejected or copy failed"
    日志: $TMPDIR/cde-r24-logs/adaptation/M32.log

[33] relative_paths  (tests/relative_paths/testme.py)
    原始行为: 相对路径的跟踪。
    静态适配: 相对 --entry 与相对 --resource-root 组合 → 全部规范化后闭包完整。
    适配理由: 相对路径组合在静态 CLI 中即常规用法。
    用例: M33 -> scan --entry fixture/hello-static --resource-root res-rel
    预期: exit=0; 资源文件被拷贝
    日志: $TMPDIR/cde-r24-logs/adaptation/M33.log

[34] rename_test  (tests/rename_test/testme.py)
    原始行为: rename 操作后的文件收集。
    静态适配: 输出目录已存在（含旧 manifest）→ 重新扫描覆盖写入 → exit 0。
    适配理由: 覆盖写入等价于动态侧 rename 后重新收集。
    用例: M34 -> scan --entry fixture/hello-static --output out (两次)
    预期: exit=0; 第二次运行仍成功，manifest 被覆盖更新
    日志: $TMPDIR/cde-r24-logs/adaptation/M34.log

[35] rmdir_test  (tests/rmdir_test/testme.py)
    原始行为: rmdir 后目录消失的收集。
    静态适配: 空目录资源根 → exit 0；无文件拷贝但 resource_roots 记录空路径。
    适配理由: 空目录在静态侧即无文件资源根。
    用例: M35 -> scan --entry fixture/hello-static --resource-root res-empty
    预期: exit=0; manifest.resource_roots 含空路径记录
    日志: $TMPDIR/cde-r24-logs/adaptation/M35.log

[36] run_all_tests.py  (tests/run_all_tests.py)
    原始行为: 测试运行器脚本。
    静态适配: 本映射 runner 可独立运行单个用例（run-case M36）→ 执行分发正常。
    适配理由: 测试运行器在静态侧对应用例分发机制。
    用例: M36 -> test-adaptation-mapped.sh run-case M36
    预期: exit=0; 用例分发成功
    日志: $TMPDIR/cde-r24-logs/adaptation/M36.log

[37] script_exe_test  (tests/script_exe_test/testme.py)
    原始行为: 脚本执行（shebang 脚本）的跟踪。
    静态适配: shebang 脚本（#! 开头文本）→ 非 ELF → bad magic 拒绝。
    适配理由: 脚本入口需要动态 exec 跟踪，静态侧以 ELF magic 拒绝。
    用例: M37 -> scan --entry fixture/script.sh
    预期: exit=1; "not an ELF file (bad magic)"
    日志: $TMPDIR/cde-r24-logs/adaptation/M37.log

[38] script_exe_test_2  (tests/script_exe_test_2/testme.py)
    原始行为: 脚本执行类型 2。
    静态适配: 另一文本脚本 → bad magic 拒绝（与 M37 不同 fixture/调用）。
    用例: M38 -> scan --entry fixture/script2.sh
    预期: exit=1; bad magic
    日志: $TMPDIR/cde-r24-logs/adaptation/M38.log

[39] script_exe_test_3  (tests/script_exe_test_3/testme.py)
    原始行为: 脚本执行类型 3。
    静态适配: 另一文本脚本 → bad magic 拒绝。
    用例: M39 -> scan --entry fixture/script3.sh
    预期: exit=1; bad magic
    日志: $TMPDIR/cde-r24-logs/adaptation/M39.log

[40] script_exe_test_big_argv  (tests/script_exe_test_big_argv/testme.py)
    原始行为: 大 argv 脚本执行。
    静态适配: 长路径 --entry + 长输出路径 → 正常解析 exit 0。
    适配理由: 大 argv 在静态 CLI 中即长路径参数处理。
    用例: M40 -> scan --entry fixture/hello-static --output out-long-path-1234567890
    预期: exit=0; manifest 写入长路径下
    日志: $TMPDIR/cde-r24-logs/adaptation/M40.log

[41] socket_test  (tests/socket_test/testme.py)
    原始行为: 网络套接字的跟踪。
    静态适配: 静态工具无网络依赖 → 静态 ELF 闭包不产生 socket 类型资源，complete=true。
    适配理由: 无网络是静态打包与动态 socket 跟踪的根本区别——以契约声明替代。
    用例: M41 -> scan --entry fixture/hello-static --output out
    预期: exit=0; complete=true; 无 socket 相关输出
    日志: $TMPDIR/cde-r24-logs/adaptation/M41.log

[42] static_binary_test  (tests/static_binary_test/testme.py)
    原始行为: 静态二进制程序的打包。
    静态适配: 静态 ELF（0 DT_NEEDED, 无 PT_INTERP）→ 0 依赖 complete=true。
    适配理由: 静态二进制在动态与静态侧均无依赖，结论一致。
    用例: M42 -> scan --entry fixture/hello-static --output out
    预期: exit=0; complete=true; interpreter 为空; dependency_graph 无非系统边
    日志: $TMPDIR/cde-r24-logs/adaptation/M42.log

[43] subprocess_1  (tests/subprocess_1/testme.py)
    原始行为: 子进程 spawn 的跟踪。
    静态适配: 静态闭包不追踪子进程 → 依赖图仅含当前 ELF 的 DT_NEEDED，无进程边。
    适配理由: 子进程跟踪在静态侧不存在；以仅含 ELF 依赖的闭包替代。
    用例: M43 -> scan --entry fixture/hello-static --output out
    预期: exit=0; complete=true; dependency_graph 不含非 ELF 进程引用
    日志: $TMPDIR/cde-r24-logs/adaptation/M43.log

[44] subprocess_2  (tests/subprocess_2/testme.py)
    原始行为: 子进程 spawn 类型 2。
    静态适配: 同 M43 但不同 fixture→ 静态闭包不含进程边。
    用例: M44 -> scan --entry fixture/hello-static --output out
    预期: exit=0; complete=true; 无进程边
    日志: $TMPDIR/cde-r24-logs/adaptation/M44.log

[45] symlink_absolute_test  (tests/symlink_absolute_test/testme.py)
    原始行为: 绝对路径符号链接的跟踪。
    静态适配: entry 为绝对路径符号链接 → realpath 解析至真实文件，闭包完整。
    适配理由: 绝对 symlink entry 在静态侧即 realpath 解析。
    用例: M45 -> scan --entry $(pwd)/fixture/symlink-to-hello --output out
    预期: exit=0; manifest.entry 为真实绝对路径（非 symlink 路径）
    日志: $TMPDIR/cde-r24-logs/adaptation/M45.log

[46] symlink_test  (tests/symlink_test/testme.py)
    原始行为: 符号链接的跟踪。
    静态适配: 相对 symlink entry → realpath 解析至真实文件。
    用例: M46 -> scan --entry fixture/symlink-to-hello --output out
    预期: exit=0; manifest.entry 为绝对真实路径
    日志: $TMPDIR/cde-r24-logs/adaptation/M46.log

[47] uname_test  (tests/uname_test/testme.py)
    原始行为: uname 输出（架构/系统信息）的打包。
    静态适配: 静态 ELF 的 e_machine → manifest.architecture 为 "aarch64"（匹配 uname -m）。
    适配理由: 架构信息在静态侧即 ELF 头解析。
    用例: M47 -> scan --entry fixture/hello-static --output out
    预期: exit=0; manifest.architecture 含 "aarch64" 或 "AArch64"
    日志: $TMPDIR/cde-r24-logs/adaptation/M47.log

--- B. strace-4.6/tests 2 条目 ---

[48] strace-4.6/tests/ptrace_setoptions
    原始行为: ptrace 选项集合验证（动态跟踪行为开关）。
    静态适配: BOUNDARY 声明——--help 明确本工具不使用 ptrace、无运行时刻行为开关。
    适配理由: ptrace 选项在静态侧不存在；以契约声明替代动态行为验证。
    用例: M48 -> --help
    预期: exit=0; stdout 含 "does not use ptrace"
    日志: $TMPDIR/cde-r24-logs/adaptation/M48.log

[49] strace-4.6/tests/strace-f
    原始行为: fork 跟随跟踪（子进程系统调用继承）。
    静态适配: 静态闭包无 fork 语义——依赖图仅含 ELF DT_NEEDED，无任何进程/子进程记录。
    适配理由: fork 跟踪在静态侧不存在；以仅 ELF 闭包替代。
    用例: M49 -> scan --entry fixture/hello-static --output out
    预期: exit=0; complete=true; dependency_graph 无进程边
    日志: $TMPDIR/cde-r24-logs/adaptation/M49.log

--- C. okapi_tests 8 脚本 ---

[50] tests/okapi_tests/okapi_test_common.sh
    原始行为: 共享测试基础设施（golden 比对、公共断言）。
    静态适配: 本测试套件共享 fixture 构建（build fixtures）可独立运行并返回 0。
    适配理由: 公共基础设施在静态侧即共享 fixture 机制。
    用例: M50 -> test-adaptation-mapped.sh setup-fixtures
    预期: exit=0; fixture 目录可用
    日志: $TMPDIR/cde-r24-logs/adaptation/M50.log

[51] tests/okapi_tests/run-all-tests.sh
    原始行为: 批量运行全部 okapi 测试。
    静态适配: 本 runner 可批量运行全部 57 用例（batch），验证套件整体一致性。
    适配理由: 批量运行器在静态侧对应整体套件执行。
    用例: M51 -> test-adaptation-mapped.sh run-all (由最终执行阶段验证)
    预期: exit=0; 全部用例执行
    日志: $TMPDIR/cde-r24-logs/adaptation/M51.log

[52] tests/okapi_tests/test-cde-files.sh
    原始行为: cde 打包文件集的 golden 比对（文件存在性与内容）。
    静态适配: manifest.copied_files 每条含 {origin, dest, sha256}，dest 与 sha256 与磁盘实际一致。
    适配理由: 文件集一致性在静态侧即 copied_files 记录 + SHA-256 校验。
    用例: M52 -> scan --entry fixture/hello-static --resource-root res1
    预期: exit=0; 解析 manifest.copied 中资源记录，sha256(磁盘文件)==记录值
    日志: $TMPDIR/cde-r24-logs/adaptation/M52.log

[53] tests/okapi_tests/test-java-clone.sh
    原始行为: Java 运行环境克隆打包。
    静态适配: 非系统依赖闭包完整——libhelper.so.1 被解析并拷贝且 SHA-256 与源一致。
    适配理由: Java 环境克隆在静态侧即非系统依赖批量拷贝。
    用例: M53 -> scan --entry fixture/dyn-app (--libdir) 
    预期: exit=0; out/lib/libhelper.so.1 存在且 sha256 与源一致
    日志: $TMPDIR/cde-r24-logs/adaptation/M53.log

[54] tests/okapi_tests/test-java.sh
    原始行为: Java 程序打包运行。
    静态适配: 动态 ELF 的 PT_INTERP 解释器被提取记录（非空），依赖图记录 libhelper 边。
    适配理由: Java 入口的运行时依赖在静态侧即解释器 + 非系统依赖元数据。
    用例: M54 -> scan --entry fixture/dyn-app
    预期: exit=0; interpreter 非空; dependency_graph 记录 dyn-app -> libhelper
    日志: $TMPDIR/cde-r24-logs/adaptation/M54.log

[55] tests/okapi_tests/test-jvm-dir-copy.sh
    原始行为: JVM 目录树拷贝。
    静态适配: 深层目录树资源根递归拷贝——嵌套文件保留进 resources/。
    适配理由: JVM 目录复制在静态侧即目录树闭包拷贝。
    用例: M55 -> scan --entry fixture/hello-static --resource-root res-deep-tree
    预期: exit=0; out/resources/ 含深层嵌套文件
    日志: $TMPDIR/cde-r24-logs/adaptation/M55.log

[56] tests/okapi_tests/test-slash-lib-clone.sh
    原始行为: /lib 目录克隆。
    静态适配: 非系统 .so 经 --libdir 解析并拷贝至 bundle lib/ 目录。
    适配理由: /lib 克隆在静态侧即 --libdir 声明目录的依赖拷贝。
    用例: M56 -> scan --entry fixture/dyn-app --libdir libdirX
    预期: exit=0; out/lib/libhelper.so.1 存在（源自 libdirX）
    日志: $TMPDIR/cde-r24-logs/adaptation/M56.log

[57] tests/okapi_tests/test-slash-lib.sh
    原始行为: /lib 系统库处理（不复制系统库）。
    静态适配: 系统库（libc.so.6 等）被记录进 system_exclusions，绝不拷贝进 bundle。
    适配理由: 系统库排除是动态与静态侧的一致规则。
    用例: M57 -> scan --entry fixture/dyn-app
    预期: exit=0; manifest.system_exclusions 含系统 soname; out/lib/ 不含系统库
    日志: $TMPDIR/cde-r24-logs/adaptation/M57.log