# AddLLVM.cmake — Minimal stub for OHOS SDK LLVM overlay
# Provides the LLVM CMake functions needed by Enzyme's build system.
# The OHOS SDK LLVM's AddLLVM.cmake is incompatible with Enzyme's
# build context (targets reference .a files that don't exist).
# This stub provides only the functions that Enzyme actually uses.

# ─── tablegen ───────────────────────────────────────────────────────
# Defined in LLVM's TableGen.cmake. Provides the tablegen() function.
# OHOS SDK LLVM doesn't include llvm-tblgen binary, so we provide a
# stub that creates stub output files via the stub-tblgen.sh script.
function(tablegen project ofn)
    cmake_parse_arguments(ARG "" "" "DEPENDS;EXTRA_INCLUDES" ${ARGN})
    if(DEFINED ENZYME_TABLEGEN_EXE AND EXISTS "${ENZYME_TABLEGEN_EXE}")
        set(_TBLGEN_EXE "${ENZYME_TABLEGEN_EXE}")
    elseif(DEFINED LLVM_TABLEGEN_EXE AND EXISTS "${LLVM_TABLEGEN_EXE}")
        set(_TBLGEN_EXE "${LLVM_TABLEGEN_EXE}")
    else()
        set(_OUTPUT_FILE "${CMAKE_CURRENT_BINARY_DIR}/${ofn}")
        file(WRITE "${_OUTPUT_FILE}" "// Auto-generated stub for OHOS SDK (no TableGen available)\n")
        message(STATUS "tablegen stub: created ${_OUTPUT_FILE}")
        return()
    endif()
    set(_OUTPUT_FILE "${CMAKE_CURRENT_BINARY_DIR}/${ofn}")
    execute_process(COMMAND "${_TBLGEN_EXE}" -o "${_OUTPUT_FILE}" ${ARG_UNPARSED_ARGUMENTS}
                    WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"
                    RESULT_VARIABLE _TBLGEN_RESULT)
    if(NOT _TBLGEN_RESULT EQUAL 0)
        message(WARNING "tablegen stub failed (${_TBLGEN_RESULT}), creating empty file")
        file(WRITE "${_OUTPUT_FILE}" "// Auto-generated stub for OHOS SDK\n")
    endif()
    set(TABLEGEN_OUTPUT "${TABLEGEN_OUTPUT};${_OUTPUT_FILE}" PARENT_SCOPE)
endfunction()

# ─── add_public_tablegen_target ─────────────────────────────────────
# Used by Enzyme/CMakeLists.txt to create tablegen targets.
function(add_public_tablegen_target target)
    add_custom_target(${target} COMMAND echo "Stub tablegen: ${target}")
    set_target_properties(${target} PROPERTIES FOLDER "Tablegen targets")
    set(ARG_TABLEGEN "")
    cmake_parse_arguments(ARG "" "TABLEGEN" "" ${ARGN})
    if(ARG_TABLEGEN)
        add_dependencies(${target} ${ARG_TABLEGEN})
    endif()
endfunction()

# ─── add_tablegen ───────────────────────────────────────────────────
# Used by tools/CMakeLists.txt to create tablegen executables.
# No-op on OHOS (no TableGen available).
function(add_tablegen project)
endfunction()

# ─── add_llvm_library ───────────────────────────────────────────────
# Used by Enzyme/CMakeLists.txt to build Enzyme as a shared library.
function(add_llvm_library name)
    cmake_parse_arguments(ARG "SHARED;STATIC;MODULE;INSTALL_WITH_TOOLCHAIN;DISABLE_LLVM_LINK_LLVM_DYLIB;PARTIAL_SOURCES_INTENDED" "" "" ${ARGN})
    set(_SOURCES ${ARG_UNPARSED_ARGUMENTS})
    if("PARTIAL_SOURCES_INTENDED" IN_LIST _SOURCES)
        list(REMOVE_ITEM _SOURCES "PARTIAL_SOURCES_INTENDED")
    endif()
    if("--" IN_LIST _SOURCES)
        list(REMOVE_ITEM _SOURCES "--")
    endif()
    set(_REAL_SOURCES "")
    set(_SKIP_DEPENDS FALSE)
    foreach(_src IN LISTS _SOURCES)
        if(_src STREQUAL "DEPENDS")
            set(_SKIP_DEPENDS TRUE)
            continue()
        elseif(_SKIP_DEPENDS)
            continue()
        endif()
        list(APPEND _REAL_SOURCES "${_src}")
    endforeach()
    set(_LIBTYPE "")
    if(ARG_SHARED OR ARG_MODULE)
        set(_LIBTYPE "SHARED")
    elseif(ARG_STATIC)
        set(_LIBTYPE "STATIC")
    else()
        if(BUILD_SHARED_LIBS)
            set(_LIBTYPE "SHARED")
        else()
            set(_LIBTYPE "STATIC")
        endif()
    endif()
    if(_REAL_SOURCES)
        add_library(${name} ${_LIBTYPE} ${_REAL_SOURCES})
        message(STATUS "add_llvm_library: ${name} (${_LIBTYPE}, ${_REAL_SOURCES})")
    else()
        if(NOT TARGET ${name})
            set(_DUMMY_SRC "${CMAKE_CURRENT_BINARY_DIR}/${name}_stub.c")
            file(WRITE "${_DUMMY_SRC}" "// Stub for ${name}\n")
            add_library(${name} ${_LIBTYPE} "${_DUMMY_SRC}")
            message(STATUS "add_llvm_library stub: ${name} (${_LIBTYPE}, stub)")
        endif()
    endif()
    if(NOT ARG_DISABLE_LLVM_LINK_LLVM_DYLIB AND TARGET LLVM)
        target_link_libraries(${name} INTERFACE LLVM)
    endif()
endfunction()

# ─── configure_lit_site_cfg ─────────────────────────────────────────
# Used by test/CMakeLists.txt to configure lit test site.
# No-op on OHOS (lit tests cannot run).
function(configure_lit_site_cfg input output)
    get_filename_component(_OUTPUT_DIR "${output}" PATH)
    file(MAKE_DIRECTORY "${_OUTPUT_DIR}")
    file(WRITE "${output}" "# Stub lit site config for OHOS SDK\n")
    message(STATUS "configure_lit_site_cfg stub: ${output}")
endfunction()

# ─── get_llvm_lit_path ──────────────────────────────────────────────
function(get_llvm_lit_path lit_dir lit_file)
    set(${lit_dir} "${CMAKE_BINARY_DIR}" PARENT_SCOPE)
    set(${lit_file} "lit" PARENT_SCOPE)
endfunction()

# ─── add_lit_target ─────────────────────────────────────────────────
function(add_lit_target target)
endfunction()