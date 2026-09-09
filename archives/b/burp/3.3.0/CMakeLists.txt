# burp 3.3.0 - OHOS CMake wrapper (generated from Makefile.am; bypass autotools.
# tarball ships no pre-generated configure/Makefile.in and host lacks automake/libtool).
# Mirrors upstream: main_SOURCES compiled fresh per target (no shared lib - the
# asfd struct differs under -DUTEST so a shared libburp would be an ODR hazard).
cmake_minimum_required(VERSION 3.10)
project(burp C)
set(CMAKE_C_STANDARD 11)
set(BURP_SRC ${CMAKE_CURRENT_SOURCE_DIR}/src)

# config.h = what ./configure would emit for OHOS aarch64, each macro verified
# against the OHOS sysroot (headers + readelf of libc.so dyn-syms):
#  crypt, lockf, lutimes, prctl, setreuid, llistxattr/listxattr/lgetxattr/
#  getxattr/lsetxattr/setxattr all present in musl libc; sys/xattr.h,
#  endian.h, prctl.h present; librsync has RS_BLAKE2_SIG_MAGIC (HAVE_BLAKE2).
#  NOT defined (sysroot lacks them): HAVE_CHFLAGS (no chflags), HAVE_ACL
#  (no sys/acl.h), HAVE_NCURSES (no ncurses.h), HAVE_SYSTEMD, HAVE_LIBCAP
#  (no libcap lib), HAVE_DARWIN/NETBSD/OPENBSD/SUN/FREEBSD_OS.
file(WRITE ${CMAKE_BINARY_DIR}/config.h
"#define HAVE_LINUX_OS 1\n"
"#define HAVE_IPV6 1\n"
"#define HAVE_ENDIAN_H 1\n"
"#define HAVE_DIRENT_H 1\n"
"#define HAVE_FSEEKO 1\n"
"#define HAVE_TYPEOF 1\n"
"#define HAVE_LOCKF 1\n"
"#define HAVE_LUTIMES 1\n"
"#define HAVE_SYS_XATTR_H 1\n"
"#define HAVE_XATTR 1\n"
"#define HAVE_CRYPT 1\n"
"#define HAVE_BLAKE2 1\n"
"#define HAVE_SYS_PRCTL_H 1\n"
"#define HAVE_PRCTL 1\n"
"#define HAVE_SETREUID 1\n"
"#define PACKAGE_NAME \"Burp\"\n"
"#define PACKAGE_VERSION \"3.3.0\"\n"
"#define PACKAGE_STRING \"Burp 3.3.0\"\n"
"#define PACKAGE_TARNAME \"burp\"\n"
"#define PACKAGE_BUGREPORT \"https://github.com/grke/burp/issues\"\n"
"#define PACKAGE_URL \"http://burp.grke.net/\"\n"
"#define VERSION \"3.3.0\"\n"
"#define SYSCONFDIR \"/usr/local/etc\"\n")

# deps from conan (explicit imported targets; find_package searches sysroot not conan)
add_library(SSL_crypto STATIC IMPORTED)
set_target_properties(SSL_crypto PROPERTIES IMPORTED_LOCATION ${OPENSSL_ROOT_DIR}/lib/libcrypto.a)
add_library(SSL_ssl STATIC IMPORTED)
set_target_properties(SSL_ssl PROPERTIES IMPORTED_LOCATION ${OPENSSL_ROOT_DIR}/lib/libssl.a
  INTERFACE_INCLUDE_DIRECTORIES ${OPENSSL_ROOT_DIR}/include)
add_library(LIBRSYNC STATIC IMPORTED)
set_target_properties(LIBRSYNC PROPERTIES IMPORTED_LOCATION ${LIBRSYNC_ROOT_DIR}/lib/librsync.a
  INTERFACE_INCLUDE_DIRECTORIES ${LIBRSYNC_ROOT_DIR}/include)
add_library(ZLIB_z STATIC IMPORTED)
set_target_properties(ZLIB_z PROPERTIES IMPORTED_LOCATION ${ZLIB_ROOT_DIR}/lib/libz.a
  INTERFACE_INCLUDE_DIRECTORIES ${ZLIB_ROOT_DIR}/include)
add_library(CHECK_check STATIC IMPORTED)
set_target_properties(CHECK_check PROPERTIES IMPORTED_LOCATION ${CHECK_ROOT_DIR}/lib/libcheck.a
  INTERFACE_INCLUDE_DIRECTORIES ${CHECK_ROOT_DIR}/include)
add_library(UTHASH_hdr INTERFACE IMPORTED)
set_target_properties(UTHASH_hdr PROPERTIES INTERFACE_INCLUDE_DIRECTORIES ${UTHASH_ROOT_DIR}/include)
# link plain "m" (resolved by the OHOS clang driver via --sysroot); find_library
# misses libm under the conan CMakeToolchain sysroot (sets NOTFOUND)
set(BURP_M m)

