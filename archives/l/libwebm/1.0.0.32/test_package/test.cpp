// Consumer test for libwebm 1.0.0.32 on HarmonyOS PC.
//
// Programmatically muxes a small WebM file (no checked-in binary fixtures),
// parses it back with both the mkvparser and webm_parser APIs, and exercises
// error paths (empty/truncated/garbage input).

#include <webm/mkvmuxer/mkvmuxer.h>
#include <webm/mkvmuxer/mkvwriter.h>
#include <webm/mkvparser/mkvparser.h>
#include <webm/mkvparser/mkvreader.h>
#include <webm/buffer_reader.h>
#include <webm/callback.h>
#include <webm/dom_types.h>
#include <webm/file_reader.h>
#include <webm/status.h>
#include <webm/webm_parser.h>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

namespace {

int failures = 0;

void Require(bool condition, const char* message) {
  if (!condition) {
    std::cerr << "FAIL: " << message << std::endl;
    ++failures;
  }
}

std::vector<std::uint8_t> FramePayload(int seed) {
  return {static_cast<std::uint8_t>(0x10 | (seed & 0x7f)),
          0x00, 0x00, 0x01, 0x2a, 0x43, 0x0f, 0x00};
}

std::string MuxWebMFile() {
  const std::string path = "libwebm-consumer-test.webm";
  std::remove(path.c_str());

  mkvmuxer::MkvWriter writer;
  Require(writer.Open(path.c_str()), "MkvWriter::Open failed");

  mkvmuxer::Segment segment;
  Require(segment.Init(&writer), "Segment::Init failed");
  segment.set_mode(mkvmuxer::Segment::kFile);

  const std::uint64_t video_track = segment.AddVideoTrack(320, 240, 0);
  Require(video_track == 1, "AddVideoTrack did not allocate track 1");

  mkvmuxer::Track* const track = segment.GetTrackByNumber(video_track);
  Require(track != nullptr, "GetTrackByNumber returned null");
  track->set_codec_id("V_VP8");

  // Three frames spanning two clusters exercise SimpleBlock + timestamps.
  for (int i = 0; i < 3; ++i) {
    const std::vector<std::uint8_t> payload = FramePayload(i);
    Require(
        segment.AddFrame(payload.data(), payload.size(), video_track,
                         static_cast<std::uint64_t>(i), i == 0),
        "AddFrame failed");
  }
  Require(segment.Finalize(), "Segment::Finalize failed");
  writer.Close();
  return path;
}

void TestMkvParser(const std::string& path) {
  mkvparser::MkvReader reader;
  Require(reader.Open(path.c_str()) == 0, "MkvReader::Open failed");

  long long pos = 0;
  mkvparser::EBMLHeader ebml_header;
  const long long parse_result = ebml_header.Parse(&reader, pos);
  Require(parse_result >= 0, "EBMLHeader::Parse failed");
  Require(ebml_header.m_docType != nullptr &&
              std::strcmp(ebml_header.m_docType, "webm") == 0,
          "doc type is not webm");

  mkvparser::Segment* raw_segment = nullptr;
  const long long create_result =
      mkvparser::Segment::CreateInstance(&reader, pos, raw_segment);
  Require(create_result == 0 && raw_segment != nullptr,
          "Segment::CreateInstance failed");
  std::unique_ptr<mkvparser::Segment> segment(raw_segment);
  Require(segment->Load() >= 0, "Segment::Load failed");

  const mkvparser::Tracks* const tracks = segment->GetTracks();
  Require(tracks != nullptr && tracks->GetTracksCount() == 1,
          "expected exactly one track");

  const mkvparser::Track* const track = tracks->GetTrackByNumber(1);
  Require(track != nullptr, "track 1 missing after parse");
  Require(track->GetType() == mkvparser::Track::kVideo,
          "track is not video");
  Require(track->GetCodecId() != nullptr &&
              std::strcmp(track->GetCodecId(), "V_VP8") == 0,
          "codec id mismatch after parse");

  const mkvparser::Cluster* cluster = segment->GetFirst();
  Require(cluster != nullptr, "GetFirst returned no cluster");
  Require(cluster->GetTimeCode() == 0, "first cluster timecode is not 0");

  const mkvparser::BlockEntry* entry = nullptr;
  long status = cluster->GetFirst(entry);
  int frame_count = 0;
  while (status >= 0 && entry != nullptr && !entry->EOS()) {
    const mkvparser::Block* const block = entry->GetBlock();
    if (block != nullptr) {
      Require(block->GetTrackNumber() == 1, "wrong track number in block");
      ++frame_count;
    }
    status = cluster->GetNext(entry, entry);
  }
  Require(frame_count == 3, "expected 3 muxed frames in first cluster");
}

// webm_parser (new API) callbacks recording everything the parser reports.
class RecordingCallback : public webm::Callback {
 public:
  webm::Status OnElementBegin(const webm::ElementMetadata&,
                              webm::Action* action) override {
    ++element_count_;
    *action = webm::Action::kRead;
    return webm::Status(webm::Status::kOkCompleted);
  }

