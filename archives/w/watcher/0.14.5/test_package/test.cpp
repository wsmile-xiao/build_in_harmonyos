#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include "wtr/watcher.hpp"

int main()
{
    namespace fs = std::filesystem;
    using namespace std::chrono_literals;

    auto root = fs::temp_directory_path() / "watcher-conan-smoke";
    std::error_code remove_ec;
    fs::remove_all(root, remove_ec);
    if (remove_ec) {
        std::cerr << "failed to remove old test directory: " << root << "\n";
        return 1;
    }

    std::error_code create_ec;
    fs::create_directories(root, create_ec);
    if (create_ec) {
        std::cerr << "failed to create test directory: " << root << "\n";
        return 1;
    }

    std::mutex mutex;
    std::vector<std::string> events;

    auto callback = [&](wtr::event event) {
        std::lock_guard<std::mutex> lock(mutex);
        events.push_back(wtr::to<std::string>(event.path_name));
    };

    auto watcher = wtr::watch(root, callback);
    std::this_thread::sleep_for(100ms);

    {
        std::ofstream file(root / "sample.txt");
        file << "watcher smoke test\n";
    }
    std::this_thread::sleep_for(300ms);

    auto close_ok = watcher.close();
    bool saw_lifecycle = false;
    {
        std::lock_guard<std::mutex> lock(mutex);
        for (const auto& event : events) {
            if (event.find("s/self/live@") != std::string::npos) {
                saw_lifecycle = true;
                break;
            }
        }
    }

    std::error_code cleanup_ec;
    fs::remove_all(root, cleanup_ec);

    if (!close_ok || !saw_lifecycle) {
        std::cerr << "watcher smoke failed: close_ok=" << close_ok
                  << " saw_lifecycle=" << saw_lifecycle << "\n";
        return 1;
    }

    std::cout << "watcher smoke: OK\n";
    return 0;
}