set(DEF_BASE HAVE_LINUX_OS=1 HAVE_IPV6=1)
set(INC_BASE ${CMAKE_BINARY_DIR} ${BURP_SRC} ${OPENSSL_ROOT_DIR}/include
  ${LIBRSYNC_ROOT_DIR}/include ${ZLIB_ROOT_DIR}/include)
set(LINK_BASE SSL_ssl SSL_crypto LIBRSYNC ZLIB_z ${BURP_M})

# ---- burp (main program, sbin_PROGRAMS=$(PACKAGE_TARNAME)) ----
add_executable(burp
    src/alloc.c
    src/asfd.c
    src/async.c
    src/attribs.c
    src/base64.c
    src/berrno.c
    src/bfile.c
    src/bu.c
    src/cmd.c
    src/cntr.c
    src/conf.c
    src/conffile.c
    src/cstat.c
    src/forkchild.c
    src/fsops.c
    src/fzp.c
    src/handy.c
    src/handy_extra.c
    src/hexmap.c
    src/incexc_recv.c
    src/incexc_send.c
    src/iobuf.c
    src/ipacl.c
    src/linkhash.c
    src/lock.c
    src/log.c
    src/md5.c
    src/msg.c
    src/pathcmp.c
    src/prepend.c
    src/prog.c
    src/regexp.c
    src/rs_buf.c
    src/run_script.c
    src/sbuf.c
    src/slist.c
    src/ssl.c
    src/strlist.c
    src/times.c
    src/transfer.c
    src/yajl_gen_w.c
    src/client/acl.c
    src/client/auth.c
    src/client/autoupgrade.c
    src/client/backup.c
    src/client/backup_phase1.c
    src/client/backup_phase2.c
    src/client/ca.c
    src/client/cvss.c
    src/client/delete.c
    src/client/extra_comms.c
    src/client/extrameta.c
    src/client/find.c
    src/client/find_logic.c
    src/client/glob_windows.c
    src/client/list.c
    src/client/main.c
    src/client/monitor.c
    src/client/restore.c
    src/client/xattr.c
    src/client/monitor/json_input.c
    src/client/monitor/lline.c
    src/client/monitor/sel.c
    src/client/monitor/status_client_ncurses.c
    src/client/restore_switch.c
    src/server/auth.c
    src/server/autoupgrade.c
    src/server/backup.c
    src/server/backup_phase1.c
    src/server/backup_phase2.c
    src/server/backup_phase3.c
    src/server/backup_phase4.c
    src/server/bedup.c
    src/server/blocklen.c
    src/server/bu_get.c
    src/server/ca.c
    src/server/child.c
    src/server/compress.c
    src/server/delete.c
    src/server/deleteme.c
    src/server/diff.c
    src/server/dpth.c
    src/server/extra_comms.c
    src/server/fdirs.c
    src/server/link.c
    src/server/list.c
    src/server/main.c
    src/server/manio.c
    src/server/manios.c
    src/server/quota.c
    src/server/restore.c
    src/server/restore_sbuf.c
    src/server/resume.c
    src/server/rubble.c
    src/server/run_action.c
    src/server/sdirs.c
    src/server/timer.c
    src/server/timestamp.c
    src/server/zlibio.c
    src/server/monitor/browse.c
    src/server/monitor/cache.c
    src/server/monitor/cstat.c
    src/server/monitor/json_output.c
    src/server/monitor/status_server.c
    src/yajl/yajl.c
    src/yajl/yajl_alloc.c
    src/yajl/yajl_buf.c
    src/yajl/yajl_encode.c
    src/yajl/yajl_gen.c
    src/yajl/yajl_lex.c
    src/yajl/yajl_parser.c
    src/yajl/yajl_tree.c
)
target_include_directories(burp PRIVATE ${INC_BASE})
target_compile_options(burp PRIVATE -fno-strict-aliasing)
target_compile_definitions(burp PRIVATE ${DEF_BASE})
target_link_libraries(burp PRIVATE ${LINK_BASE} UTHASH_hdr)

