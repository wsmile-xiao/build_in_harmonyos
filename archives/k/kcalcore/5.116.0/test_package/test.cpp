/*
 * test_package for kcalcore 5.116.0 — consumer-side verification (R34).
 *
 * Drives the real public KCalendarCore API exactly the way downstream KDE
 * PIM consumers (eventviews et al.) use it:
 *   - MemoryCalendar in a named timezone + Event/Todo management
 *     (addEvent/rawEvents/dates/duration),
 *   - ICalFormat::toString / fromRawString round-trip through the
 *     libical-backed parser inside the packaged libKF5CalendarCore.so,
 *   - vCalendar export through VCalFormat (the libical vcal/vobject API).
 *
 * HarmonyOS-specific assertions (R53; kpeople5 KPEOPLE_SO_PATH precedent):
 * the packaged libKF5CalendarCore.so carries the OHOS-required unversioned
 * DT_SONAME and a DT_RUNPATH (E537 install-RPATH adaptation), verified by
 * parsing the ELF dynamic section directly from the consumer-visible
 * package path (kernel-side /proc/self/maps paths on HMDFS cannot be
 * re-opened, so the path is injected at compile time).
 */
#include <KCalendarCore/MemoryCalendar>
#include <KCalendarCore/Event>
#include <KCalendarCore/Todo>
#include <KCalendarCore/ICalFormat>
#include <KCalendarCore/VCalFormat>

#include <QDebug>
#include <QTimeZone>

#include <cstdio>
#include <cstring>
#include <elf.h>
#include <string>
#include <vector>

#ifndef KCALCORE_SO_PATH
#define KCALCORE_SO_PATH ""
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

} // namespace

// ---------------------------------------------------------------------------
// R53: parse the ELF dynamic section of the packaged library (consumer-view
// path injected at compile time) and assert the OHOS adaptation properties.
// Dynamic entries carry link-time virtual addresses; they are translated to
// file offsets through the PT_LOAD program headers (identity for the flat
// layouts the OHOS linker produces, but computed properly regardless).
// ---------------------------------------------------------------------------
static int check_elf_adaptation()
{
    FILE *f = std::fopen(KCALCORE_SO_PATH, "rb");
    if (!f) {
        std::printf("FAIL - cannot open packaged %s\n", KCALCORE_SO_PATH);
        return 1;
    }
    std::fseek(f, 0, SEEK_END);
    const long size = std::ftell(f);
    std::fseek(f, 0, SEEK_SET);
    if (size <= 0) {
        std::fclose(f);
        std::printf("FAIL - cannot size %s\n", KCALCORE_SO_PATH);
        return 1;
    }
    std::vector<unsigned char> buf(static_cast<size_t>(size));
    if (std::fread(buf.data(), 1, buf.size(), f) != buf.size()) {
        std::fclose(f);
        std::printf("FAIL - cannot read %s\n", KCALCORE_SO_PATH);
        return 1;
    }
    std::fclose(f);

    if (buf.size() < sizeof(Elf64_Ehdr)
        || std::memcmp(buf.data(), ELFMAG, SELFMAG) != 0) {
        std::printf("FAIL - %s is not an ELF file\n", KCALCORE_SO_PATH);
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
            // W3 CI L5 soname gate: unversioned "libKF5CalendarCore.so"
            // (no .so.5 suffix).
            soname_unversioned = (soname == "libKF5CalendarCore.so");
            break;
        case DT_RUNPATH:
        case DT_RPATH:
            has_runpath = true;
            break;
        default:
            break;
        }
    }

    check(has_soname, "packaged libKF5CalendarCore.so has DT_SONAME");
    check(soname_unversioned,
          "DT_SONAME is unversioned (libKF5CalendarCore.so)");
    check(has_runpath, "library carries a DT_RUNPATH (E537 install-RPATH)");

    if (g_fail == 0) {
        std::printf("ELF adaptation checks passed on %s (soname=%s)\n",
                    KCALCORE_SO_PATH, soname.c_str());
    }
    return g_fail == 0 ? 0 : 1;
}

