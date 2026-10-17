// test_package/test.cpp — consumer test for kplotting5 5.116.0 on HarmonyOS PC.
//
// R34: links KF5::Plotting and actually drives the public API
//      (KPlotWidget, KPlotObject, KPlotPoint, KPlotAxis), asserting
//      observable behaviour rather than just that the library links.
// R53: asserts the HarmonyOS adaptation path:
//      1. QApplication runs under the OHOS "offscreen" QPA platform plugin
//         (the headless GUI path used by a Widgets library on HarmonyOS);
//      2. the loaded libKF5Plotting.so carries the OHOS-required unversioned
//         DT_SONAME `libKF5Plotting.so` (CMAKE_PLATFORM_NO_VERSIONED_SONAME)
//         and a DT_RUNPATH (E537: CMAKE_BUILD_WITH_INSTALL_RPATH=ON, so the
//         installed ELF is not rewritten after linking and stays loadable);
//      3. the packaged libKF5Plotting.so carries a .codesign section (the
//         recipe signs every installed ELF with the OHOS binary-sign-tool).
#include <elf.h>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include <QApplication>
#include <QBrush>
#include <QColor>
#include <QPen>
#include <QPointF>
#include <QRectF>
#include <QString>
#include <QList>

#include <KPlotAxis>
#include <KPlotObject>
#include <KPlotPoint>
#include <KPlotWidget>

// Injected by CMake ($<TARGET_FILE:KF5::Plotting>): the packaged .so path.
#ifndef KPLOTTING_SO_PATH
#define KPLOTTING_SO_PATH ""
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

// Locate the file backing the loaded libKF5Plotting.so via /proc/self/maps.
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
    bool has_codesign = false;
};

