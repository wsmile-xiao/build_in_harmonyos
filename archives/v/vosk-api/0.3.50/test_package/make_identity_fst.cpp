/*
 * Test-only fixture generator (links OpenFst, not libvosk).
 *
 * Writes a byte-level identity transducer: one state, one self-loop per byte
 * label (ilabel == olabel) and the state is final. Feeding it to
 * vosk_text_processor_new() as both the tagger and the verbalizer makes the
 * vosk ITN pipeline a no-op, so vosk_text_processor_itn() must return its
 * input unchanged — a deterministic, model-free functional check of the
 * library's FST path.
 *
 * usage: make_identity_fst <out.fst>
 */
#include <fst/fstlib.h>

#include <cstdio>

using fst::ArcSort;
using fst::ILabelCompare;
using fst::StdArc;
using fst::StdVectorFst;
using fst::TropicalWeight;

int main(int argc, char **argv)
{
    if (argc < 2) {
        std::fprintf(stderr, "usage: %s <out.fst>\n", argv[0]);
        return 2;
    }
    StdVectorFst fst;
    fst.AddState();
    fst.SetStart(0);
    /* label 0 is epsilon, so start at byte 1 */
    for (int b = 1; b < 256; ++b) {
        fst.AddArc(0, StdArc(b, b, TropicalWeight::One(), 0));
    }
    fst.SetFinal(0, TropicalWeight::One());
    ArcSort(&fst, ILabelCompare<StdArc>());
    fst.Write(argv[1]);
    std::printf("wrote identity transducer: %s\n", argv[1]);
    return 0;
}
