# run_consumer.cmake — ctest wrapper for test_consumer
# Sets LD_LIBRARY_PATH so the OHOS loader finds libblastrampoline.so.5
# (the OHOS clang does not embed rpaths when linking by file path).
if(NOT LBT_DIR)
    # Empty means CMakeLists could not resolve the packaged lib dir; running
    # anyway would only produce a confusing loader exit 127.
    message(FATAL_ERROR "LBT_DIR is empty: packaged library dir not resolved")
endif()
if(NOT DEFINED ENV{LD_LIBRARY_PATH})
    set(ENV{LD_LIBRARY_PATH} "${LBT_DIR}")
else()
    set(ENV{LD_LIBRARY_PATH} "${LBT_DIR}:$ENV{LD_LIBRARY_PATH}")
endif()
# script mode has no CMAKE_SHARED_LIBRARY_SUFFIX; the fake backends are
# plain "lib<name>.so" modules (PREFIX "" on all platforms we support)
set(_suffix ".so")
if(WIN32)
    set(_suffix ".dll")
elseif(APPLE)
    set(_suffix ".so")
endif()
execute_process(COMMAND "${TEST_BIN}"
    "${BACKEND_DIR}/fakeblas_lp64${_suffix}"
    "${BACKEND_DIR}/fakeblas_ilp64${_suffix}"
    "${BACKEND_DIR}/fakeblas_ilp64_nosuffix${_suffix}"
    RESULT_VARIABLE rc)
if(NOT rc EQUAL 0)
    message(FATAL_ERROR "test_consumer exited with ${rc}")
endif()
