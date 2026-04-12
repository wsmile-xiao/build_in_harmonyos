# hints/harmonyos.sh - Hints for HarmonyOS/OpenHarmony (aarch64, musl libc)
#
# This hint file is loaded automatically by Configure when building on
# HarmonyOS. It overrides incorrectly detected values for this platform.
#
# See hints/README.hints for the hints file specification.
# Pattern: similar to hints/darwin.sh, hints/aix.sh, etc.

# === Toolchain: LLVM (not GNU) ===
# HarmonyOS uses clang/llvm-ar/llvm-nm/llvm-ranlib
# Set defaults if early Configure detection didn't fire
cc=${cc:-clang}
ar=${ar:-llvm-ar}
nm=${nm:-llvm-nm}
ranlib=${ranlib:-llvm-ranlib}

# === Libraries ===
# musl libc (not glibc) - standard POSIX libs
libs='-lpthread -ldl -lm -lcrypt -lutil -lc'

# === Locale: musl limitations ===
# HarmonyOS shadow.h exists but is incomplete (no getspnam declaration)
i_shadow='undef'
d_getspnam='undef'
HAS_GETSPNAM='undef'

# musl does not provide glibc-specific _NL_* langinfo constants
d_nl_langinfo_l='undef'

# blksize_t is defined in sys/types.h as int, not in sys/stat.h
d_blksize='define'

# === Memory allocation ===
# Use system malloc (perl's MYMALLOC causes SIGSEGV on this platform)
usemymalloc='n'
mallocobj=''

# === Build options ===
# No shared library support yet (DynaLoader needs work)
useshrplib='false'

# === Compiler flags ===
# _GNU_SOURCE needed for some POSIX extensions
# -fno-strict-aliasing required by perl core
ccflags="$ccflags -D_GNU_SOURCE -fno-strict-aliasing -pipe -fstack-protector-strong"
ldflags="$ldflags -fstack-protector-strong"

# === Known issues / future work ===
# - DynaLoader (XS dynamic loading) not yet supported
# - Some locale functions emulated via locale_stub
# - Thread support not tested
