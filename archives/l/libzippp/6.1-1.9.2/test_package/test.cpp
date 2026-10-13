#include "libzippp.h"
#include <sys/stat.h>
#include <sys/utsname.h>
#include <unistd.h>
#include <fcntl.h>
#include <dlfcn.h>
#include <cerrno>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>

static int fail(const char* message) {
    std::cerr << "FAIL: " << message << " errno=" << errno << '\n';
    return 1;
}

int main(int argc, char** argv) {
    if (argc != 3 && argc != 4) return fail("arguments");
    const bool harmony = argc == 4 && std::string(argv[3]) == "--harmony";
    const std::string root = argv[1], libraries = argv[2];
    struct stat parent{};
    if (stat(root.c_str(), &parent) || !S_ISDIR(parent.st_mode)) return fail("private directory");
    void* loader = nullptr;
    if (harmony) {
        struct utsname platform{};
        if (uname(&platform) || std::string(platform.sysname) != "HarmonyOS" ||
            std::string(platform.machine) != "aarch64" ||
            root.find("/storage/Users/") != 0) return fail("HarmonyOS storage identity");
        loader = dlopen((libraries + "/libzippp.so.6.1.0").c_str(), RTLD_NOW | RTLD_LOCAL);
        if (!loader) { std::cerr << dlerror() << '\n'; return fail("signed HMDFS shared loader"); }
        void* close_symbol = dlsym(loader, "_ZN8libzippp10ZipArchive5closeEv");
        Dl_info loaded{};
        if (!close_symbol || !dladdr(close_symbol, &loaded) || !loaded.dli_fname ||
            (std::string(loaded.dli_fname) != libraries + "/libzippp.so.6.1.0" &&
             std::string(loaded.dli_fname) != libraries + "/libzippp.so.6" &&
             std::string(loaded.dli_fname) != libraries + "/libzippp.so"))
            return fail("loader symbol does not bind task library");
        std::cout << "loaded_library=" << loaded.dli_fname << '\n';
    }
    const std::string path = root + (harmony ? "/鸿蒙压缩包.zip" : "/consumer.zip");
    int fd = open(path.c_str(), O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (fd < 0) return fail("exclusive private archive");
    if (close(fd)) return fail("reserve close");
    const std::string bytes = "HarmonyOS UTF-8 payload: 中文\n";
    libzippp::ZipArchive archive(path);
    if (!archive.open(libzippp::ZipArchive::New) ||
        !archive.addData("目录/数据.txt", bytes.data(), bytes.size()) ||
        archive.close() != LIBZIPPP_OK) return fail("create ZIP with libzippp");
    struct stat actual{};
    if (stat(path.c_str(), &actual) || actual.st_size <= 0 ||
        actual.st_uid != parent.st_uid) return fail("storage owner projection");
    fd = open(path.c_str(), O_RDONLY);
    if (fd < 0 || fsync(fd) || close(fd)) return fail("archive persistence");
    libzippp::ZipArchive readback(path);
    if (!readback.open(libzippp::ZipArchive::ReadOnly)) return fail("reopen ZIP");
    const libzippp::ZipEntry entry = readback.getEntry("目录/数据.txt");
    if (entry.isNull() || entry.readAsText() != bytes ||
        readback.close() != LIBZIPPP_OK) return fail("exact UTF-8 ZIP readback");
    if (unlink(path.c_str()) || access(path.c_str(), F_OK) == 0 || errno != ENOENT)
        return fail("private archive cleanup");
    if (loader && dlclose(loader)) return fail("shared loader release");
    std::cout << "storage_parent_uid=" << parent.st_uid << " process_uid=" << getuid() << '\n';
    std::cout << (harmony ? "HARMONY_TEST_PASS=1/1" : "CONSUMER_TEST_PASS=1/1") << '\n';
    return 0;
}






