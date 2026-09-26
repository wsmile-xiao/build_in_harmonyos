cmake_minimum_required(VERSION 3.16)
project(oas C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

add_library(oas SHARED src/oas.c src/connect.c)

# src/connect.c calls dlsym(RTLD_NEXT, "connect"). On the OHOS musl libc the
# RTLD_NEXT macro is only exposed by <dlfcn.h> when _GNU_SOURCE is defined.
# Upstream already guarantees that: src/connect.c:1 is literally
# "#define _GNU_SOURCE", measured on the pinned upstream tarball (the earlier
# guess "the recipe has to inject it" was disproved by that same reading and is
# retracted in notes.md section 2 and in section 4, row 2). The definition below
# is therefore redundant-but-harmless defensive scope: PRIVATE, no ABI change,
# no effect on the glibc side. It is kept as-is because it belongs to the build
# shape that passed the gates; the "-Wmacro-redefined" notice it produces for
# _GNU_SOURCE is disclosed in notes.md section 6 instead of being silenced here.
target_compile_definitions(oas PRIVATE _GNU_SOURCE)
target_include_directories(oas PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/src)

find_library(OAS_DL_LIBRARY dl)
if(OAS_DL_LIBRARY)
  target_link_libraries(oas PRIVATE ${OAS_DL_LIBRARY})
endif()

# Shared-library versioning replicates libtool's default instead of inventing an
# interface that upstream never declared: src/Makefile.am:1 has only
# "lib_LTLIBRARIES = liboas.la" and the tree carries no
# "liboas_la_LDFLAGS = -version-info", so libtool falls back to
# current:revision:age = 0:0:0 and installs liboas.so.0.0.0 with
# DT_SONAME = liboas.so.0 plus the liboas.so -> liboas.so.0 development symlink.
# The VERSION/SOVERSION pair below yields exactly that artefact set, which is
# also what the framework's L5a SONAME gate asks for (a relative DT_SONAME; an
# absolute one is rejected by the same rule).
#
# The extra line below is an OHOS host fixup, not an interface decision: this
# CMake has no Platform/HarmonyOS module (the configure log of this very build
# prints "System is unknown to cmake, create: Platform/HarmonyOS"), so
# CMAKE_SHARED_LIBRARY_SONAME_C_FLAG comes out empty while
# CMAKE_C_CREATE_SHARED_LIBRARY still carries the <SONAME_FLAG><TARGET_SONAME>
# placeholders. Measured on this host: with the flag empty CMake silently drops
# the whole VERSION/SOVERSION machinery and links a bare liboas.so without any
# DT_SONAME; giving it the value a Linux-like platform module would have set
# restores the normal behaviour (see notes.md section 12.1a for the probe).
set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")
set_target_properties(oas PROPERTIES OUTPUT_NAME oas VERSION 0.0.0 SOVERSION 0)

install(TARGETS oas LIBRARY DESTINATION lib)
install(FILES src/oas.h DESTINATION include)
