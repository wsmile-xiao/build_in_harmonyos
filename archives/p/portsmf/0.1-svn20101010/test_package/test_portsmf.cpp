#include <cmath>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>

#include <allegro.h>

namespace {

bool close_to(double actual, double expected, double tolerance = 1e-6)
{
    return std::fabs(actual - expected) <= tolerance;
}

int fail(const char *message)
{
    std::cerr << message << '\n';
    return 1;
}

Alg_seq *make_sequence()
{
    Alg_seq *sequence = new Alg_seq;
    Alg_note *note = sequence->create_note(0.6, 0, 60, 60.0f, 100.0f, 0.3);
    sequence->add_event(note, 0);
    return sequence;
}

int sequence_construction()
{
    Alg_seq sequence;
    return sequence.tracks() == 1 && sequence.track(0)->length() == 0
               ? 0
               : fail("default sequence layout is invalid");
}

int note_insertion()
{
    Alg_seq *sequence = make_sequence();
    const bool ok = sequence->track(0)->length() == 1 &&
                    (*sequence->track(0))[0]->is_note();
    delete sequence;
    return ok ? 0 : fail("note insertion failed");
}

int unit_conversion()
{
    Alg_seq *sequence = make_sequence();
    sequence->convert_to_beats();
    const bool ok = !sequence->get_units_are_seconds() &&
                    close_to((*sequence->track(0))[0]->time, 1.0);
    delete sequence;
    return ok ? 0 : fail("seconds-to-beats conversion failed");
}

int tempo_map()
{
    Alg_seq sequence;
    sequence.convert_to_beats();
    const bool changed = sequence.insert_tempo(120.0, 0.0);
    return changed && close_to(sequence.get_tempo(0.0), 2.0)
               ? 0
               : fail("tempo map update failed");
}

int time_signature()
{
    Alg_seq sequence;
    sequence.convert_to_beats();
    sequence.set_time_sig(0.0, 3.0, 4.0);
    long measure = -1;
    double beat = -1.0;
    double numerator = 0.0;
    double denominator = 0.0;
    sequence.beat_to_measure(
        4.0, &measure, &beat, &numerator, &denominator);
    return measure == 1 && close_to(beat, 1.0) &&
                   close_to(numerator, 3.0) && close_to(denominator, 4.0)
               ? 0
               : fail("time-signature conversion failed");
}

int serialization()
{
    Alg_seq *sequence = make_sequence();
    void *buffer = nullptr;
    long bytes = 0;
    sequence->serialize(&buffer, &bytes);
    Alg_track *decoded = Alg_track::unserialize(buffer, bytes);
    std::free(buffer);
    const bool ok = bytes > 0 && decoded != nullptr &&
                    decoded->to_alg_seq() != nullptr &&
                    decoded->to_alg_seq()->track(0)->length() == 1;
    delete decoded;
    delete sequence;
    return ok ? 0 : fail("binary serialization round trip failed");
}

int midi_round_trip(const char *path)
{
    Alg_seq *sequence = make_sequence();
    const bool wrote = sequence->smf_write(path);
    delete sequence;
    if (!wrote) {
        return fail("SMF write failed");
    }
    Alg_seq decoded(path, true);
    const bool ok = decoded.get_read_error() == alg_no_error &&
                    decoded.tracks() >= 1 && decoded.track(0)->length() >= 1;
    std::remove(path);
    return ok ? 0 : fail("SMF read round trip failed");
}

int ohos_aarch64_abi()
{
    static_assert(sizeof(void *) == 8, "HarmonyOS PC requires a 64-bit ABI");
    static_assert(
        __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__,
        "HarmonyOS PC AArch64 is little-endian");

    Alg_seq *sequence = make_sequence();
    void *buffer = nullptr;
    long bytes = 0;
    sequence->serialize(&buffer, &bytes);
    const bool aligned = buffer != nullptr && bytes > 0 &&
                         (reinterpret_cast<std::size_t>(buffer) % 8U) == 0U;
    std::free(buffer);
    delete sequence;
    if (!aligned) {
        return fail("AArch64 serialization buffer alignment failed");
    }
    return midi_round_trip("portsmf_ohos_aarch64.mid");
}

} // namespace

int main(int argc, char **argv)
{
    if (argc != 2) {
        return fail("usage: test_portsmf <1..8>");
    }
    switch (std::atoi(argv[1])) {
    case 1: return sequence_construction();
    case 2: return note_insertion();
    case 3: return unit_conversion();
    case 4: return tempo_map();
    case 5: return time_signature();
    case 6: return serialization();
    case 7: return midi_round_trip("portsmf_round_trip.mid");
    case 8: return ohos_aarch64_abi();
    default: return fail("invalid consumer test number");
    }
}