# ---- runner (upstream utest harness, check lib, -DUTEST) ----
add_executable(runner
    utest/builders/build_attribs.c
    utest/builders/build_asfd_mock.c
    utest/builders/build_clientconfdir.c
    utest/builders/build_file.c
    utest/builders/build_slist.c
    utest/builders/build_paths.c
    utest/builders/server/build_manifest.c
    utest/builders/server/build_storage_dirs.c
    utest/main.c
    utest/prng.c
    utest/client/monitor/test_json_input.c
    utest/client/monitor/test_lline.c
    utest/client/monitor/test_status_client_ncurses.c
    utest/client/test_acl.c
    utest/client/test_auth.c
    utest/client/test_backup_phase2.c
    utest/client/test_delete.c
    utest/client/test_extra_comms.c
    utest/client/test_extrameta.c
    utest/client/test_find.c
    utest/client/test_monitor.c
    utest/client/test_restore.c
    utest/client/test_xattr.c
    utest/server/monitor/test_browse.c
    utest/server/monitor/test_cache.c
    utest/server/monitor/test_cstat.c
    utest/server/monitor/test_json_output.c
    utest/server/monitor/test_status_server.c
    utest/server/test_auth.c
    utest/server/test_autoupgrade.c
    utest/server/test_bedup.c
    utest/server/test_blocklen.c
    utest/server/test_ca.c
    utest/server/test_backup_phase2.c
    utest/server/test_backup_phase3.c
    utest/server/test_backup_phase4.c
    utest/server/test_bu_get.c
    utest/server/test_delete.c
    utest/server/test_dpth.c
    utest/server/test_extra_comms.c
    utest/server/test_fdirs.c
    utest/server/test_list.c
    utest/server/test_manio.c
    utest/server/test_resume.c
    utest/server/test_restore.c
    utest/server/test_restore_sbuf.c
    utest/server/test_run_action.c
    utest/server/test_sdirs.c
    utest/server/test_timer.c
    utest/test_alloc.c
    utest/test_asfd.c
    utest/test_attribs.c
    utest/test_base64.c
    utest/test_cmd.c
    utest/test_cntr.c
    utest/test_conf.c
    utest/test_conffile.c
    utest/test_fzp.c
    utest/test_handy_extra.c
    utest/test_hexmap.c
    utest/test_lock.c
    utest/test_md5.c
    utest/test_pathcmp.c
    utest/test_rs_buf.c
    utest/test_slist.c
    utest/test_times.c
    src/alloc.c
    src/asfd.c
    src/async.c
    src/attribs.c
    src/base64.c
    src/berrno.c
    src/bfile.c
    src/bu.c
    src/cmd.c
    src/cntr.c
    src/conf.c
    src/conffile.c
    src/cstat.c
    src/forkchild.c
    src/fsops.c
    src/fzp.c
    src/handy.c
    src/handy_extra.c
    src/hexmap.c
    src/incexc_recv.c
    src/incexc_send.c
    src/iobuf.c
    src/ipacl.c
    src/linkhash.c
    src/lock.c
    src/log.c
    src/md5.c
    src/msg.c
    src/pathcmp.c
    src/prepend.c
    src/prog.c
    src/regexp.c
    src/rs_buf.c
    src/run_script.c
    src/sbuf.c
    src/slist.c
    src/ssl.c
    src/strlist.c
    src/times.c
    src/transfer.c
    src/yajl_gen_w.c
    src/client/acl.c
    src/client/auth.c
    src/client/autoupgrade.c
    src/client/backup.c
    src/client/backup_phase1.c
    src/client/backup_phase2.c
    src/client/ca.c
    src/client/cvss.c
    src/client/delete.c
    src/client/extra_comms.c
    src/client/extrameta.c
    src/client/find.c
    src/client/find_logic.c
    src/client/glob_windows.c
    src/client/list.c
    src/client/main.c
    src/client/monitor.c
    src/client/restore.c
    src/client/xattr.c
    src/client/monitor/json_input.c
    src/client/monitor/lline.c
    src/client/monitor/sel.c
    src/client/monitor/status_client_ncurses.c
    src/client/restore_switch.c
    src/server/auth.c
    src/server/autoupgrade.c
    src/server/backup.c
    src/server/backup_phase1.c
    src/server/backup_phase2.c
    src/server/backup_phase3.c
    src/server/backup_phase4.c
    src/server/bedup.c
    src/server/blocklen.c
    src/server/bu_get.c
    src/server/ca.c
    src/server/child.c
    src/server/compress.c
    src/server/delete.c
    src/server/deleteme.c
    src/server/diff.c
    src/server/dpth.c
    src/server/extra_comms.c
    src/server/fdirs.c
    src/server/link.c
    src/server/list.c
    src/server/main.c
    src/server/manio.c
    src/server/manios.c
    src/server/quota.c
    src/server/restore.c
    src/server/restore_sbuf.c
    src/server/resume.c
    src/server/rubble.c
    src/server/run_action.c
    src/server/sdirs.c
    src/server/timer.c
    src/server/timestamp.c
    src/server/zlibio.c
    src/server/monitor/browse.c
    src/server/monitor/cache.c
    src/server/monitor/cstat.c
    src/server/monitor/json_output.c
    src/server/monitor/status_server.c
    src/yajl/yajl.c
    src/yajl/yajl_alloc.c
    src/yajl/yajl_buf.c
    src/yajl/yajl_encode.c
    src/yajl/yajl_gen.c
    src/yajl/yajl_lex.c
    src/yajl/yajl_parser.c
    src/yajl/yajl_tree.c
)
target_include_directories(runner PRIVATE ${INC_BASE} ${CMAKE_CURRENT_SOURCE_DIR}/utest)
target_compile_options(runner PRIVATE -fno-strict-aliasing)
target_compile_definitions(runner PRIVATE ${DEF_BASE} UTEST=1
  TOP_SRCDIR="${CMAKE_CURRENT_SOURCE_DIR}")
target_link_libraries(runner PRIVATE ${LINK_BASE} CHECK_check UTHASH_hdr)

# conan package(): ship the client binary (runner is a test harness, not shipped)
install(TARGETS burp RUNTIME DESTINATION bin)
