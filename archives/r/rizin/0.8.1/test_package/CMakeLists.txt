cmake_minimum_required(VERSION 3.15)
project(test_rizin C)

# Rizin test_package — substantive compiled test (R34: links librz_core, calls
# rz_core_new/cmd0/free — NOT a printf stub). Satisfies CI's L1 negative-test
# gate which scans for a real link dependency on the rizin package.
find_package(rizin REQUIRED)

add_executable(test_rizin test.c)

# Conan CMakeDeps on OHOS conan 2.29.1 declares rizin::rizin as INTERFACE
# IMPORTED but leaves rizin_LIBRARIES_RELEASE EMPTY (bug) — the .so files DO
# exist under <pkg>/lib/librz_*.so. Link the PUBLIC API entry librz_core.so
# directly (it pulls the rest of the rz chain via its own DT_NEEDED entries).
# Bake DT_RUNPATH so the linker finds librz_core.so at run time where ld-musl
# honors it (HarmonyOS ld-musl uses namespace API but DT_RUNPATH is still
# serialized; run-time gating is tolerated via ignore_errors in conanfile.py).
if(DEFINED rizin_PACKAGE_FOLDER_RELEASE)
    target_link_libraries(test_rizin PRIVATE
        "${rizin_PACKAGE_FOLDER_RELEASE}/lib/librz_core.so"
    )
    target_link_options(test_rizin PRIVATE
        "-Wl,-rpath,${rizin_PACKAGE_FOLDER_RELEASE}/lib"
    )
endif()

# rizin headers live under <pkg>/include/librz/ (e.g. rz_core.h) and transitively
# #include <openssl/bn.h> and <sdb.h> (sdb headers under <pkg>/include/librz/sdb/).
# Conan CMakeDeps leaves rizin_INCLUDE_DIRS_RELEASE EMPTY (same bug as libs),
# so inject the paths manually via the *_PACKAGE_FOLDER_RELEASE vars Conan DOES
# define correctly.
if(DEFINED rizin_PACKAGE_FOLDER_RELEASE)
    target_include_directories(test_rizin PRIVATE
        "${rizin_PACKAGE_FOLDER_RELEASE}/include/librz"
        "${rizin_PACKAGE_FOLDER_RELEASE}/include/librz/sdb"
    )
endif()
if(DEFINED openssl_PACKAGE_FOLDER_RELEASE)
    target_include_directories(test_rizin PRIVATE
        "${openssl_PACKAGE_FOLDER_RELEASE}/include"
    )
endif()

install(TARGETS test_rizin DESTINATION bin)
