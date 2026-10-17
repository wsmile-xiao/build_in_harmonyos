cmake_minimum_required(VERSION 3.15)
project(pipexec_test_package C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# pipexec is package_type=application: it ships bin/pipexec (and bin/ptee,
# bin/peet) and exports no library or CMake config target, so there is
# deliberately no find_package()/target_link_libraries() here.
#
# pipehelper is the consumer-test child process.  pipexec execs children by
# absolute path (execv), so the test cannot lean on /bin/echo etc. — HarmonyOS
# has no traditional /bin (E165).  One helper binary covers every role the
# smoke test needs (produce / pass / consume / echo / exit / abort-once).
#
# No OHOS platform macro is used (R8): the same source builds on Linux and OHOS.
add_executable(pipehelper pipehelper.c)
target_compile_options(pipehelper PRIVATE -Wall -Wextra)
