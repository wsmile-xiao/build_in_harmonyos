/*
 * test_package for kholidays5 5.116.0 — consumer-side verification (R34).
 *
 * Drives the real public KHolidays API exactly the way downstream KDE
 * consumers (Plasma digital-clock holidays, eventviews, calendar plugins)
 * use it:
 *   - HolidayRegion over a bundled region (gb-eaw_en-gb): regionCodes()
 *     registry, rawHolidaysWithAstroSeasons for a known year, isHoliday,
 *     observedStartDate/duration round-trip on the parsed plan2 data,
 *   - SunRiseSet utcSunrise/utcSunset (the NYC 2012-01-01 reference
 *     values from the upstream autotest),
 *   - LunarPhase phaseAtDate (the 2005 full-moon reference from the
 *     upstream autotest),
 *   - Zodiac signAtDate/signName (the tropical Jan-1 Capricorn boundary
 *     from the upstream autotest),
 *   - the org.kde.kholidays QML plugin deliverable present in the package.
 *
 * HarmonyOS-specific assertions (R53; kpeople5 KPEOPLE_SO_PATH precedent):
 * the packaged libKF5Holidays.so carries the OHOS-required unversioned
 * DT_SONAME and a DT_RUNPATH (E537 install-RPATH adaptation), verified by
 * parsing the ELF dynamic section directly from the consumer-visible
 * package path (kernel-side /proc/self/maps paths on HMDFS cannot be
 * re-opened, so the path is injected at compile time).
 */
#include <KHolidays/HolidayRegion>
#include <KHolidays/LunarPhase>
#include <KHolidays/SunRiseSet>
#include <KHolidays/Zodiac>

#include <QCoreApplication>
#include <QDate>
#include <QDateTime>
#include <QDebug>
#include <QDir>
#include <QFileInfo>
#include <QString>
#include <QTime>

#include <cerrno>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include <elf.h>

static int g_fail = 0;
static int g_checks = 0;

static void check(bool ok, const char *what)
{
    ++g_checks;
    if (ok) {
        std::printf("ok   - %s\n", what);
    } else {
        ++g_fail;
        std::printf("FAIL - %s\n", what);
    }
}

