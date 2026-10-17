/*
Copyright (c) 2026 Nestopia UE OHOS PC adaptation contributors

Headless driver for the Nestopia UE core on HarmonyOS PC.

The upstream Linux frontend (source/fltkui) is an FLTK GUI with an
OpenGL (libepoxy) video renderer and SDL2 audio/joystick input.  FLTK
and a desktop GL stack are not available on HarmonyOS PC, so this
driver reuses the frontend-agnostic manager layer (JGManager /
SettingManager / CheatManager + the JG core binding in jg.cpp) and
drives the emulator core frame-by-frame from the command line:

    nestopia [options] <rom>

Options:
    --version            print version and exit
    --frames <N>         run N frames headless, then exit 0
    --nosound            skip audio subsystem setup
    --nosetup           skip reading user settings (defaults only)

This is the same "clip the un-adapted GUI, keep the core" approach the
far2l / actiona adaptations use for HarmonyOS PC.

Licensed under the same terms as Nestopia UE (GPL-2.0-or-later).
*/
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
#include <vector>

#include "fltkui/jgmanager.h"
#include "fltkui/setmanager.h"
#include "fltkui/chtmanager.h"
#include "fltkui/logdriver.h"
#include "fltkui/version.h"
#include "fltkui/jg/jg.h"

#include "nstheadless.h"

int main(int argc, char *argv[]) {
    // Parse command line arguments
    std::string filename{};
    long frames = 0;
    bool nosound = false;
    bool nosetup = false;

    for (int i = 1; i < argc; ++i) {
        std::string arg{argv[i]};
        if (arg == "-v" || arg == "--version" || arg == "--help") {
            std::cout << "Nestopia UE " << JG_VERSION << " (headless)" << std::endl;
            return 0;
        }
        else if (arg == "--frames" && i + 1 < argc) {
            frames = std::strtol(argv[++i], nullptr, 10);
        }
        else if (arg == "--nosound") {
            nosound = true;
        }
        else if (arg == "--nosetup") {
            nosetup = true;
        }
        else if (!arg.empty() && arg[0] != '-' && filename.empty()) {
            filename = arg;
        }
    }

    if (filename.empty()) {
        std::cout << "Nestopia UE " << JG_VERSION << " (headless)" << std::endl;
        std::cout << "Usage: " << NSTHEADLESS_NAME << " [--frames N] [--nosound] <rom>" << std::endl;
        return 0;
    }

    // Bring up the frontend-agnostic manager layer
    JGManager jgm{};
    SettingManager setmgr{jgm};

    if (!nosetup) {
        setmgr.read(jgm);
    }

    // Read the ROM (plain files only; archive support lives in the
    // FLTK frontend which is not part of this headless build)
    std::ifstream stream(filename, std::ios::in | std::ios::binary);
    if (!stream.is_open()) {
        std::cerr << "Failed to open file: " << filename << std::endl;
        return 1;
    }
    std::vector<uint8_t> game{std::istreambuf_iterator<char>(stream),
                              std::istreambuf_iterator<char>()};
    stream.close();

    if (game.empty()) {
        std::cerr << "Empty file: " << filename << std::endl;
        return 1;
    }

    jgm.load_game(filename.c_str(), game);

    if (!jgm.is_loaded()) {
        std::cerr << "Failed to load game: " << filename << std::endl;
        return 1;
    }

    // Set up video (the pixel buffer is owned by this driver and handed
    // to the core via the JG vidinfo struct)
    jg_videoinfo_t *vidinfo = jg_get_videoinfo();
    static std::vector<uint32_t> videobuf(
        static_cast<size_t>(vidinfo->hmax) * vidinfo->wmax, 0);
    vidinfo->buf = videobuf.data();

    jgm.setup_video();

    if (!nosound) {
        // Audio needs a sample buffer plus a silent audio callback
        jg_audioinfo_t *audinfo = jgm.get_audioinfo();
        static std::vector<int16_t> audiobuf(
            static_cast<size_t>(audinfo->spf) * audinfo->channels, 0);
        audinfo->buf = audiobuf.data();

        jgm.set_audio_cb([](size_t frames) {
            (void)frames; // headless: swallow generated samples
        });

        jgm.setup_audio();
    }

    // Run the requested number of frames (0 = just load and verify)
    jgm.reset(1);

    for (long i = 0; i < frames; ++i) {
        jgm.exec_frame();
    }

    if (frames > 0) {
        std::cout << "Executed " << frames << " frames of "
                  << jgm.get_gamename() << std::endl;
    }
    else {
        std::cout << "Loaded " << jgm.get_gamename()
                  << " (" << game.size() << " bytes)" << std::endl;
    }

    return 0;
}
