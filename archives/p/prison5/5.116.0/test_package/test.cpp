/*
 * test_package for prison5 5.116.0 — consumer-side verification (R34).
 *
 * Drives the real public Prison API:
 *   - Prison::createBarcode factory for every barcode type of this
 *     package's configuration (QRCode / Code39 / Code93 / Code128 / Aztec
 *     are built in; Null returns nullptr by contract),
 *   - setData / toImage round-trips that exercise the QPainter rendering
 *     path of AbstractBarcode and the qrencode backend for QR codes,
 *   - the Null / DataMatrix / PDF417 / EAN13 null-pointer contract of the
 *     optional-backend cut (Dmtx / ZXing disabled),
 *   - data()/byteArrayData() content round-trips.
 *
 * HarmonyOS-specific assertions (R53): the loaded libKF5Prison.so carries
 * the OHOS-required unversioned DT_SONAME and a DT_RUNPATH/DT_RPATH (E537:
 * the installed ELF is linked with its final install RPATH and is never
 * rewritten post-link, so OHOS keeps mmap'ing it PROT_EXEC).
 */
#include <prison/abstractbarcode.h>
#include <prison/prison.h>

#include <QByteArray>
#include <QColor>
#include <QCoreApplication>
#include <QImage>
#include <QSizeF>
#include <QString>

#include <cstdio>
#include <cstring>
#include <elf.h>
#include <memory>
#include <string>
#include <vector>

#ifndef PRISON_SO_PATH
#define PRISON_SO_PATH ""
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

// Locate the file backing the loaded libKF5Prison.so via /proc/self/maps.
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
        // ("addr perms offset dev inode path"); take the whole pathname.
        const char *p = line;
        int field = 0;
        while (field < 5 && *p) {
            while (*p == ' ' || *p == '\t') {
                ++p;
            }
            if (!*p) {
                break;
            }
            while (*p && *p != ' ' && *p != '\t') {
                ++p;
            }
            ++field;
        }
        while (*p == ' ' || *p == '\t') {
            ++p;
        }
        if (*p && *p != '\n') {
            path.assign(p);
            while (!path.empty()
                   && (path.back() == '\n' || path.back() == '\r')) {
                path.pop_back();
            }
            if (path[0] == '/') {
                break;
            }
        }
    }
    std::fclose(maps);
    return path;
}

struct ElfDynamic {
    bool ok = false;
    std::string soname = "(none)";
    bool has_runpath = false;
    bool has_rpath = false;
};

