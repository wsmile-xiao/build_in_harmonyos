/*
 * Test for libfm-qt — verifies the library can be linked and basic API
 * functions work correctly on HarmonyOS PC. Compiles as C++ (libfm-qt is a
 * C++/Qt library).
 *
 * Uses real 2.4.0 APIs only:
 *  - Fm::FilePath::fromLocalPath()/uri()/baseName()/parent()/homeDir()
 *    (baseName()/uri() return CStrPtr, accessed via .get()/->)
 *  - Fm::Folder::fromPath() returns std::shared_ptr<Folder> (->/.get())
 *  - Fm::FolderModel can be instantiated.
 */
#include <cstdio>
#include <memory>

#include <libfm-qt6/libfmqt.h>
#include <libfm-qt6/core/filepath.h>
#include <libfm-qt6/core/folder.h>
#include <libfm-qt6/foldermodel.h>

static int tests = 0, passed = 0;

#define CHECK(cond, msg) do { tests++; if (cond) { passed++; } \
    else { std::fprintf(stderr, "FAIL: %s\n", msg); return 1; } } while (0)

int main() {
    /* 1. FilePath API — real path objects from "/" */
    Fm::FilePath fp = Fm::FilePath::fromLocalPath("/");
    CHECK(fp.isValid(), "FilePath::fromLocalPath(\"/\") is valid");
    CHECK(fp.uri() != nullptr, "FilePath::uri() returns a URI");
    // baseName of "/" is a CStrPtr; verify it is non-null.
    CHECK(fp.baseName() != nullptr, "FilePath::baseName() works");
    CHECK(fp.parent().isValid() || fp.isValid(), "FilePath::parent() is callable");
    Fm::FilePath home = Fm::FilePath::homeDir();
    CHECK(home.isValid(), "FilePath::homeDir() is valid");

    /* 2. Folder API — open "/" and verify a real object with valid path */
    auto folder = Fm::Folder::fromPath(fp);
    CHECK(folder != nullptr, "Folder::fromPath(\"/\") returns non-null");
    if (folder) {
        CHECK(folder->path().uri().get() != nullptr, "Folder::path() has a URI");
        // folder->isValid() must be callable; enumerating files would require
        // an async load, so only verify the object contract above.
        (void)folder->isValid();
    }

    /* 3. FolderModel API — verify the type can be instantiated */
    std::shared_ptr<Fm::FolderModel> model = std::make_shared<Fm::FolderModel>();
    CHECK(model != nullptr, "FolderModel instantiation works");

    std::printf("libfm-qt API test: %d/%d passed\n", passed, tests);
    return (passed == tests) ? 0 : 1;
}