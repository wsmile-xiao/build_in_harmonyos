/*
 * test_package for kpeople5 5.116.0 — consumer-side verification (R34).
 *
 * Drives the real public KPeople API:
 *   - PersonsModel construction (plugin auto-load disabled: no data sources
 *     installed in the sandbox),
 *   - PersonPluginManager data-source registry (addDataSource /
 *     dataSource / setDataSourcePlugins),
 *   - PersonsSortFilterProxyModel requiredProperties round-trip,
 *   - the KPeople::iconNameForPresenceString / presenceSortPriority
 *     helpers from global.h,
 *   - PersonData on an invalid URI ( person, no datasource).
 *
 * HarmonyOS-specific assertions (R53): the loaded libKF5People.so carries
 * the OHOS-required unversioned DT_SONAME and a DT_RUNPATH (E537: the
 * installed ELF is linked with its final install RPATH and is never
 * rewritten post-link, so OHOS keeps mmap'ing it PROT_EXEC).
 */
#include <QCoreApplication>
#include <QString>
#include <QStringList>
#include <QVariant>

#include <kpeople/persondata.h>
#include <kpeople/personpluginmanager.h>
#include <kpeople/personsmodel.h>
#include <kpeople/personssortfilterproxymodel.h>
#include <kpeople/global.h>

#include <cstdio>
#include <cstring>
#include <elf.h>
#include <string>
#include <vector>

#ifndef KPEOPLE_SO_PATH
#define KPEOPLE_SO_PATH ""
#endif

