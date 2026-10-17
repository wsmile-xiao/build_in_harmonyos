# ===========================================================================
#  https://www.gnu.org/software/autoconf-archive/ax_cxxflags_warn_all.html
# ===========================================================================
#
# SYNOPSIS
#
#   AX_CXXFLAGS_WARN_ALL([VARIABLE], [VALUE])
#
# DESCRIPTION
#
#   Try to find a compiler option that enables most reasonable warnings.
#   This macro is copied from it's C variant. This macro borrows heavily
#   from the AX_CFLAGS_WARN_ALLEXPERIMENTAL macro.
#
#   For the GNU CC compiler it will be -Wall (and -ansi -pedantic) The
#   result is added to the shellvar being CXXFLAGS by default.
#
#   Currently this macro only works with GCC, compilers implicitly
#   derived from GCC, and compilers that have an '-Wall' option, or
#   '-qinfo=all' or '-warn all' options.
#
#   If VARIABLE is not given, it will default to CXXFLAGS
#
#   To make this macro compatible with older autoconf macros, the
#   VARIABLE must be lowercase below since the flag is added to
#   CXXFLAGS, e.g.:
#
#     AX_CXXFLAGS_WARN_ALL([portable_cxxflags])
#
#   The VALUE given is the flag prefix for the given compiler, e.g.:
#
#     AX_CXXFLAGS_WARN_ALL([], [-Wunused])
#
# LICENSE
#
#   Copyright (c) 2008 Guido U. Draheim <guidod@gmx.de>
#   Copyright (c) 2008 Alan Jenkins <alan-jenkins@tuffmail.co.uk>
#
#   This program is free software; you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by the
#   Free Software Foundation; either version 3 of the License, or (at your
#   option) any later version.
#
#   This program is distributed in the hope that it will be useful, but
#   WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
#   Public License for more details.
#
#   You should have received a copy of the GNU General Public License along
#   with this program. If not, see <https://www.gnu.org/licenses/>.
#
#   As a special exception, the respective Autoconf Macro's copyright notice
#   and license terms shall prevail and apply regardless of the version of
#   the GNU General Public License incorporated in this file.

#serial 9

AC_DEFUN([AX_CXXFLAGS_WARN_ALL], [
  AC_REQUIRE([AC_PROG_CXX])
  AC_LANG_PUSH([C++])
  AC_CACHE_CHECK([for C++ compiler warning flags], ax_cv_cxxflags_warn_all, [
    ax_cv_cxxflags_warn_all="unknown"
    for flag in -Wall -Wunused -qinfo=all; do
      AC_COMPILE_IFELSE([AC_LANG_PROGRAM([[int main(void){return 0;}]], [])],
        [ax_cv_cxxflags_warn_all="$flag"; break])
    done
  ])
  AC_LANG_POP([C++])
  AS_IF([test "x$ax_cv_cxxflags_warn_all" != "xunknown"],
    [AS_IF([test -n "$1"],
      [$1="$$1 $ax_cv_cxxflags_warn_all"],
      [CXXFLAGS="$CXXFLAGS $ax_cv_cxxflags_warn_all"])])
])