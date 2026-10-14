if(CMAKE_SYSTEM_NAME MATCHES "^(HarmonyOS|OHOS|OpenHarmony)$")
    # Native CMake's unknown-platform fallback omits ELF SONAME/RPATH flags.
    # Keep the real system identity; enable clang/ELF linker semantics only.
    set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")
    set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")
    set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")
endif()
