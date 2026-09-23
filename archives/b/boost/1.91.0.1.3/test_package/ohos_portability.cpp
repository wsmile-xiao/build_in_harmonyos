#include <atomic>
#include <fstream>
#include <string>

#include <boost/filesystem.hpp>
#include <boost/thread.hpp>

int main() {
    namespace fs = boost::filesystem;
    const fs::path root("boost-ohos-portability-test");
    const fs::path source = root / "source.txt";
    const fs::path destination = root / "destination.txt";

    fs::remove_all(root);
    int failures = !fs::create_directories(root);
    {
        std::ofstream output(source.string(), std::ios::binary);
        output << "boost-ohos";
    }
    fs::copy_file(source, destination, fs::copy_options::overwrite_existing);
    failures += !fs::exists(destination) || fs::file_size(destination) != 10;

    std::atomic<int> thread_result{0};
    boost::thread worker([&thread_result]() { thread_result.store(191); });
    worker.join();
    failures += thread_result.load() != 191;

    fs::remove_all(root);
    return failures;
}