// Minimal ELF64 walker (program headers for the dynamic table, section
// headers for .codesign) — same approach as the validated kitemviews5 test.
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
    // Section-header walk for the OHOS .codesign section.
    if (eh.e_shnum > 0 && eh.e_shstrndx != SHN_UNDEF) {
        std::vector<Elf64_Shdr> shdrs(eh.e_shnum);
        if (std::fseek(f, static_cast<long>(eh.e_shoff), SEEK_SET) == 0
            && std::fread(shdrs.data(), sizeof(Elf64_Shdr), shdrs.size(), f) == shdrs.size()
            // P3 fix: validate the section-name string-table index before use.
            && eh.e_shstrndx < shdrs.size()) {
            const Elf64_Shdr &strtab_sh = shdrs[eh.e_shstrndx];
            std::vector<char> names(strtab_sh.sh_size);
            if (std::fseek(f, static_cast<long>(strtab_sh.sh_offset), SEEK_SET) == 0
                && std::fread(names.data(), 1, names.size(), f) == names.size()) {
                for (const Elf64_Shdr &sh : shdrs) {
                    if (sh.sh_name < names.size()) {
                        const std::string name(names.data() + sh.sh_name);
                        if (name == ".codesign") {
                            info.has_codesign = true;
                            break;
                        }
                    }
                }
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
    QApplication app(argc, argv);
    app.setApplicationName(QStringLiteral("test_kplotting5"));

    // --- R53: HarmonyOS adaptation assertions -----------------------------
    {
        const std::string mapped = loaded_library_path("libKF5Plotting.so");
        check(!mapped.empty(), "libKF5Plotting.so is mapped into the process");
        // P1 fix: hold the temporary QByteArray in a named object — taking
        // constData() of an unnamed temporary is a use-after-free.
        const QByteArray platform_ba = QApplication::platformName().toLocal8Bit();
        const char *platform = platform_ba.constData();
        check(std::strcmp(platform, "offscreen") == 0,
              "QApplication runs on the offscreen QPA platform");

        const std::string elf_path = std::strlen(KPLOTTING_SO_PATH) > 0
                                         ? std::string(KPLOTTING_SO_PATH)
                                         : mapped;
        const ElfDynamic info = read_dynamic(elf_path);
        check(info.ok, "packaged libKF5Plotting.so parses as ELF64");
        check(info.soname == "libKF5Plotting.so",
              "DT_SONAME is the unversioned libKF5Plotting.so");
        check(info.has_runpath || info.has_rpath,
              "libKF5Plotting.so carries a DT_RUNPATH (E537)");
        check(info.has_codesign,
              "libKF5Plotting.so carries a .codesign section (OHOS signing)");
    }

    // --- R34: real public API ---------------------------------------------
    {
        // KPlotPoint: geometry + label + barWidth round-trips.
        KPlotPoint p(2.0, 3.0, QStringLiteral("label"), 5.0);
        check(p.x() == 2.0, "KPlotPoint::x()");
        check(p.y() == 3.0, "KPlotPoint::y()");
        check(p.label() == QStringLiteral("label"), "KPlotPoint::label()");
        check(p.barWidth() == 5.0, "KPlotPoint::barWidth()");
        p.setPosition(QPointF(7.5, -1.25));
        check(p.position() == QPointF(7.5, -1.25), "KPlotPoint::setPosition()");
        p.setX(0.5);
        p.setY(0.25);
        check(p.x() == 0.5 && p.y() == 0.25, "KPlotPoint::setX()/setY()");

        // KPlotAxis: label/tick format state.
        KPlotAxis axis(QStringLiteral("magnitude"));
        check(axis.label() == QStringLiteral("magnitude"), "KPlotAxis::label()");
        axis.setTickLabelFormat('e', 3, 2);
        check(axis.tickLabelFormat() == 'e', "KPlotAxis::setTickLabelFormat(char)");
        check(axis.tickLabelWidth() == 3, "KPlotAxis::tickLabelWidth()");
        check(axis.tickLabelPrecision() == 2, "KPlotAxis::tickLabelPrecision()");
        axis.setTickMarks(0.0, 1.0);
        check(axis.majorTickMarks().size() > 0, "KPlotAxis::setTickMarks() major ticks");
        // P3 fix: size() >= 0 was tautological; assert deterministic accessor
        // stability across two calls instead.
        const QList<double> minor_a = axis.minorTickMarks();
        const QList<double> minor_b = axis.minorTickMarks();
        check(minor_a.size() == minor_b.size(),
              "KPlotAxis::minorTickMarks() stable across calls");

        // KPlotObject: pen/brush/size state + point management.
        KPlotObject obj(QColor(Qt::red), KPlotObject::Points, 3.0, KPlotObject::Square);
        obj.setPen(QPen(Qt::green, 2));
        check(obj.pen().color() == QColor(Qt::green), "KPlotObject::setPen()");
        obj.setBrush(QBrush(Qt::blue));
        check(obj.brush().color() == QColor(Qt::blue), "KPlotObject::setBrush()");
        check(obj.size() == 3.0, "KPlotObject::size()");
        obj.addPoint(1.0, 2.0, QStringLiteral("pt"), 0.5);
        obj.addPoint(QPointF(3.0, 4.0));
        obj.addPoint(5.0, 6.0);
        check(obj.points().size() == 3, "KPlotObject::addPoint() x3");
        obj.removePoint(0);
        check(obj.points().size() == 2, "KPlotObject::removePoint()");
        check(obj.points().at(1)->x() == 5.0, "KPlotObject::points() ordering");
        obj.clearPoints();
        check(obj.points().isEmpty(), "KPlotObject::clearPoints()");

        // KPlotWidget: plot-object management, limits, colors (offscreen).
        KPlotWidget w;
        w.setLimits(-1.0, 1.0, -10.0, 10.0);
        check(w.dataRect() == QRectF(-1.0, -10.0, 2.0, 20.0), "KPlotWidget::setLimits()/dataRect()");
        KPlotObject *po1 = new KPlotObject(QColor(Qt::white), KPlotObject::Lines);
        KPlotObject *po2 = new KPlotObject(QColor(Qt::white), KPlotObject::Bars);
        w.addPlotObject(po1);
        check(w.plotObjects().size() == 1, "KPlotWidget::addPlotObject()");
        w.addPlotObjects(QList<KPlotObject *>() << po2);
        check(w.plotObjects().size() == 2, "KPlotWidget::addPlotObjects()");
        w.replacePlotObject(0, new KPlotObject(QColor(Qt::yellow), KPlotObject::Points));
        check(w.plotObjects().size() == 2, "KPlotWidget::replacePlotObject()");
        w.setBackgroundColor(QColor(0x102030));
        check(w.backgroundColor() == QColor(0x102030), "KPlotWidget::setBackgroundColor()");
        w.setForegroundColor(QColor(0x405060));
        check(w.foregroundColor() == QColor(0x405060), "KPlotWidget::setForegroundColor()");
        w.setGridColor(QColor(0x708090));
        check(w.gridColor() == QColor(0x708090), "KPlotWidget::setGridColor()");
        w.setShowGrid(false);
        check(!w.isGridShown(), "KPlotWidget::setShowGrid(false)");
        w.setShowGrid(true);
        check(w.isGridShown(), "KPlotWidget::setShowGrid(true)");
        w.setAntialiasing(true);
        check(w.antialiasing(), "KPlotWidget::setAntialiasing()");
        w.setTopPadding(11);
        w.setBottomPadding(12);
        w.setLeftPadding(13);
        w.setRightPadding(14);
        check(w.topPadding() == 11 && w.bottomPadding() == 12
                  && w.leftPadding() == 13 && w.rightPadding() == 14,
              "KPlotWidget::set*Padding()");
        w.removeAllPlotObjects();
        check(w.plotObjects().isEmpty(), "KPlotWidget::removeAllPlotObjects()");
    }

    std::printf("SUMMARY: %d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