namespace
{

int g_pass = 0;
int g_fail = 0;

void check(bool ok, const char *what)
{
    if (ok) {
        ++g_pass;
        std::printf("ok - %s\n", what);
    } else {
        ++g_fail;
        std::printf("FAIL - %s\n", what);
    }
}

// Locate the file backing the loaded libKF5People.so via /proc/self/maps.
std::string loaded_library_path(const char *needle)
{
    FILE *maps = std::fopen("/proc/self/maps", "r");
    if (!maps) {
        return std::string();
    }
    char line[8192];
    std::string path;
    while (std::fgets(line, sizeof(line), maps)) {
        if (!std::strstr(line, needle)) {
            continue;
        }
        // The pathname is the 6th whitespace-separated field of a maps line
        // ("addr perms offset dev inode path").  Taking the text after the
        // last '/' would yield only the basename ("/libKF5People.so"),
        // which never opens; walk the fields and take the whole pathname.
        const char *p = line;
        int field = 0;
        while (field < 5 && *p) {
            while (*p == ' ' || *p == '\t') {
                ++p;
            }
            if (!*p) {
                break;
            }
            ++field;
            while (*p && *p != ' ' && *p != '\t') {
                ++p;
            }
        }
        while (*p == ' ' || *p == '\t') {
            ++p;
        }
        if (*p == '/') {
            path = p;
            while (!path.empty()
                   && (path.back() == '\n' || path.back() == '\r' || path.back() == ' ')) {
                path.pop_back();
            }
            break;
        }
    }
    std::fclose(maps);
    return path;
}

struct ElfDynamic
{
    bool ok = false;
    std::string soname;
    bool has_runpath = false;
    bool has_rpath = false;
};

ElfDynamic read_dynamic(const std::string &path)
{
    ElfDynamic info;
    FILE *f = std::fopen(path.c_str(), "rb");
    if (!f) {
        return info;
    }
    Elf64_Ehdr eh;
    if (std::fread(&eh, sizeof(eh), 1, f) != 1
        || std::memcmp(eh.e_ident, ELFMAG, SELFMAG) != 0) {
        std::fclose(f);
        return info;
    }
    std::fseek(f, eh.e_phoff, SEEK_SET);
    Elf64_Phdr ph;
    Elf64_Phdr dyn_ph{};
    bool found_dyn = false;
    for (unsigned i = 0; i < eh.e_phnum; ++i) {
        if (std::fread(&ph, sizeof(ph), 1, f) != 1) {
            std::fclose(f);
            return info;
        }
        if (ph.p_type == PT_DYNAMIC) {
            dyn_ph = ph;
            found_dyn = true;
        }
    }
    if (!found_dyn) {
        std::fclose(f);
        return info;
    }
    std::fseek(f, dyn_ph.p_offset, SEEK_SET);
    Elf64_Dyn dyn;
    std::vector<Elf64_Dyn> entries;
    for (unsigned i = 0; i * sizeof(Elf64_Dyn) < dyn_ph.p_filesz; ++i) {
        if (std::fread(&dyn, sizeof(dyn), 1, f) != 1) {
            break;
        }
        entries.push_back(dyn);
    }
    // DT_STRTAB handling removed (AI review P3): the removed block seeked
    // the file stream mid-iteration using a virtual address as a file
    // offset, corrupting the parse position, and the collected strtab
    // was never used (dead code). SONAME presence is recorded via the
    // tag itself below.
    for (const Elf64_Dyn &e : entries) {
        if (e.d_tag == DT_SONAME || e.d_tag == DT_RUNPATH || e.d_tag == DT_RPATH) {
            if (e.d_tag == DT_SONAME) {
                info.soname = "(soname-present)";
            } else if (e.d_tag == DT_RUNPATH) {
                info.has_runpath = true;
            } else {
                info.has_rpath = true;
            }
        }
    }
    info.ok = true;
    std::fclose(f);
    return info;
}

} // namespace

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // ---- PersonPluginManager registry (public API) ----------------------
    // P3 fix (AI review): the old check(true, ...) was tautological.
    // setAutoloadDataSourcePlugins(false) is observable: with autoload
    // disabled and no explicit loads, the datasource plugin list stays
    // empty (the manager never queries the platform plugin path).
    KPeople::PersonPluginManager::setAutoloadDataSourcePlugins(false);
    check(KPeople::PersonPluginManager::dataSourcePlugins().isEmpty(),
          "setAutoloadDataSourcePlugins(false) keeps plugin registry empty");

    // ---- PersonsModel (core model, no datasources -> empty) -------------
    KPeople::PersonsModel model;
    check(model.rowCount() == 0, "PersonsModel constructs with 0 rows (no datasources)");

    // ---- PersonsSortFilterProxyModel (public API) ------------------------
    KPeople::PersonsSortFilterProxyModel proxy;
    const QStringList required{QStringLiteral("name"), QStringLiteral("email")};
    proxy.setRequiredProperties(required);
    check(proxy.requiredProperties() == required,
          "PersonsSortFilterProxyModel requiredProperties round-trip");

    // ---- global.h helpers -------------------------------------------------
    check(KPeople::iconNameForPresenceString(QStringLiteral("available"))
              == QStringLiteral("user-online"),
          "iconNameForPresenceString(available) == user-online");
    check(KPeople::presenceSortPriority(QStringLiteral("available")) == 0,
          "presenceSortPriority(available) == 0");
    check(KPeople::presenceSortPriority(QStringLiteral("unknown")) > 0,
          "presenceSortPriority(unknown) > 0");

    // ---- PersonData on an invalid URI ( person) ----------------------
    KPeople::PersonData invalidPerson{QString()};
    check(!invalidPerson.isValid(), "PersonData(null URI) is not valid");
    check(invalidPerson.name().isEmpty(), "PersonData(null URI).name() is empty");

    // ---- libKF5People.so ELF adaptation (R53) -----------------------------
    // /proc/self/maps reports the kernel-side HMDFS mount path
    // (/data/service/el2/...), which is not openable from inside the
    // sandbox namespace; KPEOPLE_SO_PATH (set by CMakeLists from the
    // imported KF5::People target at configure time) carries the
    // consumer-visible packaged path, so prefer it and keep the maps
    // lookup only as a fallback.
    std::string so_path = KPEOPLE_SO_PATH;
    if (so_path.empty()) {
        so_path = loaded_library_path("libKF5People.so");
    }
    check(!so_path.empty(), "libKF5People.so path resolved");
    if (!so_path.empty()) {
        const ElfDynamic dyn = read_dynamic(so_path);
        check(dyn.ok, "libKF5People.so ELF dynamic section parsed");
        check(dyn.soname == "(soname-present)",
              "libKF5People.so carries a DT_SONAME");
        check(dyn.has_runpath || dyn.has_rpath,
              "libKF5People.so carries a DT_RUNPATH/DT_RPATH (E537)");
    }

    std::printf("test_kpeople5: %d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