int main(int argc, char **argv)
{
    Q_UNUSED(argc);
    Q_UNUSED(argv);

    // ------------------------------------------------------------------
    // 1) MemoryCalendar + Event management (the core downstream API).
    // ------------------------------------------------------------------
    KCalendarCore::MemoryCalendar::Ptr calendar(
        new KCalendarCore::MemoryCalendar(QTimeZone::utc()));
    check(calendar->timeZone() == QTimeZone::utc(),
          "MemoryCalendar constructed in UTC timezone");

    KCalendarCore::Event::Ptr event(new KCalendarCore::Event);
    event->setSummary(QStringLiteral("HarmonyOS PC kcalcore consumer test"));
    event->setDtStart(QDateTime(QDate(2026, 10, 4), QTime(9, 0, 0), QTimeZone::utc()));
    event->setDtEnd(QDateTime(QDate(2026, 10, 4), QTime(10, 0, 0), QTimeZone::utc()));
    check(calendar->addEvent(event), "addEvent accepted the event");

    const KCalendarCore::Event::List events = calendar->rawEvents();
    check(events.count() == 1 && events.first() == event,
          "rawEvents returns the added event");

    // ------------------------------------------------------------------
    // 2) ICalFormat round-trip: serialise + parse back through the
    //    libical-backed parser inside the packaged library.
    // ------------------------------------------------------------------
    KCalendarCore::ICalFormat format;
    const QString ics = format.toString(calendar);
    check(ics.contains(QStringLiteral("BEGIN:VCALENDAR"))
              && ics.contains(QStringLiteral("HarmonyOS PC kcalcore consumer test")),
          "ICalFormat::toString produced VCALENDAR with the event summary");

    KCalendarCore::MemoryCalendar::Ptr parsed(
        new KCalendarCore::MemoryCalendar(QTimeZone::utc()));
    // CalFormat::fromRawString takes the raw bytes (QByteArray).
    check(format.fromRawString(parsed, ics.toUtf8()),
          "ICalFormat::fromRawString parsed the serialized calendar");
    check(parsed->rawEvents().count() == 1,
          "parsed calendar carries exactly one event");
    if (parsed->rawEvents().count() == 1) {
        check(parsed->rawEvents().first()->summary()
                  == QStringLiteral("HarmonyOS PC kcalcore consumer test"),
              "parsed event summary round-trips");
        check(parsed->rawEvents().first()->dtStart()
                  == QDateTime(QDate(2026, 10, 4), QTime(9, 0, 0), QTimeZone::utc()),
              "parsed event start time round-trips");
    }

    // ------------------------------------------------------------------
    // 3) Todo API sanity (duration handling).
    // ------------------------------------------------------------------
    KCalendarCore::Todo::Ptr todo(new KCalendarCore::Todo);
    todo->setSummary(QStringLiteral("verify KCalendarCore::Todo"));
    todo->setDtStart(QDateTime(QDate(2026, 10, 4), QTime(9, 0, 0), QTimeZone::utc()));
    todo->setDuration(KCalendarCore::Duration(3600, KCalendarCore::Duration::Seconds));
    check(todo->duration().asSeconds() == 3600,
          "Todo duration round-trip (3600 seconds)");

    // ------------------------------------------------------------------
    // 4) VCalFormat: the vCalendar 1.0 import path (the vobject/vcc parser
    //    from libical) also lives in this library.  Note upstream's
    //    toString() for VCalFormat is an unimplemented stub ("Exporting
    //    into VCAL is not supported", returns an empty string), so the
    //    consumer-side check exercises the read direction instead - the
    //    way downstream apps import legacy Outlook vCal files.
    // ------------------------------------------------------------------
    KCalendarCore::VCalFormat vformat;
    const QByteArray vcal =
        "BEGIN:VCALENDAR\r\n"
        "VERSION:1.0\r\n"
        "BEGIN:VEVENT\r\n"
        "DCREATED:19960328T080000Z\r\n"
        "UID:19960401T130000Z-12345@example.com\r\n"
        "DTSTART:19960401T130000Z\r\n"
        "DTEND:19960401T140000Z\r\n"
        "SUMMARY:vCalendar import consumer test\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n";
    KCalendarCore::MemoryCalendar::Ptr vcalCal(
        new KCalendarCore::MemoryCalendar(QTimeZone::utc()));
    check(vformat.fromRawString(vcalCal, vcal),
          "VCalFormat::fromRawString parsed the vCalendar 1.0 text");
    check(vcalCal->rawEvents().count() == 1,
          "vCalendar calendar carries exactly one event");
    if (vcalCal->rawEvents().count() == 1) {
        check(vcalCal->rawEvents().first()->summary()
                  == QStringLiteral("vCalendar import consumer test"),
              "vCalendar event summary round-trips");
    }

    // ------------------------------------------------------------------
    // 5) R53: OHOS ELF adaptation properties of the packaged library.
    // ------------------------------------------------------------------
    const int elf_rc = check_elf_adaptation();

    std::printf("\n%d passed, %d failed\n", g_pass, g_fail);
    return (g_fail == 0 && elf_rc == 0) ? 0 : 1;
}
