cmake_minimum_required(VERSION 3.15)
project(test_pidgin C)

# pidgin's autotools-only build doesn't install a cmake config — instead
# we let CMakeDeps generate a pidgin::pidgin interface target (R33).
# Note: due to cpp_info.libs=["purple"] being non-empty, the pidgin::pidgin
# target does NOT propagate glib/libxml2 link deps — we link them explicitly.
#
# Team glib/2.84.0 recipe (ohpcd) does NOT use components — it's a flat
# cpp_info.libs list. The CMake target is therefore the aggregate
# `glib::glib` (file_name + "::" + file_name convention; no cmake_target_name
# was set by the recipe).  We link the aggregate once; it transitively
# exposes the .a files for glib-2.0, gobject-2.0, gio-2.0, gmodule-2.0,
# gthread-2.0 — i.e. all six PKG_CHECK_MODULES components from
# configure.ac at once.  Earlier revisions of this file (pre-2026-07-31)
# listed six separate glib::glib-2.0 / glib::gobject-2.0 etc., which were
# correct for conan-center glib 2.72.4 but do not exist for the team's
# recipe and would produce "Target \"glib::glib-2.0\" not found".
#
# libxml2 recipe sets cmake_file_name="LibXml2" and cmake_target_name=
# "LibXml2::LibXml2" so we lookup find_package(LibXml2) (case-sensitive
# on the file name in CONFIG mode).
find_package(pidgin REQUIRED CONFIG)
find_package(glib REQUIRED CONFIG)
find_package(LibXml2 REQUIRED CONFIG)

add_executable(test_pidgin test_pidgin.c)
# Aggregate glib::glib pulls in libglib-2.0, libgobject-2.0, libgio-2.0,
# libgmodule-2.0, libgthread-2.0 — all the symbols libpurple's
# configure.ac PKG_CHECK_MODULES references. Plus libxml2 via
# LibXml2::LibXml2 which is the explicit cmake_target_name from the
# libxml2/2.15.3 recipe.
target_link_libraries(test_pidgin
    pidgin::pidgin
    glib::glib
    LibXml2::LibXml2
)

# ============================================================
# ⚠️ AI-review note (P3): file(GLOB) is a known CMake anti-pattern when used
# for source-file globbing (CMake re-runs are required to pick up new files).
# This codebase uses it for a DIFFERENT purpose: locating glib.h / libxml2.h
# inside the conan cache at *configure* time, not as a build-system source list.
# The pattern is therefore acceptable here, but if a future Conan version
# fixes the components-INTERFACE_INCLUDE_DIRECTORIES bug (referenced below),
# this whole block should be replaced with target_link_libraries(... INTERFACE
# target only) and the file(GLOB) lines deleted.
# ============================================================
#
# R34 / R36: conan-center glib 2.84.0 + libxml2 2.15.3 (team registry) components
# do not always export INTERFACE_INCLUDE_DIRECTORIES via CMakeDeps (conan 2.29
# quirk). Add glib and libxml2 include paths explicitly from conan cache.
# glib needs BOTH include/glib-2.0 (glib.h) and lib/glib-2.0/include
# (glibconfig.h). libxml2 needs include/libxml2/.
#
# Version note 2026-07-31: bumped from glib/2.72.4, libxml2/2.10.3 to the
# team registry versions (glib/2.84.0, libxml2/2.15.3) per maintainer
# feedback. Cache folder hashes differ (e.g. glib/2.84.0 → p/b/glibXXXX,
# libxml2/2.15.3 → p/b/libxmXXXX) but the GLOB patterns below don't
# depend on the full package name — only on the 5-char prefix that
# conan uses for its on-disk package id (`glib`, `libxm`, ...).
#
# IMPORTANT: the prefix conan uses for binary packages is the first 5
# characters of the recipe name. For `libxml2` this is `libxm`, NOT
# `libxml2`. Older revisions of this file used `p/b/libxml2*` which
# never matched (conan folder is `p/b/libxm<hash>`). The xmlversion.h
# filename filter at the end of the glob still disambiguates libxml2
# from any future sibling packages like libxmlcatalog — only libxml2
# installs include/libxml2/libxml/xmlversion.h.
#
# Alternative considered: env-var hardcoded paths (e.g. CONAN_INCLUDE_GLIB).
# Rejected because CI runs across WSL Ubuntu-22.04, GitHub Actions runners,
# and OHOS dev containers — each has different CONAN_HOME layouts. file(GLOB)
# with a pattern is the only path that "just works" everywhere.
#
# Pattern notes:
#   - glib*: stays as-is. "glib" is the full 5-char prefix for `glib` and
#     no other common package starts with "glib".
#   - libxm*: broadened from "libxml2*" (which never matched the conan
#     on-disk layout — see "IMPORTANT" above). Still disambiguates via
#     the xmlversion.h filename at the end of the glob.
if(NOT DEFINED CONAN_HOME)
    if(DEFINED ENV{CONAN_HOME})
        set(CONAN_HOME $ENV{CONAN_HOME})
    elseif(DEFINED ENV{HOME})
        set(CONAN_HOME $ENV{HOME}/.conan2)
    else()
        # CI environments may not set HOME (e.g. some OHOS worker containers
        # where conan is invoked via absolute path with --package-folder).
        # Fall back to a deterministic empty string; subsequent file(GLOB) will
        # return 0 matches and the empty-GLOB guard above will skip the
        # include-dir fallback cleanly instead of producing a malformed
        # CONAN_HOME=//.conan2 path.
        set(CONAN_HOME "")
    endif()