ElfDynamic read_dynamic(const std::string &path)
{
    ElfDynamic result;
    FILE *f = std::fopen(path.c_str(), "rb");
    if (!f) {
        return result;
    }
    unsigned char e_ident[16];
    if (std::fread(e_ident, 1, 16, f) != 16
        || std::memcmp(e_ident, ELFMAG, 4) != 0) {
        std::fclose(f);
        return result;
    }
    bool is64 = e_ident[EI_CLASS] == ELFCLASS64;
    std::vector<unsigned char> header(is64 ? 64 : 52);
    std::rewind(f);
    if (std::fread(header.data(), 1, header.size(), f) != header.size()) {
        std::fclose(f);
        return result;
    }

    std::uint64_t e_shoff = 0;
    std::uint16_t e_shentsize = 0, e_shnum = 0, e_shstrndx = 0;
    if (is64) {
        e_shoff = *reinterpret_cast<const std::uint64_t *>(&header[0x28]);
        e_shentsize = *reinterpret_cast<const std::uint16_t *>(&header[0x3A]);
        e_shnum = *reinterpret_cast<const std::uint16_t *>(&header[0x3C]);
        e_shstrndx = *reinterpret_cast<const std::uint16_t *>(&header[0x3E]);
    } else {
        e_shoff = *reinterpret_cast<const std::uint32_t *>(&header[0x20]);
        e_shentsize = *reinterpret_cast<const std::uint16_t *>(&header[0x2E]);
        e_shnum = *reinterpret_cast<const std::uint16_t *>(&header[0x30]);
        e_shstrndx = *reinterpret_cast<const std::uint16_t *>(&header[0x32]);
    }
    if (!e_shoff || !e_shentsize || !e_shnum) {
        std::fclose(f);
        return result;
    }

    std::vector<unsigned char> shdrs(
        static_cast<std::size_t>(e_shentsize) * e_shnum);
    if (std::fseek(f, static_cast<long>(e_shoff), SEEK_SET) != 0
        || std::fread(shdrs.data(), 1, shdrs.size(), f) != shdrs.size()) {
        std::fclose(f);
        return result;
    }

    auto sh_field = [&](std::size_t idx, std::size_t off, std::size_t len) -> std::uint64_t {
        const unsigned char *base = &shdrs[static_cast<std::size_t>(e_shentsize) * idx + off];
        std::uint64_t v = 0;
        for (std::size_t i = 0; i < len; ++i) {
            v |= static_cast<std::uint64_t>(base[i]) << (8 * i);
        }
        return v;
    };

    std::size_t dyn_idx = static_cast<std::size_t>(-1);
    for (std::size_t i = 0; i < e_shnum; ++i) {
        if (sh_field(i, 0x04, 4) == SHT_DYNAMIC) {  // sh_type
            dyn_idx = i;
            break;
        }
    }
    if (dyn_idx == static_cast<std::size_t>(-1)) {
        std::fclose(f);
        return result;
    }

    std::uint64_t dyn_offset = sh_field(dyn_idx, is64 ? 0x18 : 0x10, is64 ? 8 : 4);
    std::uint64_t dyn_size = sh_field(dyn_idx, is64 ? 0x20 : 0x14, is64 ? 8 : 4);
    // The PT_DYNAMIC-referenced string table comes from the .dynstr section.
    std::size_t str_idx = static_cast<std::size_t>(-1);
    for (std::size_t i = 0; i < e_shnum; ++i) {
        if (sh_field(i, 0x04, 4) == SHT_STRTAB
            && (sh_field(i, 0x0C, is64 ? 8 : 4) != 0 || i != dyn_idx)) {
            // prefer .dynstr: the strtab whose address range covers the
            // soname offsets found in .dynamic
            str_idx = i;
            break;
        }
    }
    std::uint64_t str_offset = 0, str_size = 0;
    if (str_idx != static_cast<std::size_t>(-1)) {
        str_offset = sh_field(str_idx, is64 ? 0x18 : 0x10, is64 ? 8 : 4);
        str_size = sh_field(str_idx, is64 ? 0x20 : 0x14, is64 ? 8 : 4);
    }

    const std::size_t entsize = is64 ? 16 : 8;
    std::vector<unsigned char> dyn(static_cast<std::size_t>(dyn_size));
    if (std::fseek(f, static_cast<long>(dyn_offset), SEEK_SET) != 0
        || std::fread(dyn.data(), 1, dyn.size(), f) != dyn.size()) {
        std::fclose(f);
        return result;
    }
    std::string dynstr;
    if (str_size) {
        dynstr.resize(static_cast<std::size_t>(str_size));
        if (std::fseek(f, static_cast<long>(str_offset), SEEK_SET) != 0
            || std::fread(&dynstr[0], 1, dynstr.size(), f) != dynstr.size()) {
            dynstr.clear();
        }
    }
    std::fclose(f);

    result.ok = true;
    for (std::size_t off = 0; off + entsize <= dyn.size(); off += entsize) {
        std::uint64_t tag = 0, val = 0;
        if (is64) {
            tag = *reinterpret_cast<const std::uint64_t *>(&dyn[off]);
            val = *reinterpret_cast<const std::uint64_t *>(&dyn[off + 8]);
        } else {
            tag = *reinterpret_cast<const std::uint32_t *>(&dyn[off]);
            val = *reinterpret_cast<const std::uint32_t *>(&dyn[off + 4]);
        }
        if (tag == DT_NULL) {
            break;
        }
        if (tag == DT_SONAME && val < dynstr.size()) {
            result.soname = std::string(dynstr.c_str() + val);
        }
        if (tag == DT_RUNPATH) {
            result.has_runpath = true;
        }
        if (tag == DT_RPATH) {
            result.has_rpath = true;
        }
    }
    return result;
}

}  // namespace

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    Q_UNUSED(app);

    const QString payload = QStringLiteral("OpenHarmonyPCDeveloper/prison5");

    // ---- createBarcode: built-in generators --------------------------------
    std::unique_ptr<Prison::AbstractBarcode> qr(
        Prison::createBarcode(Prison::QRCode));
    check(qr != nullptr, "createBarcode(QRCode) returns a generator");

    std::unique_ptr<Prison::AbstractBarcode> c39(
        Prison::createBarcode(Prison::Code39));
    check(c39 != nullptr, "createBarcode(Code39) returns a generator");

    std::unique_ptr<Prison::AbstractBarcode> c93(
        Prison::createBarcode(Prison::Code93));
    check(c93 != nullptr, "createBarcode(Code93) returns a generator");

    std::unique_ptr<Prison::AbstractBarcode> c128(
        Prison::createBarcode(Prison::Code128));
    check(c128 != nullptr, "createBarcode(Code128) returns a generator");

    std::unique_ptr<Prison::AbstractBarcode> aztec(
        Prison::createBarcode(Prison::Aztec));
    check(aztec != nullptr, "createBarcode(Aztec) returns a generator");

    // ---- createBarcode: null-pointer contract -------------------------------
    check(Prison::createBarcode(Prison::Null) == nullptr,
          "createBarcode(Null) returns nullptr");
    check(Prison::createBarcode(Prison::DataMatrix) == nullptr,
          "createBarcode(DataMatrix) is nullptr without Dmtx (optional cut)");
    check(Prison::createBarcode(Prison::PDF417) == nullptr,
          "createBarcode(PDF417) is nullptr without ZXing (optional cut)");
    check(Prison::createBarcode(Prison::EAN13) == nullptr,
          "createBarcode(EAN13) is nullptr without ZXing (optional cut)");

    // ---- setData / data round-trips ------------------------------------------
    if (qr) {
        qr->setData(payload);
        check(qr->data() == payload, "QR generator data() round-trip");
    }
    if (c128) {
        const QByteArray bin("KDE\x0\x1\x2 prison5", 15);
        c128->setData(bin);
        check(c128->byteArrayData() == bin,
              "Code128 generator byteArrayData() round-trip");
    }

    // ---- toImage: QPainter rendering path ------------------------------------
    if (qr) {
        const QImage img = qr->toImage(QSizeF(120, 120));
        check(!img.isNull(), "QR toImage(120x120) is not null");
        check(img.width() > 0 && img.height() > 0,
              "QR toImage has positive dimensions");
        // A QR code of a non-empty payload must paint black AND white
        // pixels (the painter path really ran).
        bool has_black = false, has_white = false;
        for (int y = 0; y < img.height() && !(has_black && has_white); ++y) {
            for (int x = 0; x < img.width() && !(has_black && has_white); ++x) {
                const QRgb px = img.pixel(x, y);
                // The barcode foreground defaults to black.
                if (qRed(px) == 0 && qGreen(px) == 0 && qBlue(px) == 0) {
                    has_black = true;
                } else if (qRed(px) >= 240 && qGreen(px) >= 240
                           && qBlue(px) >= 240) {
                    has_white = true;
                }
            }
        }
        check(has_black && has_white,
              "QR toImage renders both dark and light modules");
    }
    if (aztec) {
        aztec->setData(payload);
        const QImage img = aztec->toImage(aztec->preferredSize(1));
        check(!img.isNull(), "Aztec toImage(preferredSize) is not null");
    }
    if (c39) {
        c39->setData(QStringLiteral("PRISON5"));
        const QImage img = c39->toImage(QSizeF(200, 60));
        check(!img.isNull(), "Code39 toImage(200x60) is not null");
    }
    if (c93) {
        c93->setData(QStringLiteral("PRISON5"));
        const QImage img = c93->toImage(QSizeF(200, 60));
        check(!img.isNull(), "Code93 toImage(200x60) is not null");
    }

    // ---- libKF5Prison.so ELF adaptation (R53) -------------------------------
    // /proc/self/maps reports the kernel-side HMDFS mount path
    // (/data/service/el2/...), which is not openable from inside the
    // sandbox namespace; PRISON_SO_PATH (set by CMakeLists from the
    // imported KF5::Prison target at configure time) carries the
    // consumer-visible packaged path, so prefer it and keep the maps
    // lookup only as a fallback.
    std::string so_path = PRISON_SO_PATH;
    if (so_path.empty()) {
        so_path = loaded_library_path("libKF5Prison.so");
    }
    check(!so_path.empty(), "libKF5Prison.so path resolved");
    if (!so_path.empty()) {
        const ElfDynamic dyn = read_dynamic(so_path);
        check(dyn.ok, "libKF5Prison.so ELF dynamic section parsed");
        check(dyn.soname == "libKF5Prison.so",
              "libKF5Prison.so carries the unversioned DT_SONAME");
        check(dyn.has_runpath || dyn.has_rpath,
              "libKF5Prison.so carries a DT_RUNPATH/DT_RPATH (E537)");
    }

    std::printf("test_prison5: %d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
