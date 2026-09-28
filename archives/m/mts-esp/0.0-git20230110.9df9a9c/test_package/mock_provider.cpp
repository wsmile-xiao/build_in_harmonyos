#include <cmath>
#include <cstring>

namespace {

bool has_master = false;
int clients = 0;
double tuning[128];
const char* scale_name = "OHOS Mock";

struct Initializer {
    Initializer() {
        for (int note = 0; note < 128; ++note) {
            tuning[note] = 440.0 * std::pow(2.0, (note - 69.0) / 12.0);
        }
    }
} initializer;

}  // namespace

extern "C" {

void MTS_RegisterClient() { ++clients; }
void MTS_DeregisterClient() { --clients; }
bool MTS_HasMaster() { return has_master; }
int MTS_GetVersionNumber() { return 0x00010003; }
bool MTS_ShouldFilterNote(char, char) { return false; }
bool MTS_ShouldFilterNoteMultiChannel(char, char) { return false; }
const double* MTS_GetTuningTable() { return tuning; }
const double* MTS_GetMultiChannelTuningTable(char) { return nullptr; }
bool MTS_UseMultiChannelTuning(char) { return false; }
const char* MTS_GetScaleName() { return scale_name; }
void MTS_RegisterMaster(void*) { has_master = true; }
void MTS_DeregisterMaster() { has_master = false; }
bool MTS_HasIPC() { return false; }
void MTS_Reinitialize() { has_master = false; }
int MTS_GetNumClients() { return clients; }
void MTS_SetNoteTunings(const double* frequencies) {
    std::memcpy(tuning, frequencies, sizeof(tuning));
}
void MTS_SetNoteTuning(double frequency, char note) {
    tuning[static_cast<unsigned char>(note) & 127u] = frequency;
}
void MTS_SetScaleName(const char* name) { scale_name = name; }
void MTS_FilterNote(bool, char, char) {}
void MTS_ClearNoteFilter() {}
void MTS_SetMultiChannel(bool, char) {}
void MTS_SetMultiChannelNoteTunings(const double*, char) {}
void MTS_SetMultiChannelNoteTuning(double, char, char) {}
void MTS_FilterNoteMultiChannel(bool, char, char) {}
void MTS_ClearNoteFilterMultiChannel(char) {}

}
