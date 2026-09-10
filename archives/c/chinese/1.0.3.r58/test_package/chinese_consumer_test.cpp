#include <filesystem>
#include <iostream>

int main(int argc, char **argv) {
    if (argc != 2) {
        std::cerr << "usage: chinese_consumer_test <package-folder>\n";
        return 2;
    }

    const std::filesystem::path package_folder(argv[1]);
    const auto executable = package_folder / "bin" / "chinese-calendar";
    const auto database = package_folder / "usr" / "share" / "chinese-calendar" / "db" / "KylinLunar.db";
    const auto desktop = package_folder / "usr" / "share" / "applications" / "chinese-calendar.desktop";

    if (!std::filesystem::exists(executable) || !std::filesystem::is_regular_file(executable)) {
        std::cerr << "missing installed executable: " << executable << '\n';
        return 1;
    }
    if ((std::filesystem::status(executable).permissions() & std::filesystem::perms::owner_exec) == std::filesystem::perms::none) {
        std::cerr << "installed executable is not executable: " << executable << '\n';
        return 1;
    }
    if (!std::filesystem::is_regular_file(database)) {
        std::cerr << "missing lunar database: " << database << '\n';
        return 1;
    }
    if (!std::filesystem::is_regular_file(desktop)) {
        std::cerr << "missing desktop entry: " << desktop << '\n';
        return 1;
    }

    std::cout << "chinese HarmonyOS consumer test passed\n";
    return 0;
}
