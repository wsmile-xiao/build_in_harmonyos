// Consumer test for kf5wayland 5.116.0 (R34: exercise the package API,
// not print a string).
//
// OHOS has no Wayland compositor, so no connection is attempted: the test
// constructs real protocol objects from both libraries and calls the
// server compositor factory. All of these run package code without socket
// I/O - client protocol classes are passive until setup/binding (see the
// KWayland::Client::Compositor docs), and the server Display constructor
// only calls wl_display_create() (createListener is never reached).
// Include paths follow the package's real Qt6 install layout
// (KDE_INSTALL_INCLUDEDIR_KF = include/KF6): client headers land at
// include/KF6/KWayland/KWayland/Client and are included as
// <KWayland/Client/...> (the target include dir include/KF6/KWayland absorbs
// the doubled path component); server headers land at
// include/KF6/KWayland/Server and are included as <KWayland/Server/...>
// (the server headers include one another that way, resolved by the server
// target's include dir include/KF6; note compositor_interface.h, not
// compositor.h); version header at include/KF6/KWayland.
#include <KWayland/Client/compositor.h>
#include <KWayland/Client/surface.h>
#include <KWayland/Server/compositor_interface.h>
#include <KWayland/Server/display.h>
#include <kwayland_version.h>

#include <cstdio>
#include <cstdint>
#include <cstring>
#include <vector>

// OHOS platform assertion (5th): the packaged client library must carry a
// non-empty .codesign ELF section. The recipe signs the packaged .so files
// (binary-sign-tool self-sign, the same mechanism the qtbase/wayland
// registry packages use); this check proves the packaged artifact went
// through that step. Parsing the section table is pure file I/O - no
// runtime linking, no compositor, safe offline.
static bool has_codesign_section(const char *path)
{
    FILE *f = std::fopen(path, "rb");
    if (!f) {
        return false;
    }
    unsigned char ident[16];
    if (std::fread(ident, 1, 16, f) != 16 || ident[0] != 0x7f || ident[1] != 'E'
        || ident[2] != 'L' || ident[3] != 'F' || ident[4] != 2) {
        std::fclose(f);
        return false; // not a 64-bit ELF
    }
    uint64_t shoff = 0;
    uint16_t shentsize = 0, shnum = 0, shstrndx = 0;
    std::fseek(f, 0x28, SEEK_SET);
    std::fread(&shoff, 8, 1, f);
    // ELF64 header field offsets: e_shoff=0x28, e_shentsize=0x3A,
    // e_shnum=0x3C, e_shstrndx=0x3E (0x36/0x38 are the program-header
    // e_phentsize/e_phnum and must not be read here).
    std::fseek(f, 0x3A, SEEK_SET);
    std::fread(&shentsize, 2, 1, f);
    std::fseek(f, 0x3C, SEEK_SET);
    std::fread(&shnum, 2, 1, f);
    std::fseek(f, 0x3E, SEEK_SET);
    std::fread(&shstrndx, 2, 1, f);
    if (!shoff || !shnum || shstrndx >= shnum || shentsize < 64) {
        std::fclose(f);
        return false;
    }
    std::vector<unsigned char> table(static_cast<size_t>(shnum) * shentsize);
    std::fseek(f, static_cast<long>(shoff), SEEK_SET);
    if (std::fread(table.data(), 1, table.size(), f) != table.size()) {
        std::fclose(f);
        return false;
    }
    const unsigned char *strtab_hdr =
        table.data() + static_cast<size_t>(shstrndx) * shentsize;
    uint64_t strtab_off = 0, strtab_size = 0;
    std::memcpy(&strtab_off, strtab_hdr + 24, 8);
    std::memcpy(&strtab_size, strtab_hdr + 32, 8);
    std::vector<unsigned char> strtab(strtab_size);
    std::fseek(f, static_cast<long>(strtab_off), SEEK_SET);
    if (std::fread(strtab.data(), 1, strtab_size, f) != strtab_size) {
        std::fclose(f);
        return false;
    }
    bool found = false;
    uint64_t section_size = 0;
    for (uint16_t i = 0; i < shnum; ++i) {
        const unsigned char *hdr =
            table.data() + static_cast<size_t>(i) * shentsize;
        uint32_t name_off = 0;
        std::memcpy(&name_off, hdr, 4);
        if (name_off < strtab_size
            && std::strcmp(
                   reinterpret_cast<const char *>(strtab.data()) + name_off,
                   ".codesign") == 0) {
            found = true;
            std::memcpy(&section_size, hdr + 32, 8);
            break;
        }
    }
    std::fclose(f);
    return found && section_size > 0;
}

int main()
{
    // Client side (libKF5WaylandClient): protocol classes.
    KWayland::Client::Compositor clientCompositor;
    KWayland::Client::Surface clientSurface;
    if (!clientCompositor.metaObject() || !clientSurface.metaObject()) {
        std::fprintf(stderr, "client protocol classes lack a meta object\n");
        return 1;
    }

    // Server side (libKF5WaylandServer): in-tree display object plus the
    // compositor interface factory.
    KWayland::Server::Display serverDisplay;
    if (!serverDisplay.metaObject()) {
        std::fprintf(stderr, "server Display lacks a meta object\n");
        return 1;
    }
    KWayland::Server::CompositorInterface *serverCompositor =
        serverDisplay.createCompositor();
    if (!serverCompositor) {
        std::fprintf(stderr, "createCompositor() returned null\n");
        return 1;
    }

    // OHOS platform assertion (5th): the packaged client library must be
    // code-signed (.codesign section present and non-empty).
    if (!has_codesign_section(KF5_CLIENT_LIB_PATH)) {
        std::fprintf(
            stderr,
            "%s lacks a non-empty .codesign section: the OHOS code "
            "signature was not applied to the packaged library\n",
            KF5_CLIENT_LIB_PATH);
        return 1;
    }

    std::printf(
        "kf5wayland %s: KF5WaylandClient + KF5WaylandServer protocol "
        "objects constructed; .codesign platform assertion passed\n",
        KWAYLAND_VERSION_STRING); // ECM 6.x ecm_setup_version emits *_VERSION_STRING
    return 0;
}
