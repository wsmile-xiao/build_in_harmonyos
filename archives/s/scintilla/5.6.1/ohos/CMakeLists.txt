# ScintillaOHOS CMake Build Configuration
# Builds libscintilla_core.a (static) and libscintilla_ohos.so (shared) for HarmonyOS

cmake_minimum_required(VERSION 3.16)
project(scintilla_ohos C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ============================================
# Find HarmonyOS SDK
# ============================================
if(NOT DEFINED OHOS_NDK_NATIVE)
    # Default SDK path for build sandbox
    set(OHOS_NDK_NATIVE "/data/service/hnp/ohos-sdk.org/ohos-sdk_6.1.0.27/ohos/native")
endif()

set(OHOS_SDK_INCLUDE "${OHOS_NDK_NATIVE}/sysroot/usr/include")
set(OHOS_ARCH "aarch64")
set(OHOS_SDK_LIB "${OHOS_NDK_NATIVE}/sysroot/usr/lib/${OHOS_ARCH}-linux-ohos")

# Scintilla source directory (configurable)
if(NOT DEFINED SCI_SRC_DIR)
    set(SCI_SRC_DIR "${CMAKE_SOURCE_DIR}/../scintilla/src")
endif()

# ============================================
# Scintilla core source files (33 files, zero modification)
# ============================================
set(SCI_CORE_SOURCES
    ${SCI_SRC_DIR}/AutoComplete.cxx
    ${SCI_SRC_DIR}/CallTip.cxx
    ${SCI_SRC_DIR}/CaseConvert.cxx
    ${SCI_SRC_DIR}/CaseFolder.cxx
    ${SCI_SRC_DIR}/CellBuffer.cxx
    ${SCI_SRC_DIR}/ChangeHistory.cxx
    ${SCI_SRC_DIR}/CharClassify.cxx
    ${SCI_SRC_DIR}/CharacterCategoryMap.cxx
    ${SCI_SRC_DIR}/CharacterType.cxx
    ${SCI_SRC_DIR}/ContractionState.cxx
    ${SCI_SRC_DIR}/DBCS.cxx
    ${SCI_SRC_DIR}/Decoration.cxx
    ${SCI_SRC_DIR}/Document.cxx
    ${SCI_SRC_DIR}/EditModel.cxx
    ${SCI_SRC_DIR}/EditView.cxx
    ${SCI_SRC_DIR}/Editor.cxx
    ${SCI_SRC_DIR}/Geometry.cxx
    ${SCI_SRC_DIR}/Indicator.cxx
    ${SCI_SRC_DIR}/KeyMap.cxx
    ${SCI_SRC_DIR}/LineMarker.cxx
    ${SCI_SRC_DIR}/MarginView.cxx
    ${SCI_SRC_DIR}/PerLine.cxx
    ${SCI_SRC_DIR}/PositionCache.cxx
    ${SCI_SRC_DIR}/RESearch.cxx
    ${SCI_SRC_DIR}/RunStyles.cxx
    ${SCI_SRC_DIR}/ScintillaBase.cxx
    ${SCI_SRC_DIR}/Selection.cxx
    ${SCI_SRC_DIR}/Style.cxx
    ${SCI_SRC_DIR}/UndoHistory.cxx
    ${SCI_SRC_DIR}/UniConversion.cxx
    ${SCI_SRC_DIR}/UniqueString.cxx
    ${SCI_SRC_DIR}/ViewStyle.cxx
    ${SCI_SRC_DIR}/XPM.cxx
)

# ============================================
# Platform adaptation source files
# ============================================
set(SCI_OHOS_SOURCES
    ${CMAKE_SOURCE_DIR}/PlatOHOS.cxx
    ${CMAKE_SOURCE_DIR}/ScintillaOHOS.cxx
)

# ============================================
# Static library: scintilla_core
# 33 core files + PlatOHOS.cxx (NO ScintillaOHOS.cxx)
# ============================================
add_library(scintilla_core STATIC
    ${SCI_CORE_SOURCES}
    ${CMAKE_SOURCE_DIR}/PlatOHOS.cxx
)

target_include_directories(scintilla_core PUBLIC
    # Scintilla headers
    ${SCI_SRC_DIR}
    ${SCI_SRC_DIR}/../include
    # OHOS headers
    ${OHOS_SDK_INCLUDE}
    # Our headers
    ${CMAKE_SOURCE_DIR}
)

target_compile_definitions(scintilla_core PRIVATE
    SCI_OHOS
    NDEBUG
    SCI_LEXER
)

# Force-include missing headers (Scintilla internal headers have fragile includes)
# Use SHELL: prefix to prevent CMake from deduplicating -include flags
target_compile_options(scintilla_core PRIVATE
    "SHELL:-include cstddef"
    "SHELL:-include cstdint"
    "SHELL:-include cassert"
    "SHELL:-include cstring"
)

# Optimization
target_compile_options(scintilla_core PRIVATE
    -O2
    -fPIC
)

# ============================================
# Shared library: libscintilla_ohos.so
# ScintillaOHOS integration + DevEco pre-built .so approach
# Links scintilla_core (whole-archive) + ScintillaOHOS.o
# ============================================
add_library(scintilla_ohos SHARED
    ${CMAKE_SOURCE_DIR}/ScintillaOHOS.cxx
)

target_include_directories(scintilla_ohos PUBLIC
    ${SCI_SRC_DIR}
    ${SCI_SRC_DIR}/../include
    ${OHOS_SDK_INCLUDE}
    ${CMAKE_SOURCE_DIR}
)

target_compile_definitions(scintilla_ohos PRIVATE
    SCI_OHOS
    NDEBUG
    SCI_LEXER
)

target_compile_options(scintilla_ohos PRIVATE
    "SHELL:-include cstddef"
    "SHELL:-include cstdint"
    "SHELL:-include cassert"
    "SHELL:-include cstring"
    -O2
    -fPIC
)

# Link everything together using --whole-archive to ensure no symbols are dropped
target_link_libraries(scintilla_ohos PUBLIC
    -Wl,--whole-archive scintilla_core -Wl,--no-whole-archive
    ${OHOS_SDK_LIB}/libnative_drawing.so
)

set_target_properties(scintilla_ohos PROPERTIES
    OUTPUT_NAME "scintilla_ohos"
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)

# ============================================
# Header installation
# ============================================
install(TARGETS scintilla_core scintilla_ohos
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
)
install(FILES ScintillaOHOS.h DESTINATION include/scintilla_ohos)
install(DIRECTORY ${SCI_SRC_DIR}/../include/ DESTINATION include/scintilla_ohos/scintilla
    FILES_MATCHING PATTERN "*.h"
)

# ============================================
# Print build summary
# ============================================
message(STATUS "")
message(STATUS "=== ScintillaOHOS Build Configuration ===")
message(STATUS "  Scintilla source: ${SCI_SRC_DIR}")
message(STATUS "  OHOS SDK: ${OHOS_NDK_NATIVE}")
message(STATUS "  Static library: libscintilla_core.a (33 core + PlatOHOS)")
message(STATUS "  Shared library: libscintilla_ohos.so (core + ScintillaOHOS)")
message(STATUS "  Architecture: ${OHOS_ARCH}")
message(STATUS "==========================================")


