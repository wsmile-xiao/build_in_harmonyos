#include <fluidsynth.h>

#include <stdio.h>

#ifndef FLUIDSYNTH_MISSING_SF2
#error "FLUIDSYNTH_MISSING_SF2 must be defined"
#endif

int main(void)
{
    fluid_settings_t *settings = new_fluid_settings();
    if (settings == NULL) {
        fputs("new_fluid_settings failed\n", stderr);
        return 1;
    }

    fluid_synth_t *synth = new_fluid_synth(settings);
    if (synth == NULL) {
        delete_fluid_settings(settings);
        fputs("new_fluid_synth failed\n", stderr);
        return 1;
    }

    if (fluid_synth_sfcount(synth) != 0) {
        delete_fluid_synth(synth);
        delete_fluid_settings(settings);
        fputs("new synth unexpectedly contains a SoundFont\n", stderr);
        return 1;
    }
    if (fluid_synth_sfload(synth, FLUIDSYNTH_MISSING_SF2, 0) != FLUID_FAILED) {
        delete_fluid_synth(synth);
        delete_fluid_settings(settings);
        fputs("missing SoundFont did not fail deterministically\n", stderr);
        return 1;
    }
    if (fluid_synth_sfcount(synth) != 0) {
        delete_fluid_synth(synth);
        delete_fluid_settings(settings);
        fputs("failed SoundFont load changed synth inventory\n", stderr);
        return 1;
    }

    delete_fluid_synth(synth);
    delete_fluid_settings(settings);
    return 0;
}
