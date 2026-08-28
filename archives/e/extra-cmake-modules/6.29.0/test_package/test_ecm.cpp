int main() {
    static_assert(ECM_MODULE_HELPERS_LOADED == 1);
    constexpr char version[] = ECM_VERSION_STRING;
    constexpr char module_dir[] = ECM_MODULE_DIR_STRING;
    static_assert(sizeof(version) > 1);
    static_assert(sizeof(module_dir) > 1);
    // Runtime validation of the actual ECM values discovered by find_package(ECM).
    if (version[0] != '6') return 1;
    if (module_dir[0] == '\0') return 1;
    return 0;
}
