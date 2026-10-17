// OpenKIM models collection consumer probe (pure-data package).
//
// Usage: openkim_models_probe <package_folder>
//
// Verifies the share/openkim-models installation tree:
//   G1 root structure (is-dir + CMakeLists.txt + LICENSE) ......... 3
//   G2 three collection subdirs present .......................... 3
//   G3 item-dir counts 34 / 445 / 96 ............................. 3
//   G4 nested helpers/ dir of the Tersoff_LAMMPS driver .......... 1
//   G5 per-item invariants: every one of the 575 item dirs has
//      kimspec.edn (exists, non-empty) and CMakeLists.txt ......... 1725
//   G6 global counts: 4228 files (+per-dir consistency), 575
//      kimspec.edn, 575 item CMakeLists.txt, 606 item LICENSE* ... 5
//   G7 content spot checks (LICENSE CDDL text, 3 extended-id
//      kimspec checks, params file, bib citation) ................ 6
//   G8 negative controls (missing/empty kimspec rejected) ........ 3
// Total assertions: 1751
//
// C++11 + POSIX dirent (proven on the HarmonyOS PC device by the
// kicad-library probe family).

#include <dirent.h>
#include <sys/stat.h>
#include <unistd.h>  // rmdir (POSIX; not transitively visible on OHOS clang)
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

int g_checks = 0;

void check(bool cond, const std::string& what) {
    ++g_checks;
    if (!cond) {
        std::cerr << "[FAIL] " << what << std::endl;
        throw std::runtime_error(what);
    }
}

std::string msg(size_t got, size_t expected, const std::string& what) {
    std::ostringstream os;
    os << what << ": got " << got << ", expected " << expected;
    return os.str();
}

bool is_dir(const std::string& p) {
    struct stat st;
    if (::stat(p.c_str(), &st) != 0) return false;
    return S_ISDIR(st.st_mode);
}

bool is_file(const std::string& p) {
    struct stat st;
    if (::stat(p.c_str(), &st) != 0) return false;
    return S_ISREG(st.st_mode);
}

std::vector<std::string> list_dirs(const std::string& p) {
    std::vector<std::string> out;
    DIR* d = ::opendir(p.c_str());
    if (!d) throw std::runtime_error("opendir failed: " + p);
    while (dirent* e = ::readdir(d)) {
        std::string n = e->d_name;
        if (n == "." || n == "..") continue;
        if (is_dir(p + "/" + n)) out.push_back(n);
    }
    ::closedir(d);
    return out;
}

size_t count_files_rec(const std::string& p) {
    size_t n = 0;
    DIR* d = ::opendir(p.c_str());
    if (!d) throw std::runtime_error("opendir failed: " + p);
    while (dirent* e = ::readdir(d)) {
        std::string nm = e->d_name;
        if (nm == "." || nm == "..") continue;
        std::string fp = p + "/" + nm;
        if (is_dir(fp)) n += count_files_rec(fp);
        else ++n;
    }
    ::closedir(d);
    return n;
}

size_t count_files_prefixed(const std::string& p, const std::string& prefix) {
    size_t n = 0;
    DIR* d = ::opendir(p.c_str());
    if (!d) throw std::runtime_error("opendir failed: " + p);
    while (dirent* e = ::readdir(d)) {
        std::string nm = e->d_name;
        if (nm == "." || nm == "..") continue;
        if (nm.compare(0, prefix.size(), prefix) == 0 &&
            is_file(p + "/" + nm))
            ++n;
    }
    ::closedir(d);
    return n;
}