  webm::Status OnTrackEntry(const webm::ElementMetadata&,
                            const webm::TrackEntry& entry) override {
    ++track_entries_;
    if (entry.track_type.is_present()) {
      last_track_type_ = static_cast<int>(entry.track_type.value());
    }
    return webm::Status(webm::Status::kOkCompleted);
  }

  webm::Status OnClusterBegin(const webm::ElementMetadata&,
                              const webm::Cluster& cluster,
                              webm::Action* action) override {
    ++clusters_;
    if (cluster.timecode.is_present()) {
      last_cluster_timecode_ =
          static_cast<std::int64_t>(cluster.timecode.value());
    }
    *action = webm::Action::kRead;
    return webm::Status(webm::Status::kOkCompleted);
  }

  webm::Status OnSimpleBlockBegin(const webm::ElementMetadata&,
                                  const webm::SimpleBlock& block,
                                  webm::Action* action) override {
    ++blocks_;
    last_block_timecode_ = block.timecode;
    *action = webm::Action::kRead;
    return webm::Status(webm::Status::kOkCompleted);
  }

  int element_count_ = 0;
  int track_entries_ = 0;
  int blocks_ = 0;
  int clusters_ = 0;
  int last_track_type_ = -1;
  std::int16_t last_block_timecode_ = -1;
  std::int64_t last_cluster_timecode_ = -1;
};

void TestWebMParser(const std::string& path) {
  std::FILE* const file = std::fopen(path.c_str(), "rb");
  Require(file != nullptr, "fopen of muxed file failed");
  webm::FileReader reader(file);
  webm::WebmParser parser;
  RecordingCallback callback;

  webm::Status status = parser.Feed(&callback, &reader);
  Require(status.completed_ok(), "webm::WebmParser did not complete OK");
  Require(callback.track_entries_ == 1,
          "webm_parser expected 1 track entry");
  Require(callback.last_track_type_ == 1 /* kVideo */,
          "webm_parser track type is not video");
  Require(callback.clusters_ >= 1, "webm_parser saw no cluster");
  Require(callback.last_cluster_timecode_ == 0,
          "webm_parser cluster timecode mismatch");
  Require(callback.blocks_ == 3, "webm_parser expected 3 simple blocks");
}

void TestErrorInputs() {
  // Empty input is a valid empty document: the parser immediately hits EOF
  // without consuming bytes and completes OK (documented Feed() semantics in
  // webm_parser.h / webm_parser.cc). It must not crash and must report zero
  // content.
  {
    webm::BufferReader reader{std::vector<std::uint8_t>{}};
    webm::WebmParser parser;
    RecordingCallback callback;
    const webm::Status status = parser.Feed(&callback, &reader);
    Require(status.completed_ok(),
            "empty input did not complete as an empty document");
    Require(callback.track_entries_ == 0 && callback.blocks_ == 0,
            "empty input unexpectedly reported content");
  }
  // Truncated/garbage input must be reported as a parsing error, never crash.
  {
    const std::vector<std::uint8_t> garbage = {0x1a, 0x45, 0xdf, 0xa3,
                                               0xff, 0x00, 0x77, 0x01};
    webm::BufferReader reader{garbage};
    webm::WebmParser parser;
    RecordingCallback callback;
    const webm::Status status = parser.Feed(&callback, &reader);
    Require(!status.completed_ok(),
            "garbage input unexpectedly parsed to completion");
    Require(status.is_parsing_error(),
            "garbage input was not flagged as a parsing error");
  }
  // A truncated but valid-prefix stream (EBML header only, size promises
  // more bytes than exist) must fail, not complete.
  {
    const std::vector<std::uint8_t> truncated = {
        0x1a, 0x45, 0xdf, 0xa3, 0x00, 0x00, 0x00, 0x20, 0x42, 0x86};
    webm::BufferReader reader{truncated};
    webm::WebmParser parser;
    RecordingCallback callback;
    const webm::Status status = parser.Feed(&callback, &reader);
    Require(!status.completed_ok(),
            "truncated header unexpectedly parsed to completion");
  }
  // mkvparser on an empty file.
  {
    const std::string empty_path = "libwebm-consumer-empty.webm";
    std::FILE* const f = std::fopen(empty_path.c_str(), "wb");
    if (f != nullptr) {
      std::fclose(f);
      mkvparser::MkvReader reader;
      Require(reader.Open(empty_path.c_str()) == 0,
              "open of empty file failed");
      long long pos = 0;
      mkvparser::EBMLHeader header;
      Require(header.Parse(&reader, pos) < 0,
              "empty file unexpectedly passed EBML header parse");
    }
  }
}

}  // namespace

int main() {
  const std::string path = MuxWebMFile();
  TestMkvParser(path);
  TestWebMParser(path);
  TestErrorInputs();
  if (failures != 0) {
    std::cerr << failures << " consumer checks failed" << std::endl;
    return 1;
  }
  std::cout << "libwebm consumer test passed" << std::endl;
  return 0;
}
