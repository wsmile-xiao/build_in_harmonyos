/* config.h — 为 HarmonyOS PC (aarch64, musl/clang) 手工合成
 * 上游 configure 的探测结果在 OHOS 上的确定性取值；沙箱无 autotools
 * （git tag 无预生成 configure，autogen.sh 依赖 autoconf/automake/libtool）。
 * 只定义已核实存在的特性；不确定的（RWLOCK/SYS_ENDIAN_H 等）一律不定义，
 * 走代码内的 fallback 分支。
 */
#ifndef CTEMPLATE_CONFIG_H
#define CTEMPLATE_CONFIG_H

#define HAVE_STDINT_H 1
#define HAVE_INTTYPES_H 1
#define HAVE_SYS_TYPES_H 1
#define HAVE_SYS_STAT_H 1
#define HAVE_STDLIB_H 1
#define HAVE_STRING_H 1
#define HAVE_STRINGS_H 1
#define HAVE_MEMORY_H 1
#define HAVE_UNISTD_H 1
#define HAVE_DIRENT_H 1
#define HAVE_DLFCN_H 1
#define HAVE_GETOPT_H 1
#define HAVE_GETOPT_LONG 1
#define HAVE_UTIME_H 1
#define HAVE_BYTESWAP_H 1
#define HAVE_ENDIAN_H 1
#define HAVE_PTHREAD 1
#define HAVE_UINT64_T 1
#define HAVE_UINT32_T 1
#define HAVE_NAMESPACES 1
#define HAVE___ATTRIBUTE__ 1
#define HAVE_UNORDERED_MAP 1
/* stl_hash.m4 在 unordered_map 分支的完整 AC_DEFINE 组（本文件此前漏了前 4 个，
 * template.cc 第 32/48 行 `#include <config.h>` + `#include HASH_MAP_H` 都是
 * 非条件包含，宏缺失直接编译失败 —— CI #43779/#43839 实测） */
#define HAVE_HASH_MAP 1
#define HAVE_HASH_SET 1
#define HASH_MAP_H <unordered_map>
#define HASH_SET_H <unordered_set>
#define HASH_NAMESPACE std
/* m4/compiler_characteristics.m4 的 AC_DEFINE_UNQUOTED(PRIuS, "${prefix}u")
 * —— LP64 aarch64 上 prefix=z。template_dictionary.cc 的 `"%" PRIuS` 是非
 * 条件使用，缺定义即 expected ')'（CI #43917 实测） */
#define PRIuS "zu"

#define PACKAGE_NAME "ctemplate"
/* make_tpl_varnames_h.cc Version() 非条件使用 PACKAGE_STRING（CI #44013
 * 实测 expected ')'）；autotools 由 AC_INIT 自动生成，手工合成须补 */
#define PACKAGE_STRING "ctemplate 2.4"
#define PACKAGE_VERSION "2.4"
#define VERSION "2.4"

#endif