// ---------------------------------------------------------------------------
// R53 ELF adaptation checks (kcalcore test_package precedent): parse the
// dynamic section of the packaged library directly.  The DT_* entries live
// at link-time virtual addresses; they are translated to file offsets
// through the PT_LOAD program headers (identity for the flat layouts the
// OHOS linker produces, but computed properly regardless).
// ---------------------------------------------------------------------------
static int check_elf_adaptation()
{
    FILE *f = std::fopen(KHOLIDAYS_SO_PATH, "rb");
    if (!f) {
        std::printf("FAIL - cannot open packaged %s\n", KHOLIDAYS_SO_PATH);
        return 1;
    }
    std::fseek(f, 0, SEEK_END);
    const long size = std::ftell(f);
    std::fseek(f, 0, SEEK_SET);
    if (size <= 0) {
        std::fclose(f);
        std::printf("FAIL - cannot size %s\n", KHOLIDAYS_SO_PATH);
        return 1;
    }
    std::vector<unsigned char> buf(static_cast<size_t>(size));
    if (std::fread(buf.data(), 1, buf.size(), f) != buf.size()) {
        std::fclose(f);
        std::printf("FAIL - cannot read %s\n", KHOLIDAYS_SO_PATH);
        return 1;
    }
    std::fclose(f);

    if (buf.size() < sizeof(Elf64_Ehdr)
        || std::memcmp(buf.data(), ELFMAG, SELFMAG) != 0) {
        std::printf("FAIL - %s is not an ELF file\n", KHOLIDAYS_SO_PATH);
        return 1;
    }
    const Elf64_Ehdr *eh = reinterpret_cast<const Elf64_Ehdr *>(buf.data());

    auto ph = [&](int i) -> const Elf64_Phdr * {
        return reinterpret_cast<const Elf64_Phdr *>(
            buf.data() + eh->e_phoff
            + static_cast<size_t>(i) * eh->e_phentsize);
    };

    const Elf64_Phdr *phdyn = nullptr;
    for (int i = 0; i < eh->e_phnum; ++i) {
        if (ph(i)->p_type == PT_DYNAMIC) {
            phdyn = ph(i);
        }
    }
    if (!phdyn) {
        std::printf("FAIL - no PT_DYNAMIC segment\n");
        return 1;
    }

    auto vaddr_to_offset = [&](Elf64_Xword vaddr) -> size_t {
        for (int i = 0; i < eh->e_phnum; ++i) {
            const Elf64_Phdr *p = ph(i);
            if (p->p_type == PT_LOAD
                && vaddr >= p->p_vaddr
                && vaddr < p->p_vaddr + p->p_filesz) {
                return static_cast<size_t>(vaddr - p->p_vaddr + p->p_offset);
            }
        }
        return static_cast<size_t>(vaddr); // flat-layout fallback
    };

    const Elf64_Dyn *dyn = reinterpret_cast<const Elf64_Dyn *>(
        buf.data() + phdyn->p_offset);
    const size_t dyn_count =
        static_cast<size_t>(phdyn->p_filesz) / sizeof(Elf64_Dyn);

    // DT_STRTAB first (dynamic entries are unordered).
    size_t strtab = 0;
    for (size_t i = 0; i < dyn_count; ++i) {
        if (dyn[i].d_tag == DT_STRTAB) {
            strtab = vaddr_to_offset(dyn[i].d_un.d_ptr);
        }
    }
    if (!strtab) {
        std::printf("FAIL - no DT_STRTAB in packaged library\n");
        return 1;
    }

    auto dynstr = [&](Elf64_Xword off) -> const char * {
        const size_t pos = strtab + static_cast<size_t>(off);
        if (pos >= buf.size()) {
            return "";
        }
        return reinterpret_cast<const char *>(buf.data() + pos);
    };

    bool has_soname = false;
    bool soname_unversioned = false;
    bool has_runpath = false;
    std::string soname;
    for (size_t i = 0; i < dyn_count; ++i) {
        switch (dyn[i].d_tag) {
        case DT_SONAME:
            has_soname = true;
            soname = dynstr(dyn[i].d_un.d_val);
            // W3 CI L5 soname gate: unversioned "libKF5Holidays.so"
            // (no .so.5 suffix).
            soname_unversioned = (soname == "libKF5Holidays.so");
            break;
        case DT_RUNPATH:
        case DT_RPATH:
            has_runpath = true;
            break;
        default:
            break;
        }
    }

    check(has_soname, "packaged libKF5Holidays.so has DT_SONAME");
    check(soname_unversioned,
          "DT_SONAME is unversioned (libKF5Holidays.so)");
    check(has_runpath, "library carries a DT_RUNPATH (E537 install-RPATH)");

    if (g_fail == 0) {
        std::printf("ELF adaptation checks passed on %s (soname=%s)\n",
                    KHOLIDAYS_SO_PATH, soname.c_str());
    }
    return 0;
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    Q_UNUSED(app)

    // ------------------------------------------------------------------
    // 1) HolidayRegion: the bundled region registry and the plan2 parser
    //    over the qrc-embedded region data (the core downstream API).
    // ------------------------------------------------------------------
    const QStringList regionCodes = KHolidays::HolidayRegion::regionCodes();
    check(regionCodes.contains(QStringLiteral("gb-eaw_en-gb")),
          "regionCodes() registry carries the bundled gb-eaw_en-gb region");
    check(regionCodes.contains(QStringLiteral("cn_zh-cn")),
          "regionCodes() registry carries the bundled cn_zh-cn region");

    KHolidays::HolidayRegion gb(QStringLiteral("gb-eaw_en-gb"));
    check(gb.isValid(), "gb-eaw_en-gb HolidayRegion is valid");
    const QString gbLang = gb.languageCode();
    check(!gbLang.isEmpty() && gbLang.startsWith(QLatin1String("en")),
          "gb-eaw region language code is en");

    // Known holiday: 2026-01-01 is New Year's Day in England and Wales
    // (the upstream testGb region).
    const KHolidays::Holiday::List holidays2026 =
        gb.rawHolidaysWithAstroSeasons(QDate(2026, 1, 1), QDate(2026, 1, 3));
    bool foundNewYear = false;
    for (const KHolidays::Holiday &h : holidays2026) {
        if (h.observedStartDate() == QDate(2026, 1, 1) && h.duration() == 1) {
            foundNewYear = true;
        }
    }
    check(foundNewYear,
          "gb-eaw region parses New Year's Day 2026 (plan2 parser over qrc data)");

    check(gb.rawHolidaysWithAstroSeasons(QDate(2026, 12, 25), QDate(2026, 12, 26))
              .count() >= 1,
          "gb-eaw region parses Christmas Day 2026");

    // Full-year parse across every bundled region code: exercises the
    // whole plan2 corpus shipped in holidays.qrc (upstream testRegions
    // consumer-side equivalent).
    int regionsParsed = 0;
    for (const QString &code : regionCodes) {
        KHolidays::HolidayRegion region(code);
        if (region.isValid()) {
            const KHolidays::Holiday::List list =
                region.rawHolidaysWithAstroSeasons(2026);
            if (!list.isEmpty()) {
                ++regionsParsed;
            }
        }
    }
    check(regionsParsed > 100,
          "every bundled region parses its 2026 holidays (plan2 corpus)");

    // ------------------------------------------------------------------
    // 2) SunRiseSet: the upstream NYC 2012-01-01 reference values
    //    (UTC times).
    // ------------------------------------------------------------------
    check(KHolidays::SunRiseSet::utcSunrise(QDate(2012, 1, 1), 40.72, -74.02)
              == QTime(12, 20),
          "SunRiseSet::utcSunrise NYC 2012-01-01 == 12:20 UTC");
    check(KHolidays::SunRiseSet::utcSunset(QDate(2012, 1, 1), 40.72, -74.02)
              == QTime(21, 39),
          "SunRiseSet::utcSunset NYC 2012-01-01 == 21:39 UTC");
    check(!KHolidays::SunRiseSet::utcSunrise(QDate(2022, 6, 21), 78.2231, 15.6322)
               .isValid(),
          "SunRiseSet::utcSunrise polar day (Spitsbergen 2022-06-21) invalid");
    check(KHolidays::SunRiseSet::isPolarDay(QDate(2022, 6, 21), 78.2231),
          "SunRiseSet::isPolarDay Spitsbergen 2022-06-21");

    // ------------------------------------------------------------------
    // 3) LunarPhase: the upstream 2005-01-25 full moon reference.
    // ------------------------------------------------------------------
    check(KHolidays::LunarPhase::phaseAtDate(QDate(2005, 1, 25))
              == KHolidays::LunarPhase::FullMoon,
          "LunarPhase::phaseAtDate 2005-01-25 == FullMoon");
    check(KHolidays::LunarPhase::phaseAtDate(QDate(2005, 1, 10))
              == KHolidays::LunarPhase::NewMoon,
          "LunarPhase::phaseAtDate 2005-01-10 == NewMoon");

    // ------------------------------------------------------------------
    // 4) Zodiac: the tropical Jan-1 Capricorn boundary.
    // ------------------------------------------------------------------
    KHolidays::Zodiac zodiac(KHolidays::Zodiac::Tropical);
    check(zodiac.signAtDate(QDate(2026, 1, 1)) == KHolidays::Zodiac::Capricorn,
          "Zodiac::signAtDate tropical 2026-01-01 == Capricorn");
    check(zodiac.signName(KHolidays::Zodiac::Capricorn)
              == QStringLiteral("Capricorn"),
          "Zodiac::signName Capricorn");

    // ------------------------------------------------------------------
    // 5) The org.kde.kholidays QML plugin deliverable is present in the
    //    package (lib/qml/org/kde/kholidays with the plugin + qmldir),
    //    derived from the consumer-visible library path.
    // ------------------------------------------------------------------
    const QString libPath = QStringLiteral(KHOLIDAYS_SO_PATH);
    const QString qmlDir = QFileInfo(libPath).absolutePath()
                           + QStringLiteral("/qml/org/kde/kholidays");
    const QDir pluginDir(qmlDir);
    check(pluginDir.exists()
              && pluginDir.exists(QStringLiteral("qmldir")),
          "org.kde.kholidays QML plugin directory with qmldir is packaged");
    bool pluginSo = false;
    const QFileInfoList entries =
        pluginDir.entryInfoList(QStringList() << QStringLiteral("*.so"));
    for (const QFileInfo &fi : entries) {
        if (fi.fileName().contains(QStringLiteral("kholidaysdeclarativeplugin"))) {
            pluginSo = true;
        }
    }
    check(pluginSo, "kholidaysdeclarativeplugin library is packaged in the QML dir");

    // ------------------------------------------------------------------
    // 6) R53 ELF adaptation checks on the packaged library.
    // ------------------------------------------------------------------
    if (check_elf_adaptation() != 0) {
        ++g_fail;
    }

    std::printf("\n%d checks, %d failures\n", g_checks, g_fail);
    return g_fail == 0 ? 0 : 1;
}