std::string read_file(const std::string& p) {
    std::ifstream f(p.c_str(), std::ios::binary);
    if (!f) throw std::runtime_error("cannot open " + p);
    std::stringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

bool has_substr(const std::string& hay, const std::string& needle) {
    return hay.find(needle) != std::string::npos;
}

// MinGW's mkdir takes no mode argument; POSIX takes (path, mode).
#ifdef _WIN32
int make_dir(const char* p) { return ::mkdir(p); }
#else
int make_dir(const char* p) { return ::mkdir(p, 0755); }
#endif

// One item dir (model-driver / portable-model / simulator-model) must
// carry its KIM metadata trio. Throws on the first violation.
void verify_item_dir(const std::string& p) {
    check(is_file(p + "/kimspec.edn"), p + ": kimspec.edn missing");
    check(!read_file(p + "/kimspec.edn").empty(), p + ": kimspec.edn empty");
    check(is_file(p + "/CMakeLists.txt"), p + ": CMakeLists.txt missing");
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc < 2) {
            std::cerr << "usage: openkim_models_probe <package_folder>\n";
            return 2;
        }
        const std::string root = argv[1];

        // G1 root structure
        check(is_dir(root), "package folder is a directory");
        check(is_file(root + "/CMakeLists.txt"),
              "collection root CMakeLists.txt present");
        check(is_file(root + "/LICENSE"), "collection root LICENSE present");
        std::cout << "[OK] G1 root structure" << std::endl;

        // G2 collection subdirs
        check(is_dir(root + "/model-drivers"), "model-drivers/ present");
        check(is_dir(root + "/portable-models"), "portable-models/ present");
        check(is_dir(root + "/simulator-models"),
              "simulator-models/ present");
        std::cout << "[OK] G2 collection subdirs" << std::endl;

        // G3 item-dir counts
        std::vector<std::string> md = list_dirs(root + "/model-drivers");
        std::vector<std::string> pm = list_dirs(root + "/portable-models");
        std::vector<std::string> sm = list_dirs(root + "/simulator-models");
        check(md.size() == 34, msg(md.size(), 34, "model-drivers item dirs"));
        check(pm.size() == 445, msg(pm.size(), 445, "portable-models item dirs"));
        check(sm.size() == 96, msg(sm.size(), 96, "simulator-models item dirs"));
        std::cout << "[OK] G3 item-dir counts 34/445/96" << std::endl;

        // G4 nested helpers/ dir of the Tersoff_LAMMPS driver
        check(is_dir(root + "/model-drivers/"
                     "Tersoff_LAMMPS__MD_077075034781_004/helpers"),
              "Tersoff_LAMMPS driver helpers/ subdir present");
        std::cout << "[OK] G4 nested helpers/ dir" << std::endl;

        // G5 per-item invariants (3 checks x 575 dirs)
        for (size_t i = 0; i < md.size(); ++i)
            verify_item_dir(root + "/model-drivers/" + md[i]);
        for (size_t i = 0; i < pm.size(); ++i)
            verify_item_dir(root + "/portable-models/" + pm[i]);
        for (size_t i = 0; i < sm.size(); ++i)
            verify_item_dir(root + "/simulator-models/" + sm[i]);
        std::cout << "[OK] G5 per-item kimspec/CMakeLists invariants ("
                  << md.size() + pm.size() + sm.size() << " dirs)"
                  << std::endl;

        // G6 global counts
        check(count_files_rec(root) == 4228,
              msg(count_files_rec(root), 4228, "total files"));
        check(count_files_rec(root + "/model-drivers") +
                  count_files_rec(root + "/portable-models") +
                  count_files_rec(root + "/simulator-models") + 2 == 4228,
              "per-dir file sums equal total");
        // kimspec.edn: one per item dir (575), CMakeLists.txt: 575 + root
        size_t kimspec = 0, cmake = 0, lic = 0;
        for (size_t i = 0; i < md.size(); ++i) {
            kimspec += is_file(root + "/model-drivers/" + md[i] + "/kimspec.edn");
            cmake += is_file(root + "/model-drivers/" + md[i] + "/CMakeLists.txt");
            lic += count_files_prefixed(root + "/model-drivers/" + md[i],
                                        "LICENSE");
        }
        for (size_t i = 0; i < pm.size(); ++i) {
            kimspec += is_file(root + "/portable-models/" + pm[i] + "/kimspec.edn");
            cmake += is_file(root + "/portable-models/" + pm[i] + "/CMakeLists.txt");
            lic += count_files_prefixed(root + "/portable-models/" + pm[i],
                                        "LICENSE");
        }
        for (size_t i = 0; i < sm.size(); ++i) {
            kimspec += is_file(root + "/simulator-models/" + sm[i] + "/kimspec.edn");
            cmake += is_file(root + "/simulator-models/" + sm[i] + "/CMakeLists.txt");
            lic += count_files_prefixed(root + "/simulator-models/" + sm[i],
                                        "LICENSE");
        }
        check(kimspec == 575, msg(kimspec, 575, "kimspec.edn files"));
        check(cmake == 575, msg(cmake, 575, "item CMakeLists.txt files"));
        check(lic == 606, msg(lic, 606, "item LICENSE* files"));
        std::cout << "[OK] G6 global counts (4228/575/575/606)" << std::endl;

        // G7 content spot checks
        check(has_substr(read_file(root + "/LICENSE"),
                         "COMMON DEVELOPMENT AND DISTRIBUTION LICENSE"),
              "root LICENSE is CDDL-1.0 text");
        check(has_substr(
                  read_file(root + "/model-drivers/"
                            "LJ_Shifted__MD_498634107543_004/kimspec.edn"),
                  "MD_498634107543_004"),
              "LJ_Shifted driver kimspec carries its extended-id");
        check(has_substr(
                  read_file(root + "/portable-models/"
                            "EAM_Dynamo_AcklandVitek_1990_Cu__MO_642748370624_000/"
                            "kimspec.edn"),
                  "MO_642748370624_000"),
              "EAM Ackland-Vitek Cu model kimspec carries its extended-id");
        check(has_substr(
                  read_file(root + "/simulator-models/"
                            "Sim_LAMMPS_ADP_ApostolMishin_2011_AlCu__SM_667696763561_000/"
                            "kimspec.edn"),
                  "SM_667696763561_000"),
              "Sim_LAMMPS ADP AlCu kimspec carries its extended-id");
        check(!read_file(root + "/portable-models/"
                         "EAM_Dynamo_AcklandVitek_1990_Cu__MO_642748370624_000/"
                         "Cu2.eam.fs")
                   .empty(),
              "Cu2.eam.fs params data non-empty");
        check(has_substr(
                  read_file(root + "/portable-models/"
                            "EAM_Dynamo_AcklandVitek_1990_Cu__MO_642748370624_000/"
                            "kimcite-MO_642748370624_000.bib"),
                  "@"),
              "kimcite bib carries a citation entry");
        std::cout << "[OK] G7 content spot checks" << std::endl;

        // G8 negative controls: a fake item dir without / with an empty
        // kimspec.edn must be rejected by verify_item_dir.
        std::string tmp = ".";
        if (const char* t = std::getenv("TMPDIR")) tmp = t;
        else if (const char* t = std::getenv("TEMP")) tmp = t;
        const std::string fake = tmp + "/omk-probe-negative";
        ::rmdir(fake.c_str());
        if (make_dir(fake.c_str()) != 0)
            throw std::runtime_error("cannot create negative scratch dir");
        bool threw = false;
        try { verify_item_dir(fake); } catch (...) { threw = true; }
        check(threw, "negative: dir without kimspec.edn is rejected");
        {   // empty kimspec + CMakeLists present -> still rejected
            std::ofstream(fake + "/kimspec.edn", std::ios::binary).close();
            std::ofstream(fake + "/CMakeLists.txt", std::ios::binary).close();
        }
        threw = false;
        try { verify_item_dir(fake); } catch (...) { threw = true; }
        check(threw, "negative: dir with empty kimspec.edn is rejected");
        ::remove((fake + "/kimspec.edn").c_str());
        ::remove((fake + "/CMakeLists.txt").c_str());
        ::rmdir(fake.c_str());
        std::cout << "[OK] G8 negative controls" << std::endl;

        std::cout << "openkim_models_probe: all assertions passed ("
                  << g_checks << ")" << std::endl;
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "[FAIL] " << e.what() << std::endl;
        return 1;
    }
}
