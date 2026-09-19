#include <libpkgmanifest/manifest/manifest.hpp>
#include <libpkgmanifest/manifest/package.hpp>
#include <libpkgmanifest/manifest/nevra.hpp>
#include <libpkgmanifest/manifest/checksum.hpp>
#include <libpkgmanifest/common/repository.hpp>
#include <libpkgmanifest/common/repositories.hpp>
#include <libpkgmanifest/common/version.hpp>

#include <cassert>
#include <iostream>

int main() {
    using namespace libpkgmanifest::manifest;
    using namespace libpkgmanifest::common;

    // Test 1: Create Manifest and verify default document/version
    Manifest manifest;
    manifest.set_document("rpm-package-manifest");
    assert(manifest.get_document() == "rpm-package-manifest");
    std::cout << "PASS: Manifest document set/get" << std::endl;

    // Test 2: Create a Repository and add to Manifest
    Repository repo;
    repo.set_id("test-repo");
    repo.set_baseurl("https://example.com/repo");
    Repositories repos;
    repos.add(repo);
    assert(repos.size() == 1);
    assert(repos.contains("test-repo"));
    std::cout << "PASS: Repository add/contains" << std::endl;

    // Test 3: Create a Package with Nevra and add to Manifest
    Nevra nevra;
    nevra.set_name("testpkg");
    nevra.set_version("1.0");
    nevra.set_release("1.el9");
    nevra.set_arch("aarch64");

    Package pkg;
    pkg.set_repo_id("test-repo");
    pkg.set_location("Packages/t/testpkg-1.0-1.el9.aarch64.rpm");
    pkg.set_size(1024);
    pkg.set_nevra(nevra);

    Packages packages;
    packages.attach(repos);
    packages.add(pkg);
    assert(packages.get().size() == 1);
    std::cout << "PASS: Package add/get" << std::endl;

    manifest.set_packages(packages);
    manifest.set_repositories(repos);
    assert(manifest.get_packages().get().size() == 1);
    assert(manifest.get_repositories().size() == 1);
    std::cout << "PASS: Manifest round-trip" << std::endl;

    std::cout << "All tests passed." << std::endl;
    return 0;
}
