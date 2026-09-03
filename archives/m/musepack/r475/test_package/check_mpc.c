/* check_mpc.c — library-level verification of the packaged musepack.
 * Opens an SV8 .mpc file through the real public API (mpc_reader_init_stdio
 * -> mpc_demux_init -> mpc_demux_get_info -> mpc_demux_decode), validates
 * the stream information and decodes a few frames. Links libmpcdec. */
#include <stdio.h>
#include <stdlib.h>

#include <mpc/mpcdec.h>
#include <mpc/reader.h>
#include <mpc/streaminfo.h>

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s <file.mpc>\n", argv[0]);
        return 2;
    }
    mpc_reader reader;
    if (MPC_STATUS_FAIL == mpc_reader_init_stdio(&reader, argv[1])) {
        fprintf(stderr, "FAIL: cannot open %s\n", argv[1]);
        return 1;
    }
    mpc_demux *demux = mpc_demux_init(&reader);
    if (!demux) {
        fprintf(stderr, "FAIL: mpc_demux_init\n");
        return 1;
    }
    mpc_streaminfo si;
    mpc_demux_get_info(demux, &si);
    printf("stream: SV%u %u Hz %u ch %llu samples\n", si.stream_version,
           si.sample_freq, si.channels, (unsigned long long)si.samples);
    if (si.stream_version != 8) {
        fprintf(stderr, "FAIL: expected SV8 stream, got SV%u\n",
                si.stream_version);
        return 1;
    }
    if (si.sample_freq != 44100 || si.channels != 2 || si.samples == 0) {
        fprintf(stderr, "FAIL: unexpected streaminfo (%u Hz, %u ch, %llu samples)\n",
                si.sample_freq, si.channels, (unsigned long long)si.samples);
        return 1;
    }

    static MPC_SAMPLE_FORMAT sample_buffer[MPC_DECODER_BUFFER_LENGTH];
    int decoded = 0;
    for (int i = 0; i < 4; i++) {
        mpc_frame_info frame = {0};
        frame.buffer = sample_buffer;
        mpc_status st = mpc_demux_decode(demux, &frame);
        if (MPC_STATUS_FAIL == st)
            break;
        if (frame.bits == -1)
            break; /* end of stream */
        if (frame.samples == 0) {
            fprintf(stderr, "FAIL: empty decoded frame\n");
            return 1;
        }
        decoded++;
    }
    if (decoded == 0) {
        fprintf(stderr, "FAIL: no frames decoded\n");
        return 1;
    }
    mpc_demux_exit(demux);
    mpc_reader_exit_stdio(&reader);
    printf("check_mpc OK: SV8 streaminfo valid, %d frames decoded via libmpcdec\n",
           decoded);
    return 0;
}
