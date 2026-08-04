cmake_minimum_required(VERSION 3.22)
project(fluidsynth_consumer_tests LANGUAGES C CXX)

foreach(required_path
    FLUIDSYNTH_PACKAGE_ROOT
    FLUIDSYNTH_INSTALLED_CMAKE_DIR
    FLUIDSYNTH_INSTALLED_PKGCONFIG_DIR)
  if(NOT DEFINED ${required_path} OR "${${required_path}}" STREQUAL "")
    message(FATAL_ERROR "${required_path} is required")
  endif()
endforeach()

find_package(
  FluidSynth CONFIG REQUIRED
  PATHS "${FLUIDSYNTH_INSTALLED_CMAKE_DIR}"
  NO_DEFAULT_PATH
)

get_filename_component(_package_root "${FLUIDSYNTH_PACKAGE_ROOT}" REALPATH)
get_filename_component(
  _expected_config
  "${FLUIDSYNTH_INSTALLED_CMAKE_DIR}/FluidSynthConfig.cmake"
  REALPATH
)
get_filename_component(_actual_config "${FluidSynth_CONFIG}" REALPATH)
if(NOT _actual_config STREQUAL _expected_config)
  message(FATAL_ERROR "FluidSynthConfig.cmake is not from the tested package")
endif()
if(NOT TARGET FluidSynth::libfluidsynth)
  message(FATAL_ERROR "Installed FluidSynth target is missing")
endif()
if(NOT FLUIDSYNTH_OSAL STREQUAL "cpp11")
  message(FATAL_ERROR "Installed FluidSynth OSAL is not cpp11")
endif()
if(FLUIDSYNTH_SUPPORT_GLIB)
  message(FATAL_ERROR "Portable FluidSynth package unexpectedly requires GLib")
endif()
if(NOT FLUIDSYNTH_SUPPORT_THREADS)
  message(FATAL_ERROR "Mixer thread support is unexpectedly disabled")
endif()
if(FLUIDSYNTH_EXPECT_SHARED AND NOT FLUIDSYNTH_IS_SHARED)
  message(FATAL_ERROR "Expected a shared FluidSynth package")
elseif(NOT FLUIDSYNTH_EXPECT_SHARED AND FLUIDSYNTH_IS_SHARED)
  message(FATAL_ERROR "Expected a static FluidSynth package")
endif()

set(_imported_locations)
get_target_property(
  _imported_location FluidSynth::libfluidsynth IMPORTED_LOCATION
)
if(_imported_location)
  list(APPEND _imported_locations "${_imported_location}")
endif()
string(TOUPPER "${CMAKE_BUILD_TYPE}" _config_upper)
foreach(_config "${_config_upper}" NOCONFIG RELEASE DEBUG)
  if(_config)
    get_target_property(
      _config_location
      FluidSynth::libfluidsynth
      "IMPORTED_LOCATION_${_config}"
    )
    if(_config_location)
      list(APPEND _imported_locations "${_config_location}")
    endif()
  endif()
endforeach()
list(REMOVE_DUPLICATES _imported_locations)
if(NOT _imported_locations)
  message(FATAL_ERROR "FluidSynth target has no imported location")
endif()
foreach(_location IN LISTS _imported_locations)
  get_filename_component(_location_real "${_location}" REALPATH)
  string(FIND "${_location_real}" "${_package_root}/" _package_prefix)
  if(NOT _package_prefix EQUAL 0)
    message(FATAL_ERROR "FluidSynth imported location escapes the package")
  endif()
endforeach()

if(WIN32)
  set(_pkg_config_path_separator ";")
else()
  set(_pkg_config_path_separator ":")
endif()
set(
  ENV{PKG_CONFIG_PATH}
  "${FLUIDSYNTH_INSTALLED_PKGCONFIG_DIR}${_pkg_config_path_separator}$ENV{PKG_CONFIG_PATH}"
)
find_package(PkgConfig REQUIRED)
if(NOT FLUIDSYNTH_EXPECT_SHARED)
  set(PKG_CONFIG_ARGN "--static")
endif()
pkg_check_modules(FLUIDSYNTH_PC REQUIRED IMPORTED_TARGET fluidsynth)
execute_process(
  COMMAND "${PKG_CONFIG_EXECUTABLE}" --print-requires-private fluidsynth
  RESULT_VARIABLE _requires_result
  OUTPUT_VARIABLE _requires_private
  OUTPUT_STRIP_TRAILING_WHITESPACE
)
if(NOT _requires_result EQUAL 0)
  message(FATAL_ERROR "pkg-config cannot inspect fluidsynth requirements")
endif()
if(NOT _requires_private STREQUAL "")
  message(FATAL_ERROR "fluidsynth.pc contains an undeclared package dependency")
endif()

foreach(_variable pcfiledir prefix libdir includedir)
  pkg_get_variable(_pc_${_variable} fluidsynth ${_variable})
  get_filename_component(_pc_${_variable}_real "${_pc_${_variable}}" REALPATH)
endforeach()
get_filename_component(
  _expected_pcfiledir "${FLUIDSYNTH_INSTALLED_PKGCONFIG_DIR}" REALPATH
)
if(NOT _pc_pcfiledir_real STREQUAL _expected_pcfiledir)
  message(FATAL_ERROR "pkg-config did not load the tested fluidsynth.pc")
endif()
if(NOT _pc_prefix_real STREQUAL _package_root)
  message(FATAL_ERROR "fluidsynth.pc has an unexpected prefix")
endif()
foreach(_variable libdir includedir)
  string(FIND "${_pc_${_variable}_real}" "${_package_root}/" _package_prefix)
  if(NOT _package_prefix EQUAL 0)
    message(FATAL_ERROR "fluidsynth.pc path escapes the package")
  endif()
endforeach()

add_executable(core_synth core_synth.cpp)
target_compile_features(core_synth PRIVATE cxx_std_11)
target_link_libraries(core_synth PRIVATE FluidSynth::libfluidsynth)

add_executable(pkgconfig_soundfont pkgconfig_soundfont.c)
target_compile_definitions(
  pkgconfig_soundfont
  PRIVATE FLUIDSYNTH_MISSING_SF2="${CMAKE_CURRENT_BINARY_DIR}/missing.sf2"
)
target_link_libraries(pkgconfig_soundfont PRIVATE PkgConfig::FLUIDSYNTH_PC)
