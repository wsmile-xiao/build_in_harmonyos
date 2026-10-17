// test_package/test.cpp — consumer test for kitemviews5 5.116.0 on HarmonyOS PC.
//
// R34: links KF5::ItemViews and actually drives the public API
//      (KListWidgetSearchLine, KTreeWidgetSearchLine, KFilterProxySearchLine,
//      KCategorizedSortFilterProxyModel, KCategorizedView, KCategoryDrawer).
// R53: asserts the HarmonyOS adaptation path:
//      1. QApplication runs under the OHOS "offscreen" QPA platform plugin
//         (the headless GUI path used by a Widgets library on HarmonyOS);
//      2. the loaded libKF5ItemViews.so carries the OHOS-required unversioned
//         DT_SONAME `libKF5ItemViews.so` (CMAKE_PLATFORM_NO_VERSIONED_SONAME)
//         and a DT_RUNPATH (E537: CMAKE_BUILD_WITH_INSTALL_RPATH=ON, so the
//         installed ELF is not rewritten after linking and stays loadable).
#include <elf.h>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include <QApplication>
#include <QListWidget>
#include <QSortFilterProxyModel>
#include <QStandardItem>
#include <QStandardItemModel>
#include <QString>
#include <QStringList>
#include <QTreeWidget>
#include <QTreeWidgetItem>

#include <KCategorizedSortFilterProxyModel>
#include <KCategorizedView>
#include <KCategoryDrawer>
#include <KFilterProxySearchLine>
#include <KListWidgetSearchLine>
#include <KTreeWidgetSearchLine>

// Injected by CMake ($<TARGET_FILE:KF5::ItemViews>): the packaged .so path.
#ifndef KITEMVIEWS_SO_PATH
#define KITEMVIEWS_SO_PATH ""
#endif

namespace {

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

// Locate the file backing the loaded libKF5ItemViews.so via /proc/self/maps.
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
        const char *slash = std::strrchr(line, '/');
        if (slash) {
            path = slash;
            while (!path.empty() && (path.back() == '\n' || path.back() == '\r' || path.back() == ' ')) {
                path.pop_back();
            }
            break;
        }
    }
    std::fclose(maps);
    return path;
}

