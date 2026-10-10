#include <SndObj/HarmTable.h>
#include <SndObj/Oscili.h>

#include <cmath>
#include <iostream>

int main() {
    HarmTable table(1024, 1, SINE);
    if (table.GetLen() != 1024 || !std::isfinite(table.Lookup(1))) return 1;

    Oscili oscillator(&table, 440.0f, 1.0f, nullptr, nullptr, 256, 44100.0f);
    if (oscillator.DoProcess() != 1) return 2;

    bool nonzero = false;
    for (int i = 0; i < 256; ++i) {
        const float sample = oscillator.Output(i);
        if (!std::isfinite(sample)) return 3;
        nonzero = nonzero || std::fabs(sample) > 0.01f;
    }
    if (!nonzero) return 4;
    std::cout << "SNDOBJ_CONSUMER_3_OF_3_PASS\n";
    return 0;
}
