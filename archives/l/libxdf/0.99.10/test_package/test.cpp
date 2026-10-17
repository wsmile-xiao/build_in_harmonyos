// Consumer test for libxdf (test_package).
//
// Builds a minimal but valid XDF file from scratch, loads it through the public
// libxdf API (Xdf::load_xdf) and asserts the parsed metadata and sample values.
// Negative cases assert the documented return codes (1 = cannot open, -1 = bad magic).

#include <xdf.h>

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <string>

namespace {

int failures = 0;

void check(bool cond, const std::string &what) {
    if (!cond) {
        std::printf("FAIL: %s\n", what.c_str());
        ++failures;
    } else {
        std::printf("ok  : %s\n", what.c_str());
    }
}

void check_close(double got, double want, const std::string &what) {
    check(std::fabs(got - want) < 1e-9, what);
}

std::string bytes_of(const void *p, size_t n) {
    return std::string(reinterpret_cast<const char *>(p), n);
}

// XDF chunk length encoding: one byte telling how many bytes carry the length,
// then the length itself, little-endian.
void write_length(std::ofstream &f, uint64_t v) {
    if (v < 256) {
        const uint8_t nbytes = 1;
        const uint8_t val = static_cast<uint8_t>(v);
        f.write(bytes_of(&nbytes, 1).data(), 1);
        f.write(bytes_of(&val, 1).data(), 1);
    } else {
        const uint8_t nbytes = 8;
        f.write(bytes_of(&nbytes, 1).data(), 1);
        f.write(bytes_of(&v, 8).data(), 8);
    }
}

// tag + payload, where payload already contains the stream id where applicable.
void write_chunk(std::ofstream &f, uint16_t tag, uint32_t stream_id, const std::string &payload) {
    write_length(f, static_cast<uint64_t>(payload.size()) + 6);  // 2 tag + 4 stream id
    f.write(bytes_of(&tag, sizeof(tag)).data(), sizeof(tag));
    f.write(bytes_of(&stream_id, sizeof(stream_id)).data(), sizeof(stream_id));
    f.write(payload.data(), static_cast<std::streamsize>(payload.size()));
}

// FileHeader / other chunks that carry no stream id.
void write_plain_chunk(std::ofstream &f, uint16_t tag, const std::string &payload) {
    write_length(f, static_cast<uint64_t>(payload.size()) + 2);  // + tag
    f.write(bytes_of(&tag, sizeof(tag)).data(), sizeof(tag));
    f.write(payload.data(), static_cast<std::streamsize>(payload.size()));
}

// One stream, two float32 channels, three samples with explicit timestamps.
void write_sample_xdf(const std::string &path) {
    const uint32_t stream_id = 1;
    const char *stream_xml =
        "<info><name>TestStream</name><type>EEG</type>"
        "<channel_count>2</channel_count><nominal_srate>100</nominal_srate>"
        "<channel_format>float32</channel_format>"
        "<desc><channels><channel><label>ch1</label></channel>"
        "<channel><label>ch2</label></channel></channels></desc></info>";

    std::ofstream f(path, std::ios::binary | std::ios::trunc);
    f.write("XDF:", 4);
    write_plain_chunk(f, 1, "<info><version>1.0</version></info>");
    write_chunk(f, 2, stream_id, stream_xml);

    // [Samples]: sample count (variable length), then tsBytes + timestamp + 2 floats per sample.
    const uint8_t nbytes = 1;
    const uint8_t sample_count = 3;
    std::string payload(1, static_cast<char>(nbytes));
    payload.push_back(static_cast<char>(sample_count));
    const double stamps[3] = {0.0, 0.01, 0.02};
    const float values[3][2] = {{1.0f, 4.0f}, {2.0f, 5.0f}, {3.0f, 6.0f}};
    for (int i = 0; i < 3; ++i) {
        const uint8_t ts_bytes = 8;
        payload += bytes_of(&ts_bytes, 1);
        payload += bytes_of(&stamps[i], sizeof(double));
        for (int c = 0; c < 2; ++c)
            payload += bytes_of(&values[i][c], sizeof(float));
    }
    write_chunk(f, 3, stream_id, payload);

    write_chunk(f, 6, stream_id,
                "<info><first_timestamp>0.0</first_timestamp>"
                "<last_timestamp>0.02</last_timestamp>"
                "<sample_count>3</sample_count></info>");
    write_length(f, 0);  // end-of-file marker
    f.close();
}

}  // namespace

int main() {
    // 1. Data path: build an XDF file and parse it through the public API.
    const std::string good = "consumer_test.xdf";
    write_sample_xdf(good);

    Xdf doc;
    const int rc = doc.load_xdf(good);
    check(rc == 0, "load_xdf returns 0 for a valid XDF file");
    check(doc.streams.size() == 1, "one stream parsed");

    if (!doc.streams.empty()) {
        const Xdf::Stream &s = doc.streams.front();
        check(s.info.name == "TestStream", "stream name parsed from header XML");
        check(s.info.type == "EEG", "stream type parsed from header XML");
        check(s.info.channel_format == "float32", "channel_format parsed");
        check(s.info.channel_count == 2, "channel_count == 2");
        check_close(s.info.nominal_srate, 100.0, "nominal_srate == 100");
        check(s.info.channels.size() == 2, "two channel descriptors parsed");
        if (s.info.channels.size() == 2) {
            const auto label0 = s.info.channels[0].find("label");
            const auto label1 = s.info.channels[1].find("label");
            check(label0 != s.info.channels[0].end() && label0->second == "ch1",
                  "channel 0 label");
            check(label1 != s.info.channels[1].end() && label1->second == "ch2",
                  "channel 1 label");
        }
        check(s.time_stamps.size() == 3, "three timestamps parsed");
        check(s.time_series.size() == 2, "time_series has one row per channel");
        bool values_ok = s.time_series.size() == 2 && s.time_series[0].size() == 3;
        if (values_ok) {
            const float expect[2][3] = {{1.0f, 2.0f, 3.0f}, {4.0f, 5.0f, 6.0f}};
            for (int c = 0; c < 2 && values_ok; ++c)
                for (int i = 0; i < 3 && values_ok; ++i)
                    values_ok = std::fabs(s.time_series[c][i] - expect[c][i]) < 1e-6;
        }
        check(values_ok, "sample values survive the round trip");
        if (s.time_stamps.size() == 3) {
            check_close(s.time_stamps[0], 0.0, "timestamp 0");
            check_close(s.time_stamps[2], 0.02, "timestamp 2");
        }
    }

    // 2. Missing file -> documented "cannot open" return code 1.
    Xdf missing;
    check(missing.load_xdf("does_not_exist.xdf") == 1, "missing file returns 1");

    // 3. Wrong magic -> documented "not a valid XDF file" return code -1.
    {
        std::ofstream bad("consumer_test_bad.xdf", std::ios::binary | std::ios::trunc);
        bad.write("NOPE:deadbeef", 13);
        bad.close();
        Xdf invalid;
        check(invalid.load_xdf("consumer_test_bad.xdf") == -1, "bad magic returns -1");
        std::remove("consumer_test_bad.xdf");
    }

    std::remove(good.c_str());

    if (failures == 0) {
        std::printf("libxdf consumer test: all checks passed\n");
        return 0;
    }
    std::printf("libxdf consumer test: %d check(s) FAILED\n", failures);
    return 1;
}
