# Resolve XKB through the consumer's Conan metadata before Qt's pkg-config finder.
list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/conan")
