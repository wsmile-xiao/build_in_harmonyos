# io_lib 1.14.9（Staden io_lib / libstaden-read）适配笔记

## 编译环境
- 构建系统: autotools（configure + libtool，2012 年生成脚本）
- 编译日期: 2026-09-30
- 编译器: clang/clang++（OHOS SDK clang 15，profile ohos-aarch64）
- conan: 2.29.1（OHOS 适配版），remote ohpcd
- 状态: built（conan create 全绿）

## 背景（为何适配）
srf/0.1（SRF 序列格式 C++ 实现）的 REQUIRED 依赖：srf 通过
io_lib-config 调用 ZTR/SRF API（ztr_read_header/ztr_read_chunk_hdr/
new_ztr/ztr_add_text 等，已核对 srf/src/SRF_Ztr.cc 与 io_lib/ztr.h
API 兼容）。制品仓无 io_lib → 按 R36 拓扑序先适配发布 io_lib。

## 真实依赖（configure.in）
- zlib（ZLIB_CHECK_CONFIG，--with-zlib=DIR）→ zlib/1.3.1.1
- libcurl（LIBCURL_CHECK_CONFIG）→ libcurl/8.5.0
- bz2 / lzma（AC_CHECK_LIB）→ bzip2/1.0.8 / xz/5.8.3.2
  （注：xz_utils/5.4.5 不存在于 ohpcd，改用 xz/5.8.3.2）

## 编译步骤
```bash
cd archives/i/io_lib/1.14.9
conan create . --build=missing -pr:h ohos-aarch64 -pr:b default
```

## 遇到的问题与解决方案（5 个补丁）
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 unknown build type | 2012 版 config.guess/sub 不识别 aarch64-linux-ohos | 0001：换仓库 2026 版（cp 覆盖式 patch） |
| 2 | config.status: ./confXXXXXX/subs1.awk: Permission denied | configure 安全临时目录 umask 077，HMDFS 上子目录不可执行 | 0002：umask 077→022（commoncpp2 先例） |
| 3 | libtool: syntax error near unexpected token `}` | 生成的 archive_expsym_cmds 用 echo "{ global:" 嵌套双引号，eval 时在 OHOS sh 下损坏 | 0003：改 -retain-symbols-file 直接用导出符号表，消除 .ver echo 管道 |
| 4 | libtool: print: command not found | mksh 探测选中 ECHO='print -r --'（ksh 内建），libtool shebang 是 bash（无 print） | 0004：configure 内两处 echo 探测分支强制走 printf |
| 5 | scram_mt/scram_v3 测试 scramble -t4 Signal 11 | musl 线程默认栈 128KB（glibc 8MB），thread_pool worker 深递归栈溢出 | 0005：pthread_attr_setstacksize 8MB |

## 工具链/打包细节
- conan autotools.install() 强制 DESTDIR=package_folder，与绝对
  --prefix 组合会把产物嵌套到 package/<abs-prefix>/lib/…（包内出现
  storage/ 目录）。修法：package() 用 make target="install"（落私有
  prefix）再 copy 进包（R49 布局）。
- 头文件装在 include/io_lib/，且头间交叉引用 "io_lib/Read.h" →
  cpp_info.includedirs = ["include", "include/io_lib"] 双路径。
- 上游 quirk：新建 chunk 的 ztr_add_text 使 dlength 多计 1（实测
  38 vs 理论 37），消费者测试按下限断言。

## 上游测试三步法（R51）
1. **清点**：tests/Makefile.am TESTS 注册 10 项
   （srf2fasta/srf2fastq/srf_info/srf_filter/srf_index/scram/scram_mt/
   scram_v3/cram_io/java），另有 compare_sam.pl/generate_data.pl 辅助。
2. **运行**（构建目录 + 源码 tests/ 副本，环境变量
   srcdir/top_builddir=build 符号链接/outdir/test.out，日志
   ~/tmp/builds/io_lib-upstream-tests*.log）：
   - 第一轮（无 0005）：8/10，scram_mt/scram_v3 Signal 11
   - 0005 后：**10/10 rc=0**，Signal 11 计数 0（mt-final/v3-final）
   - java.test rc=0（机器无 java，脚本内跳过 Java 段，如实记录）
3. **回填**：10/10（100%），证据行见 manifest.yaml upstream_tests。

## test_package（R34 实质消费者用例）
test_io_lib_ztr.c：new_ztr → 手填 header magic（new_ztr 不初始化，
调用方必须 memcpy ZTR_MAGIC+版本，与 srf SRF_Ztr.cc 一致）→
ztr_add_text(key,value) → fwrite_ztr 写真实文件 → fread_ztr 读回 →
ztr_find_chunks(ZTR_TYPE_TEXT) 校验 data[0]=ZTR_FORM_RAW 与
key\0value 载荷 → delete_ztr。全数据路径，非打印空壳。

## 交付物
- lib/libstaden-read.so（SONAME .so.11，含版本符号链接）+ .la
- include/io_lib/*.h（51 个头文件）
- bin/ 37 个工具（scramble/srf2fasta/srf_info/cram_dump 等，含
  srf 系工具——srf/0.1 生态直接受益）
- lib/pkgconfig/io_lib.pc

## 已知限制
- java.test 的 Java 段在无 JVM 机器跳过（上游设计如此，rc=0）
- curl 支持按 conan libcurl/8.5.0 链接（open_trace_file 远程取数）