endif()

# R-NEW (2026-08-05): log GLOB result sizes — lets us confirm the GLOB found
# exactly one match per dep (the expected steady state) and exposes any
# multi-match or zero-match regression in CI logs early.
#
# R-NEW (2026-08-07): the team ohpcd registry's glib/2.84.0 and libxml2/2.15.3
# recipes install to conan cache layout `p/<pkg_short_id>/p/...` (no `b/`
# segment), while pidgin itself (an autotools build) installs to
# `p/b/<pkg_short_id>/b/...` (conan places its build subdir under `b/`).
# Old versions of this file only globbed the `p/b/<pkg>/...` layout, so on
# the OHOS worker the GLOB returned empty for all three deps and `list(LENGTH)`
# crashed with "requires two arguments" because `${${_var}}` was the empty string.
# Now we glob both layouts in a single file(GLOB) call — file(GLOB) takes an
# arbitrary number of patterns and concatenates matches — so one line covers
# all observed conan cache variants.
file(GLOB _GLIB_H_FILES
    "${CONAN_HOME}/p/b/glib*/p/include/glib-2.0/glib.h"
    "${CONAN_HOME}/p/glib*/p/include/glib-2.0/glib.h")
file(GLOB _GLIB_CONFIG_H_FILES
    "${CONAN_HOME}/p/b/glib*/p/lib/glib-2.0/include/glibconfig.h"
    "${CONAN_HOME}/p/glib*/p/lib/glib-2.0/include/glibconfig.h")
# AI-review note (P2, 2026-07-27): glib's xmlversion.h is 1 hop below the
# include dir, so a single get_filename_component(... DIRECTORY) is enough.
# libxml2's xmlversion.h is 2 hops below (include/libxml2/libxml/xmlversion.h),
# so we need a SECOND get_filename_component call to climb out of `libxml/`.
# Globbing at libxml/parser.h would also work, but xmlversion.h is the canonical
# versioned sentinel used in conan-center recipes' CMakeLists.txt.
# R-NEW (2026-08-07): same dual-layout fallback as glib above.
file(GLOB _LIBXML2_H_FILES
    "${CONAN_HOME}/p/b/libxm*/p/include/libxml2/libxml/xmlversion.h"
    "${CONAN_HOME}/p/libxm*/p/include/libxml2/libxml/xmlversion.h")

message(STATUS "test_package: GLOB _GLIB_H_FILES='${_GLIB_H_FILES}'")
message(STATUS "test_package: GLOB _GLIB_CONFIG_H_FILES='${_GLIB_CONFIG_H_FILES}'")
message(STATUS "test_package: GLOB _LIBXML2_H_FILES='${_LIBXML2_H_FILES}'")

