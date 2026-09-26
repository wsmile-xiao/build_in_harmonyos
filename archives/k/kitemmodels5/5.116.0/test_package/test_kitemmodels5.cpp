// test_package/test_kitemmodels5.cpp — consumer test for kitemmodels5
// 5.116.0 on HarmonyOS PC.
//
// R34: links KF5::ItemModels and actually drives the public API
//      (KConcatenateRowsProxyModel, KExtraColumnsProxyModel,
//      KDescendantsProxyModel, KNumberModel, KSelectionProxyModel,
//      KModelIndexProxyMapper, KRecursiveFilterProxyModel).
// R53: asserts the HarmonyOS adaptation path: the packaged libKF5ItemModels.so
//      carries the OHOS-required unversioned DT_SONAME `libKF5ItemModels.so`
//      (CMAKE_PLATFORM_NO_VERSIONED_SONAME) and a DT_RUNPATH (E537:
//      CMAKE_BUILD_WITH_INSTALL_RPATH=ON, so the installed ELF is not
//      rewritten after linking and stays loadable).
#include <elf.h>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include <QCoreApplication>
#include <QItemSelection>
#include <QItemSelectionModel>
#include <QSortFilterProxyModel>
#include <QStandardItem>
#include <QStandardItemModel>
#include <QString>
#include <QTest>

#include <KConcatenateRowsProxyModel>
#include <KDescendantsProxyModel>
#include <KExtraColumnsProxyModel>
#include <KModelIndexProxyMapper>
#include <KNumberModel>
#include <KRecursiveFilterProxyModel>
#include <KRearrangeColumnsProxyModel>
#include <KSelectionProxyModel>

