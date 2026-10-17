#include <fluidsynth.h>

#include <cmath>
#include <cstdio>

namespace {

int fail(const char *message)
{
    std::fprintf(stderr, "%s\n", message);
    return 1;
}

bool ok(int result)
{
    return result == FLUID_OK;
}

} // namespace

int main()
{
    fluid_settings_t *settings = new_fluid_settings();
    if (settings == nullptr) {
        return fail("new_fluid_settings failed");
    }

    int major = 0;
    int minor = 0;
    int micro = 0;
    fluid_version(&major, &minor, &micro);
    if (major != 2 || minor != 5 || micro != 7) {
        delete_fluid_settings(settings);
        return fail("header and library versions do not match 2.5.7");
    }

    if (!ok(fluid_settings_setnum(settings, "synth.sample-rate", 48000.0))) {
        delete_fluid_settings(settings);
        return fail("setting synth.sample-rate failed");
    }
    double sample_rate = 0.0;
    if (!ok(fluid_settings_getnum(settings, "synth.sample-rate", &sample_rate)) ||
        std::fabs(sample_rate - 48000.0) > 0.001) {
        delete_fluid_settings(settings);
        return fail("synth.sample-rate did not round-trip");
    }

    fluid_synth_t *synth = new_fluid_synth(settings);
    if (synth == nullptr) {
        delete_fluid_settings(settings);
        return fail("new_fluid_synth failed");
    }

    fluid_synth_set_gain(synth, 0.35f);
    if (std::fabs(fluid_synth_get_gain(synth) - 0.35f) > 0.0001f) {
        delete_fluid_synth(synth);
        delete_fluid_settings(settings);
        return fail("synth gain did not round-trip");
    }

    if (!ok(fluid_synth_set_interp_method(synth, -1, FLUID_INTERP_4THORDER)) ||
        !ok(fluid_synth_program_change(synth, 0, 0)) ||
        !ok(fluid_synth_cc(synth, 0, 7, 100)) ||
        !ok(fluid_synth_pitch_bend(synth, 0, 8192)) ||
        !ok(fluid_synth_channel_pressure(synth, 0, 32)) ||
        !ok(fluid_synth_key_pressure(synth, 0, 60, 48))) {
        delete_fluid_synth(synth);
        delete_fluid_settings(settings);
        return fail("MIDI event sequence failed");
    }
    if (fluid_synth_sfcount(synth) != 0 ||
        fluid_synth_noteon(synth, 0, 60, 90) != FLUID_FAILED) {
        delete_fluid_synth(synth);
        delete_fluid_settings(settings);
        return fail("empty synth accepted a note without a preset");
    }

    float samples[128] = {};
    if (!ok(fluid_synth_write_float(synth, 64, samples, 0, 2,
                                    samples, 1, 2))) {
        delete_fluid_synth(synth);
        delete_fluid_settings(settings);
        return fail("fluid_synth_write_float failed");
    }
    for (float sample : samples) {
        if (!std::isfinite(sample)) {
            delete_fluid_synth(synth);
            delete_fluid_settings(settings);
            return fail("renderer produced a non-finite sample");
        }
    }

    fluid_synth_noteoff(synth, 0, 60);
    delete_fluid_synth(synth);
    delete_fluid_settings(settings);
    return 0;
}
