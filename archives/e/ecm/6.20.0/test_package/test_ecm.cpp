int main() {
    static_assert(ECM_MODULE_HELPERS_LOADED == 1);
    constexpr char version[] = ECM_VERSION_STRING;
    constexpr char module_dir[] = ECM_MODULE_DIR_STRING;
    static_assert(sizeof(version) > 1);
    static_assert(sizeof(module_dir) > 1);
    return version[0] == '6' && module_dir[0] != '\0' ? 0 : 1;
}
