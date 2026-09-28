cmake_minimum_required(VERSION 3.18)
project(yodl VERSION 4.05.01 LANGUAGES C CXX)

include(GNUInstallDirs)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(YODL_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
set(YODL_WIP_DIR "${YODL_SOURCE_DIR}/tmp/wip")
file(MAKE_DIRECTORY "${YODL_WIP_DIR}")

file(STRINGS "${YODL_SOURCE_DIR}/VERSION" _version_line
     REGEX "^#define VERSION")
file(STRINGS "${YODL_SOURCE_DIR}/VERSION" _years_line
     REGEX "^#define YEARS")
string(REGEX MATCH "\"([^\"]+)\"" _version_match "${_version_line}")
set(YODL_VERSION "${CMAKE_MATCH_1}")
string(REGEX MATCH "\"([^\"]+)\"" _years_match "${_years_line}")
set(YODL_YEARS "${CMAKE_MATCH_1}")
if(NOT YODL_VERSION STREQUAL PROJECT_VERSION)
    message(FATAL_ERROR
        "Conan version ${PROJECT_VERSION} does not match upstream ${YODL_VERSION}")
endif()

set(YODL_BIN_DIR "${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_BINDIR}")
set(YODL_DATA_DIR "${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_DATADIR}/yodl")
file(WRITE "${YODL_WIP_DIR}/config.h"
    "#define STD_INCLUDE \"${YODL_DATA_DIR}\"\n"
    "#define VERSION \"${YODL_VERSION}\"\n"
    "#define YEARS \"${YODL_YEARS}\"\n"
    "#define YODL_BIN \"${YODL_BIN_DIR}\"\n")

# Upstream's icmake script derives these two generated files from gram*.c.
# Generate the same declarations/data directly so icmake is not a build
# dependency of this package.
file(GLOB _builtin_sources CONFIGURE_DEPENDS
     "${YODL_SOURCE_DIR}/yodl/gram*.c")
if(NOT _builtin_sources)
    message(FATAL_ERROR "No upstream builtin implementation files found")
endif()
set(_gram_header "#ifndef GRAM_H_\n#define GRAM_H_\n")
set(_builtin_table "/* generated from upstream yodl/gram*.c */\n#include \"gram.h\"\nBuiltin builtin_array[] =\n{\n")
foreach(_source IN LISTS _builtin_sources)
    get_filename_component(_name "${_source}" NAME_WE)
    string(REGEX REPLACE "^gram" "" _symbol "${_name}")
    string(TOUPPER "${_symbol}" _symbol)
    string(APPEND _gram_header "void gram_${_symbol}(void);\n")
    string(APPEND _builtin_table "{\"${_symbol}\", gram_${_symbol}},\n")
endforeach()
string(APPEND _gram_header "#endif\n")
string(APPEND _builtin_table "{0, 0}\n};\n")
file(WRITE "${YODL_WIP_DIR}/gram.h" "${_gram_header}")
file(WRITE "${YODL_WIP_DIR}/builtins.def" "${_builtin_table}")

set(_include_dirs "${YODL_SOURCE_DIR}" "${YODL_SOURCE_DIR}/yodl")
set(_components
    args builtin chartab counter file hashitem hashmap lexer lines macro media
    message new ostream parser postqueue process queue root stack string
    strvector subst symbol)
set(_component_sources)
foreach(_component IN LISTS _components)
    file(GLOB _sources CONFIGURE_DEPENDS
         "${YODL_SOURCE_DIR}/${_component}/*.c")
    if(NOT _sources)
        message(FATAL_ERROR "Missing upstream component sources: ${_component}")
    endif()
    list(APPEND _component_sources ${_sources})
endforeach()

add_library(yodl_runtime STATIC ${_component_sources})
target_include_directories(yodl_runtime PRIVATE ${_include_dirs})
target_compile_options(yodl_runtime PRIVATE -Wall -fdiagnostics-color=never)

file(GLOB _yodl_sources CONFIGURE_DEPENDS "${YODL_SOURCE_DIR}/yodl/*.c")
add_executable(yodl ${_yodl_sources})
target_include_directories(yodl PRIVATE ${_include_dirs})
target_compile_options(yodl PRIVATE -Wall -fdiagnostics-color=never)
target_link_libraries(yodl PRIVATE yodl_runtime)

file(GLOB _post_sources CONFIGURE_DEPENDS
     "${YODL_SOURCE_DIR}/yodlpost/*.c")
add_executable(yodlpost ${_post_sources})
target_include_directories(yodlpost PRIVATE
    ${_include_dirs} "${YODL_SOURCE_DIR}/yodlpost")
target_compile_options(yodlpost PRIVATE -Wall -fdiagnostics-color=never)
target_link_libraries(yodlpost PRIVATE yodl_runtime)

# icmbuild compiles the top-level files plus each declared class directory.
# Keep the same scope and exclude line/driver/main.cc, which is a standalone
# helper and would otherwise introduce a second main().
file(GLOB _verbinsert_sources CONFIGURE_DEPENDS
     "${YODL_SOURCE_DIR}/verbinsert/*.cc"
     "${YODL_SOURCE_DIR}/verbinsert/line/*.cc"
     "${YODL_SOURCE_DIR}/verbinsert/process/*.cc"
     "${YODL_SOURCE_DIR}/verbinsert/out/*.cc")
file(GLOB _verbinsert_driver CONFIGURE_DEPENDS
     "${YODL_SOURCE_DIR}/verbinsert/line/driver/*.cc")
list(REMOVE_ITEM _verbinsert_sources ${_verbinsert_driver})
add_executable(yodlverbinsert ${_verbinsert_sources})
target_compile_options(yodlverbinsert PRIVATE
    -Wall -fdiagnostics-color=never)
target_include_directories(yodlverbinsert PRIVATE
    "${YODL_SOURCE_DIR}/verbinsert"
    "${YODL_SOURCE_DIR}/verbinsert/line"
    "${YODL_SOURCE_DIR}/verbinsert/line/linetype"
    "${YODL_SOURCE_DIR}/verbinsert/process"
    "${YODL_SOURCE_DIR}/verbinsert/out")

# Keep upstream's macro and converter-script generators; only replace the
# icmake orchestration. These assets are generated into the Conan package
# prefix, never into a shared /usr or /usr/local location.
find_program(YODL_BASH_EXECUTABLE NAMES bash REQUIRED)
find_program(YODL_PERL_EXECUTABLE NAMES perl REQUIRED)
set(_runtime_dir "${CMAKE_CURRENT_BINARY_DIR}/runtime")
set(_runtime_bin "${_runtime_dir}/bin")
set(_runtime_share "${_runtime_dir}/${CMAKE_INSTALL_DATADIR}/yodl")
file(MAKE_DIRECTORY "${_runtime_bin}" "${_runtime_share}")

foreach(_format html latex man txt xml)
    execute_process(
        COMMAND "${YODL_BASH_EXECUTABLE}" -e
                "${YODL_SOURCE_DIR}/scripts/configreplacements"
                "${YODL_SOURCE_DIR}/macros/in/${_format}.in"
                "${_runtime_share}/${_format}.yo" "${YODL_DATA_DIR}"
        WORKING_DIRECTORY "${YODL_SOURCE_DIR}"
        RESULT_VARIABLE _result)
    if(NOT _result EQUAL 0)
        message(FATAL_ERROR "Failed to generate ${_format}.yo")
    endif()
endforeach()

execute_process(
    COMMAND "${YODL_BASH_EXECUTABLE}" -e
            "${YODL_SOURCE_DIR}/scripts/configreplacements"
            "${YODL_SOURCE_DIR}/macros/in/yodlversion.in"
            "${_runtime_share}/yodlversion.yo" "${YODL_DATA_DIR}"
    WORKING_DIRECTORY "${YODL_SOURCE_DIR}"
    RESULT_VARIABLE _result)
if(NOT _result EQUAL 0)
    message(FATAL_ERROR "Failed to generate yodlversion.yo")
endif()

foreach(_format html latex man txt xml)
    execute_process(
        COMMAND "${YODL_BASH_EXECUTABLE}" -e
                "${YODL_SOURCE_DIR}/scripts/stdmacros"
                "${CMAKE_CURRENT_BINARY_DIR}/scratch"
                "${_runtime_share}" "${_format}" "${YODL_DATA_DIR}"
        WORKING_DIRECTORY "${YODL_SOURCE_DIR}"
        RESULT_VARIABLE _result)
    if(NOT _result EQUAL 0)
        message(FATAL_ERROR "Failed to generate standard ${_format} macros")
    endif()
endforeach()
file(COPY "${YODL_SOURCE_DIR}/macros/yodl/" DESTINATION "${_runtime_share}")

foreach(_format html latex man ms sgml txt xml)
    execute_process(
        COMMAND "${YODL_BASH_EXECUTABLE}" -e
                "${YODL_SOURCE_DIR}/scripts/configreplacements"
                "${YODL_SOURCE_DIR}/scripts/yodl2whatever.in"
                "${_runtime_bin}/yodl2${_format}" "${YODL_DATA_DIR}"
        WORKING_DIRECTORY "${YODL_SOURCE_DIR}"
        RESULT_VARIABLE _result)
    if(NOT _result EQUAL 0)
        message(FATAL_ERROR "Failed to generate yodl2${_format}")
    endif()
endforeach()
configure_file("${YODL_SOURCE_DIR}/scripts/yodlstriproff"
               "${_runtime_bin}/yodlstriproff" COPYONLY)

install(TARGETS yodl yodlpost yodlverbinsert
        RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}")
install(PROGRAMS
    "${_runtime_bin}/yodl2html"
    "${_runtime_bin}/yodl2latex"
    "${_runtime_bin}/yodl2man"
    "${_runtime_bin}/yodl2ms"
    "${_runtime_bin}/yodl2sgml"
    "${_runtime_bin}/yodl2txt"
    "${_runtime_bin}/yodl2xml"
    "${_runtime_bin}/yodlstriproff"
    DESTINATION "${CMAKE_INSTALL_BINDIR}")
install(DIRECTORY "${_runtime_share}/"
        DESTINATION "${CMAKE_INSTALL_DATADIR}/yodl")