struct ElfDynamic {
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
    if (std::fread(&eh, sizeof(eh), 1, f) != 1 || std::memcmp(eh.e_ident, ELFMAG, SELFMAG) != 0
        || eh.e_ident[EI_CLASS] != ELFCLASS64) {
        std::fclose(f);
        return info;
    }
    struct Load {
        Elf64_Addr vaddr;
        Elf64_Off offset;
        Elf64_Xword filesz;
    };
    std::vector<Load> loads;
    Elf64_Phdr dyn_ph;
    bool have_dyn = false;
    for (int i = 0; i < eh.e_phnum; ++i) {
        if (std::fseek(f, static_cast<long>(eh.e_phoff + static_cast<Elf64_Off>(i) * eh.e_phentsize), SEEK_SET) != 0) {
            std::fclose(f);
            return info;
        }
        Elf64_Phdr ph;
        if (std::fread(&ph, sizeof(ph), 1, f) != 1) {
            std::fclose(f);
            return info;
        }
        if (ph.p_type == PT_LOAD) {
            loads.push_back({ph.p_vaddr, ph.p_offset, ph.p_filesz});
        } else if (ph.p_type == PT_DYNAMIC) {
            dyn_ph = ph;
            have_dyn = true;
        }
    }
    if (!have_dyn) {
        std::fclose(f);
        return info;
    }
    auto vaddr_to_off = [&loads](Elf64_Addr v) -> Elf64_Off {
        for (const Load &s : loads) {
            if (v >= s.vaddr && v < s.vaddr + s.filesz) {
                return s.offset + (v - s.vaddr);
            }
        }
        return 0;
    };
    if (dyn_ph.p_filesz == 0 || dyn_ph.p_filesz % sizeof(Elf64_Dyn) != 0) {
        std::fclose(f);
        return info;
    }
    std::vector<Elf64_Dyn> dyn(dyn_ph.p_filesz / sizeof(Elf64_Dyn));
    if (std::fseek(f, static_cast<long>(dyn_ph.p_offset), SEEK_SET) != 0
        || std::fread(dyn.data(), sizeof(Elf64_Dyn), dyn.size(), f) != dyn.size()) {
        std::fclose(f);
        return info;
    }
    Elf64_Addr strtab = 0;
    Elf64_Xword strsz = 0;
    bool have_soname = false;
    Elf64_Word soname_off = 0;
    for (const Elf64_Dyn &d : dyn) {
        if (d.d_tag == DT_STRTAB) {
            strtab = d.d_un.d_ptr;
        } else if (d.d_tag == DT_STRSZ) {
            strsz = d.d_un.d_val;
        } else if (d.d_tag == DT_SONAME) {
            soname_off = d.d_un.d_val;
            have_soname = true;
        } else if (d.d_tag == DT_RUNPATH) {
            info.has_runpath = true;
        } else if (d.d_tag == DT_RPATH) {
            info.has_rpath = true;
        }
    }
    if (have_soname && strtab != 0 && strsz != 0) {
        const Elf64_Off off = vaddr_to_off(strtab + soname_off);
        if (off != 0) {
            char buf[512];
            if (std::fseek(f, static_cast<long>(off), SEEK_SET) == 0) {
                const size_t n = std::fread(buf, 1, sizeof(buf) - 1, f);
                buf[n] = '\0';
                info.soname = buf;
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
    // Make the headless OHOS QPA explicit so the test also runs standalone.
    if (qEnvironmentVariableIsEmpty("QT_QPA_PLATFORM")) {
        qputenv("QT_QPA_PLATFORM", "offscreen");
    }
    QApplication app(argc, argv);

    // ── R53 (1): the OHOS offscreen QPA platform plugin must be active. ──
    const QString platformName = QApplication::platformName();
    std::printf("info - QApplication platformName = %s\n", qPrintable(platformName));
    check(platformName == QLatin1String("offscreen"),
          "HarmonyOS: QApplication runs on the offscreen QPA platform plugin");

    // ── KListWidgetSearchLine ────────────────────────────────────────────
    QListWidget list;
    list.addItem(QStringLiteral("apple"));
    list.addItem(QStringLiteral("banana"));
    list.addItem(QStringLiteral("cherry"));
    KListWidgetSearchLine listSearch(nullptr, &list);
    check(listSearch.listWidget() == &list, "KListWidgetSearchLine::listWidget round-trips");
    listSearch.updateSearch(QStringLiteral("an"));
    check(!list.item(1)->isHidden() && list.item(0)->isHidden() && list.item(2)->isHidden(),
          "KListWidgetSearchLine filters matching items");
    listSearch.updateSearch(QString());
    check(!list.item(0)->isHidden() && !list.item(2)->isHidden(),
          "KListWidgetSearchLine restores items on empty search");

    // ── KTreeWidgetSearchLine ────────────────────────────────────────────
    QTreeWidget tree;
    tree.setColumnCount(1);
    QTreeWidgetItem *treeApple = new QTreeWidgetItem(&tree, QStringList() << QStringLiteral("apple"));
    QTreeWidgetItem *treeBanana = new QTreeWidgetItem(&tree, QStringList() << QStringLiteral("banana"));
    KTreeWidgetSearchLine treeSearch(nullptr, &tree);
    check(treeSearch.treeWidget() == &tree, "KTreeWidgetSearchLine::treeWidget round-trips");
    treeSearch.updateSearch(QStringLiteral("ban"));
    check(!treeBanana->isHidden() && treeApple->isHidden(),
          "KTreeWidgetSearchLine filters matching tree items");

    // ── KFilterProxySearchLine ───────────────────────────────────────────
    QStandardItemModel proxySource;
    proxySource.appendRow(new QStandardItem(QStringLiteral("apple")));
    proxySource.appendRow(new QStandardItem(QStringLiteral("banana")));
    proxySource.appendRow(new QStandardItem(QStringLiteral("cherry")));
    QSortFilterProxyModel filterProxy;
    filterProxy.setSourceModel(&proxySource);
    KFilterProxySearchLine searchLine;
    searchLine.setProxy(&filterProxy);
    check(searchLine.lineEdit() != nullptr, "KFilterProxySearchLine exposes its line edit");
    searchLine.setText(QStringLiteral("ban"));
    check(filterProxy.rowCount() == 1
              && filterProxy.index(0, 0).data().toString() == QLatin1String("banana"),
          "KFilterProxySearchLine drives QSortFilterProxyModel filtering");

    // ── KCategorizedSortFilterProxyModel ─────────────────────────────────
    QStandardItemModel categorizedSource;
    const struct {
        const char *name;
        int category;
        const char *categoryName;
    } rows[] = {
        {"Zebra", 2, "animals"},
        {"Apple", 1, "fruit"},
        {"Mango", 1, "fruit"},
        {"Berry", 0, "berries"},
    };
    for (const auto &row : rows) {
        auto *item = new QStandardItem(QString::fromUtf8(row.name));
        item->setData(row.category, KCategorizedSortFilterProxyModel::CategorySortRole);
        item->setData(QString::fromUtf8(row.categoryName),
                      KCategorizedSortFilterProxyModel::CategoryDisplayRole);
        categorizedSource.appendRow(item);
    }
    KCategorizedSortFilterProxyModel categorizedProxy;
    categorizedProxy.setSourceModel(&categorizedSource);
    check(!categorizedProxy.isCategorizedModel(),
          "KCategorizedSortFilterProxyModel categorization is off by default");
    categorizedProxy.setCategorizedModel(true);
    check(categorizedProxy.isCategorizedModel(),
          "KCategorizedSortFilterProxyModel::setCategorizedModel enables categorization");
    categorizedProxy.sort(0, Qt::AscendingOrder);
    bool categoryOrderOk = categorizedProxy.rowCount() == 4;
    int previous = -1;
    for (int i = 0; categoryOrderOk && i < categorizedProxy.rowCount(); ++i) {
        const QVariant sortRole =
            categorizedProxy.data(categorizedProxy.index(i, 0),
                                  KCategorizedSortFilterProxyModel::CategorySortRole);
        const int current = sortRole.toInt();
        if (current < previous) {
            categoryOrderOk = false;
        }
        previous = current;
    }
    check(categoryOrderOk, "KCategorizedSortFilterProxyModel sorts rows by category");

    // ── KCategorizedView + KCategoryDrawer ───────────────────────────────
    KCategorizedView view;
    KCategoryDrawer drawer(&view);
    view.setModel(&categorizedProxy);
    view.setCategoryDrawer(&drawer);
    check(view.model() == &categorizedProxy, "KCategorizedView accepts the categorized model");
    check(view.categoryDrawer() == &drawer, "KCategorizedView::setCategoryDrawer round-trips");

    // ── R53 (2): OHOS ELF adaptation of the packaged library. ────────────
    std::string libPath = KITEMVIEWS_SO_PATH;
    if (libPath.empty()) {
        libPath = loaded_library_path("libKF5ItemViews.so");
    }
    check(!libPath.empty(), "HarmonyOS: libKF5ItemViews.so is mapped into the process");
    const ElfDynamic dyn = read_dynamic(libPath);
    std::printf("info - libKF5ItemViews.so = %s\n", libPath.c_str());
    std::printf("info - DT_SONAME = %s (RUNPATH=%d RPATH=%d)\n",
                dyn.soname.c_str(), int(dyn.has_runpath), int(dyn.has_rpath));
    check(dyn.ok && dyn.soname == "libKF5ItemViews.so",
          "HarmonyOS: libKF5ItemViews.so carries the unversioned DT_SONAME");
    check(dyn.ok && dyn.has_runpath,
          "HarmonyOS: libKF5ItemViews.so carries a DT_RUNPATH (E537 install-RPATH link)");

    std::printf("SUMMARY: %d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
