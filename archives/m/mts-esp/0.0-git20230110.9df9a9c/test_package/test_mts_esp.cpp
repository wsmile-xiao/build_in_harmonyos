#include <libMTSClient.h>
#include <libMTSMaster.h>

#include <cmath>
#include <cstring>
#include <iostream>
#include <string>

namespace {

bool near(double actual, double expected, double tolerance = 1.0e-6) {
    return std::fabs(actual - expected) <= tolerance;
}

int fail(const char* message) {
    std::cerr << message << '\n';
    return 1;
}

int run(const std::string& name) {
    MTSClient* client = MTS_RegisterClient();
    if (client == nullptr) {
        return fail("MTS_RegisterClient returned null");
    }

    int result = 0;
    if (name == "client_registration") {
        result = MTS_HasMaster(client) ? fail("unexpected master") : 0;
    } else if (name == "default_frequency") {
        result = near(MTS_NoteToFrequency(client, 69, -1), 440.0) &&
                         near(MTS_NoteToFrequency(client, 60, -1),
                              261.6255653005986)
                     ? 0
                     : fail("default 12-TET frequency mismatch");
    } else if (name == "retuning_identity") {
        result = near(MTS_RetuningAsRatio(client, 64, -1), 1.0) &&
                         near(MTS_RetuningInSemitones(client, 64, -1), 0.0)
                     ? 0
                     : fail("default retuning is not identity");
    } else if (name == "frequency_to_note") {
        char channel = -1;
        const bool ok = MTS_FrequencyToNote(client, 440.0, -1) == 69 &&
                        MTS_FrequencyToNote(client, 1.0, -1) == 0 &&
                        MTS_FrequencyToNote(client, 20000.0, -1) == 127 &&
                        MTS_FrequencyToNoteAndChannel(client, 440.0, &channel) == 69 &&
                        channel == 0;
        result = ok ? 0 : fail("frequency-to-note conversion mismatch");
    } else if (name == "default_scale") {
        result = std::strcmp(MTS_GetScaleName(client), "12-TET") == 0
                     ? 0
                     : fail("default scale name mismatch");
    } else if (name == "note_filter") {
        result = !MTS_ShouldFilterNote(client, 60, -1) &&
                         !MTS_ShouldFilterNote(client, 60, 3)
                     ? 0
                     : fail("offline note unexpectedly filtered");
    } else if (name == "sysex_single_note") {
        const unsigned int value = (69u << 21u) | (69u << 14u) | 8192u;
        const unsigned char message[] = {
            0xF0, 0x7F, 0x7F, 0x08, 0x02, 0x00, 0x01,
            static_cast<unsigned char>((value >> 21u) & 0x7Fu),
            static_cast<unsigned char>((value >> 14u) & 0x7Fu),
            static_cast<unsigned char>((value >> 7u) & 0x7Fu),
            static_cast<unsigned char>(value & 0x7Fu), 0xF7};
        MTS_ParseMIDIDataU(client, message, sizeof(message));
        const double tuned = MTS_NoteToFrequency(client, 69, -1);
        result = tuned > 452.8 && tuned < 452.9
                     ? 0
                     : fail("single-note SysEx tuning was not applied");
    } else if (name == "master_offline_safety") {
        double frequencies[128] = {};
        MTS_RegisterMaster();
        MTS_SetNoteTunings(frequencies);
        MTS_SetNoteTuning(432.0, 69);
        MTS_SetScaleName("offline");
        MTS_FilterNote(true, 1, -1);
        MTS_ClearNoteFilter();
        MTS_DeregisterMaster();
        result = MTS_CanRegisterMaster() && !MTS_HasIPC() &&
                         MTS_GetNumClients() == 0
                     ? 0
                     : fail("offline master fallback mismatch");
    } else if (name == "ohos_dynamic_provider") {
        MTS_RegisterMaster();
        MTS_SetNoteTuning(432.0, 69);
        const bool ok = MTS_HasMaster(client) &&
                        near(MTS_NoteToFrequency(client, 69, -1), 432.0) &&
                        std::strcmp(MTS_GetScaleName(client), "OHOS Mock") == 0 &&
                        MTS_GetNumClients() == 1;
        MTS_DeregisterMaster();
        result = ok ? 0 : fail("HarmonyOS SONAME provider discovery failed");
    } else {
        result = fail("unknown test case");
    }

    MTS_DeregisterClient(client);
    return result;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        return fail("one test case argument is required");
    }
    return run(argv[1]);
}