// Injected by CMake ($<TARGET_FILE:KF5::ItemModels>): the packaged .so path.
#ifndef KITEMMODELS_SO_PATH
#define KITEMMODELS_SO_PATH ""
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
    if (std::fread(&eh, sizeof(eh), 1, f) != 1
        || std::memcmp(eh.e_ident, ELFMAG, SELFMAG) != 0
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
        if (std::fseek(f, static_cast<long>(eh.e_phoff
                + static_cast<Elf64_Off>(i) * eh.e_phentsize), SEEK_SET) != 0) {
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
    if (!have_dyn || dyn_ph.p_filesz == 0
        || dyn_ph.p_filesz % sizeof(Elf64_Dyn) != 0) {
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
        Elf64_Addr v = strtab + soname_off;
        Elf64_Off off = 0;
        for (const Load &s : loads) {
            if (v >= s.vaddr && v < s.vaddr + s.filesz) {
                off = s.offset + (v - s.vaddr);
                break;
            }
        }
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
    QCoreApplication app(argc, argv);

    QStandardItemModel source;
    source.insertRows(0, 3);
    source.insertColumns(0, 2);
    for (int r = 0; r < 3; ++r) {
        for (int c = 0; c < 2; ++c) {
            source.setData(source.index(r, c),
                           QString("cell %1-%2").arg(r).arg(c));
        }
    }

    // ── KConcatenateRowsProxyModel (KF5-only API) ───────────────────────
    QStandardItemModel second;
    second.insertRows(0, 1);
    second.insertColumns(0, 1);
    second.setData(second.index(0, 0), "second");
    KConcatenateRowsProxyModel concat;
    concat.addSourceModel(&source);
    concat.addSourceModel(&second);
    check(concat.rowCount() == 4,
          "KConcatenateRowsProxyModel concatenates rows (3+1=4)");
    check(concat.index(3, 0).data().toString() == QLatin1String("second"),
          "KConcatenateRowsProxyModel maps the second source model");

    // ── KExtraColumnsProxyModel (deriving: it is abstract) ──────────────
    class ExtraModel : public KExtraColumnsProxyModel
    {
    public:
        explicit ExtraModel(QAbstractItemModel *src)
            : KExtraColumnsProxyModel()
        {
            setSourceModel(src);
            appendColumn();
        }
        QVariant extraColumnData(const QModelIndex &parent, int row,
                                 int extraColumn, int role) const override
        {
            if (role == Qt::DisplayRole && extraColumn == 0) {
                return QStringLiteral("extra %1").arg(row);
            }
            return QVariant();
        }
    };
    ExtraModel extra(&source);
    check(extra.columnCount() == 3,
          "KExtraColumnsProxyModel appends an extra column (2+1=3)");
    check(extra.index(0, 0).data().toString() == source.index(0, 0).data().toString(),
          "KExtraColumnsProxyModel maps source data");
    check(extra.index(0, 2).data().toString() == QLatin1String("extra 0"),
          "KExtraColumnsProxyModel serves the derived extra column data");

    // ── KDescendantsProxyModel ──────────────────────────────────────────
    QStandardItemModel tree;
    QStandardItem *root = new QStandardItem("root");
    root->appendRow(new QStandardItem("child1"));
    root->appendRow(new QStandardItem("child2"));
    tree.appendRow(root);
    KDescendantsProxyModel flat;
    flat.setSourceModel(&tree);
    check(flat.rowCount() == 3,
          "KDescendantsProxyModel flattens the tree (1 root + 2 children)");

    // ── KNumberModel ────────────────────────────────────────────────────
    KNumberModel numbers;
    numbers.setMinimumValue(1);
    numbers.setMaximumValue(10);
    numbers.setStepSize(2);
    check(numbers.rowCount() == 5, "KNumberModel generates 5 steps (1..10 step 2)");
    check(numbers.index(0, 0).data().toString() == QLatin1String("1"),
          "KNumberModel first value formats to \"1\"");
    check(numbers.index(4, 0).data().toString() == QLatin1String("9"),
          "KNumberModel last value formats to \"9\"");

    // ── KSelectionProxyModel ────────────────────────────────────────────
    QItemSelectionModel selectionModel(&source);
    selectionModel.select(
        QItemSelection(source.index(0, 0), source.index(0, 1)),
        QItemSelectionModel::Select);
    KSelectionProxyModel filtered(&selectionModel);
    filtered.setSourceModel(&source);
    filtered.setFilterBehavior(KSelectionProxyModel::ExactSelection);
    check(filtered.rowCount() == 1,
          "KSelectionProxyModel shows exactly the selected row");

    // ── KModelIndexProxyMapper ──────────────────────────────────────────
    QSortFilterProxyModel chain1;
    chain1.setSourceModel(&source);
    QSortFilterProxyModel chain2;
    chain2.setSourceModel(&source);
    KModelIndexProxyMapper mapper(&chain1, &chain2);
    const QModelIndex mapped = mapper.mapLeftToRight(chain1.index(1, 1));
    check(mapped.isValid() && mapped.row() == 1 && mapped.column() == 1,
          "KModelIndexProxyMapper maps indexes between proxy chains");

    // ── KRecursiveFilterProxyModel ──────────────────────────────────────
    KRecursiveFilterProxyModel recursive;
    recursive.setSourceModel(&tree);
    recursive.setFilterFixedString("child1");
    check(recursive.rowCount() == 1,
          "KRecursiveFilterProxyModel keeps the parent of matching children");

    // ── R53: the packaged ELF carries the OHOS soname/runpath rules ─────
    const std::string soPath = KITEMMODELS_SO_PATH;
    if (!soPath.empty()) {
        const ElfDynamic dyn = read_dynamic(soPath);
        check(dyn.ok, "HarmonyOS: libKF5ItemModels.so ELF dynamic section is readable");
        if (dyn.ok) {
            check(dyn.soname == "libKF5ItemModels.so",
                  "HarmonyOS: unversioned DT_SONAME libKF5ItemModels.so");
            check(dyn.has_runpath || dyn.has_rpath,
                  "HarmonyOS: libKF5ItemModels.so carries a DT_RUNPATH (E537)");
        }
    }

    std::printf("kitemmodels5 consumer: %d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
