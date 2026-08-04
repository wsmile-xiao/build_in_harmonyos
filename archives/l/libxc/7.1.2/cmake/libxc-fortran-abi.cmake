set(_libxc_fortran_requested FALSE)
foreach(_libxc_component IN LISTS Libxc_FIND_COMPONENTS)
  if(_libxc_component STREQUAL "Fortran" OR
     _libxc_component STREQUAL "Libxc::xcf03" OR
     _libxc_component STREQUAL "xcf03")
    set(_libxc_fortran_requested TRUE)
  endif()
endforeach()

set(_libxc_fortran_component_guard
    "Libxc::xcf03_requires_find_package_COMPONENTS_Fortran")

if(_libxc_fortran_requested)
  if(CMAKE_VERSION VERSION_LESS "3.24")
    message(FATAL_ERROR
      "Libxc Fortran consumers require CMake 3.24 or newer to identify LLVMFlang")
  endif()
  if(NOT CMAKE_Fortran_COMPILER_LOADED)
    message(FATAL_ERROR
      "Enable the Fortran language before requesting the Libxc Fortran component")
  endif()
  if(NOT CMAKE_Fortran_COMPILER_ID STREQUAL "LLVMFlang")
    message(FATAL_ERROR
      "Libxc::xcf03 modules require LLVMFlang 20.1.0; "
      "detected ${CMAKE_Fortran_COMPILER_ID} ${CMAKE_Fortran_COMPILER_VERSION}")
  endif()
  if(NOT CMAKE_Fortran_COMPILER_VERSION VERSION_EQUAL "20.1.0")
    message(FATAL_ERROR
      "Libxc::xcf03 modules require LLVMFlang 20.1.0; "
      "detected ${CMAKE_Fortran_COMPILER_ID} ${CMAKE_Fortran_COMPILER_VERSION}")
  endif()
  if(TARGET Libxc::xcf03)
    get_property(_libxc_xcf03_links TARGET Libxc::xcf03
                 PROPERTY INTERFACE_LINK_LIBRARIES)
    list(REMOVE_ITEM _libxc_xcf03_links "${_libxc_fortran_component_guard}")
    set_property(TARGET Libxc::xcf03 PROPERTY INTERFACE_LINK_LIBRARIES
                 "${_libxc_xcf03_links}")
  endif()
elseif(TARGET Libxc::xcf03)
  get_property(_libxc_xcf03_links TARGET Libxc::xcf03
               PROPERTY INTERFACE_LINK_LIBRARIES)
  list(FIND _libxc_xcf03_links "${_libxc_fortran_component_guard}"
       _libxc_guard_index)
  if(_libxc_guard_index EQUAL -1)
    set_property(TARGET Libxc::xcf03 APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                 "${_libxc_fortran_component_guard}")
  endif()
endif()

unset(_libxc_fortran_requested)
unset(_libxc_component)
unset(_libxc_fortran_component_guard)
unset(_libxc_xcf03_links)
unset(_libxc_guard_index)