# R-NEW (2026-08-05 / revised 2026-08-07): capture GLOB result into a plain
# temporary variable BEFORE any list() or get_filename_component() calls.
#
# CMake semantics (CMake 3.20+ official docs):
#   - list(LENGTH|GET|JOIN)'s <list> parameter is a VARIABLE NAME (not a value).
#     CMake dereferences it internally. `list(LENGTH ${_var} _LEN)` is valid —
#     ${_var} expands to the variable name (e.g. "_GLIB_H_FILES"), and list()
#     dereferences that to get the actual list content.
#   - The actual trap: if the variable value contains a semicolon (e.g.
#     "/path1;/path2"), then "${${_var}}" in ANY CMake command argument context
#     causes the semicolon to be parsed as an argument separator, producing
#     "Unknown arguments specified" or garbled get_filename_component output.
#   - The fix: `set(_VAL "${${_var}}")` copies the value into a fresh
#     temporary variable _VAL. Semicolons inside _VAL are inert until _VAL
#     is used as a bare variable (not inside "${}"). So all downstream
#     operations (if(), string(FIND), get_filename_component()) use _VAL
#     directly, never re-expanded.
#
# R-NEW (2026-08-07): empty-GLOB guard — when file(GLOB) finds zero matches
# the variable is set to the empty string. Guard with a skip-when-empty
# early-out so a missing dep dir doesn't fail the whole test_package configure.
# We use `if(_VAL STREQUAL "")` (string comparison), NOT list(LENGTH):
# list(LENGTH) takes a *variable name* (not a value) as its first argument.
# If _VAL is empty ("") and we tried list(LENGTH "${_VAL}" _LEN), CMake would
# try to dereference variable "" (empty name) — likely an error. By contrast,
# if(_VAL STREQUAL "") directly compares the value to "" and works correctly.
foreach(_var IN ITEMS _GLIB_H_FILES _GLIB_CONFIG_H_FILES _LIBXML2_H_FILES)
    # Capture to plain temp variable: semicolons in the GLOB result are now
    # "frozen" inside _VAL and won't be re-parsed as argument separators.
    set(_VAL "${${_var}}")
    message(STATUS "test_package [foreach _var=${_var}]: _VAL='${_VAL}'")

    # R-NEW (2026-08-07): empty-GLOB guard.
    if(_VAL STREQUAL "")
        message(WARNING "test_package: GLOB '${_var}' matched no files under ${CONAN_HOME} — skipping include-dir fallback for this dep")
        continue()
    endif()

    # R-NEW (Pass 21): detect multiple GLOB matches (semicolon-separated list).
    # CMake stores a list with 2 elements as "path1;path2" in a variable.
    # When get_filename_component() receives a semicolon inside the input path
    # argument, CMake parses it as two separate arguments — breaking DIRECTORY
    # mode. We detect this with string(FIND) and FATAL_ERROR to make the
    # collision explicit rather than silently using a garbage path.
    string(FIND "${_VAL}" ";" _SEMI_POS)
    if(_SEMI_POS GREATER_EQUAL 0)
        # GLOB returned multiple matches — the include dir is ambiguous.
        # Tell the user to clean the conan cache rather than silently picking
        # one and hoping for the best.
        message(FATAL_ERROR
            "test_package: file(GLOB) matched multiple versions of ${_var}: ${_VAL}\n"
            "       This means multiple revisions of the same dependency are installed\n"
            "       in your conan cache (e.g. glib/2.84.0 and glib/2.72.4 coexist).\n"
            "       Please clean the conan cache to keep only one version:\n"
            "         conan remove '*' -c  # removes all cached packages\n"
            "       Or specify the exact package: conan remove glib/2.84.0 -c\n"
        )
    endif()
    get_filename_component(_DIR "${_VAL}" DIRECTORY)
    # libxml2's xmlversion.h is 2 hops below include/ (include/libxml2/libxml/),
    # so one extra parent hop is needed to reach the libxml2 include root.
    if(_var STREQUAL "_LIBXML2_H_FILES")
        get_filename_component(_DIR "${_DIR}" DIRECTORY)
    endif()
    set(_INCLUDE_DIR_NAME "${_var}_INCLUDE_DIR")
    set(${_INCLUDE_DIR_NAME} "${_DIR}")
endforeach()

message(STATUS "test_package: _GLIB_H_FILES_INCLUDE_DIR='${_GLIB_H_FILES_INCLUDE_DIR}'")
message(STATUS "test_package: _GLIB_CONFIG_H_FILES_INCLUDE_DIR='${_GLIB_CONFIG_H_FILES_INCLUDE_DIR}'")
message(STATUS "test_package: _LIBXML2_H_FILES_INCLUDE_DIR='${_LIBXML2_H_FILES_INCLUDE_DIR}'")

if(_GLIB_H_FILES_INCLUDE_DIR)
    message(STATUS "test_package: adding include dir for glib.h -> ${_GLIB_H_FILES_INCLUDE_DIR}")
    target_include_directories(test_pidgin PRIVATE ${_GLIB_H_FILES_INCLUDE_DIR})
endif()
if(_GLIB_CONFIG_H_FILES_INCLUDE_DIR)
    message(STATUS "test_package: adding include dir for glibconfig.h -> ${_GLIB_CONFIG_H_FILES_INCLUDE_DIR}")
    target_include_directories(test_pidgin PRIVATE ${_GLIB_CONFIG_H_FILES_INCLUDE_DIR})
endif()
if(_LIBXML2_H_FILES_INCLUDE_DIR)
    message(STATUS "test_package: adding include dir for libxml2 -> ${_LIBXML2_H_FILES_INCLUDE_DIR}")
    target_include_directories(test_pidgin PRIVATE ${_LIBXML2_H_FILES_INCLUDE_DIR})
endif()

enable_testing()
add_test(NAME test_pidgin COMMAND test_pidgin)
