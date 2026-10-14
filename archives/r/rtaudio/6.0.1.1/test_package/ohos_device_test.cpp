// HarmonyOS device suite for RtAudio's public API and OHAudio backend.
#include <rtaudio/RtAudio.h>
#include <rtaudio/rtaudio_c.h>
#include <ohaudio/native_audiorenderer.h>
#include <ohaudio/native_audiostreambuilder.h>

#include <atomic>
#include <chrono>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace {

const double kPi = 3.14159265358979323846;
const unsigned int kSampleRate = 48000;
const unsigned int kChannels = 2;
const unsigned int kBufferFrames = 480;

struct DirectProgress {
  std::atomic<unsigned long long> callbacks;
  std::atomic<unsigned long long> bytes;
  std::atomic<unsigned long long> magnitude;
  DirectProgress() : callbacks(0), bytes(0), magnitude(0) {}
};

struct DirectProbeStatus {
  int create;
  int configure;
  int generate;
  int start;
  int stop;
  int release;
  DirectProbeStatus() : create(-1), configure(-1), generate(-1), start(-1),
                        stop(-1), release(-1) {}
};

struct Progress {
  std::atomic<unsigned long long> callbacks;
  std::atomic<unsigned long long> outputCallbacks;
  std::atomic<unsigned long long> inputCallbacks;
  std::atomic<unsigned long long> frames;
  std::atomic<unsigned long long> inputFrames;
  std::atomic<unsigned long long> inputMagnitude;
  std::atomic<unsigned long long> outputMagnitude;
  unsigned int outputChannels;
  unsigned int inputChannels;
  bool nonInterleaved;
  bool sawWave;
  unsigned long long stopAfterFrames;
  int callbackReturn;

  Progress(unsigned int outChannels = kChannels, unsigned int inChannels = 1,
           bool planar = false, bool saw = false)
    : callbacks(0), outputCallbacks(0), inputCallbacks(0), frames(0), inputFrames(0),
      inputMagnitude(0), outputMagnitude(0), outputChannels(outChannels),
      inputChannels(inChannels), nonInterleaved(planar), sawWave(saw),
      stopAfterFrames(0), callbackReturn(0) {}
};

OH_AudioData_Callback_Result onDirectOhaudioWrite(
  OH_AudioRenderer *, void *userData, void *audioData, int32_t audioDataSize)
{
  DirectProgress *progress = static_cast<DirectProgress *>(userData);
  if (!progress || !audioData || audioDataSize <= 0)
    return AUDIO_DATA_CALLBACK_RESULT_INVALID;
  int16_t *samples = static_cast<int16_t *>(audioData);
  const unsigned int count = static_cast<unsigned int>(audioDataSize) / sizeof(int16_t);
  const unsigned long long first = progress->bytes.load() / sizeof(int16_t);
  unsigned long long magnitude = 0;
  for (unsigned int i = 0; i < count; ++i) {
    const double phase = 2.0 * kPi * 440.0 * static_cast<double>(first + i) / kSampleRate;
    samples[i] = static_cast<int16_t>(12000.0 * std::sin(phase));
    magnitude += static_cast<unsigned long long>(std::abs(static_cast<int>(samples[i])));
  }
  progress->callbacks.fetch_add(1);
  progress->bytes.fetch_add(static_cast<unsigned long long>(audioDataSize));
  progress->magnitude.fetch_add(magnitude);
  return AUDIO_DATA_CALLBACK_RESULT_VALID;
}

bool waitForCallbacks(const DirectProgress &progress, unsigned long long target,
                      unsigned int timeoutMs = 4000)
{
  const auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(timeoutMs);
  while (std::chrono::steady_clock::now() < deadline) {
    if (progress.callbacks.load() >= target) return true;
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
  }
  return progress.callbacks.load() >= target;
}

void runDirectOhaudioProbe(DirectProgress &progress, DirectProbeStatus &status)
{
  OH_AudioStreamBuilder *builder = 0;
  OH_AudioRenderer *renderer = 0;
  OH_AudioStream_Result result = OH_AudioStreamBuilder_Create(&builder, AUDIOSTREAM_TYPE_RENDERER);
  status.create = result;
  if (result == AUDIOSTREAM_SUCCESS)
    result = OH_AudioStreamBuilder_SetSamplingRate(builder, kSampleRate);
  if (result == AUDIOSTREAM_SUCCESS)
    result = OH_AudioStreamBuilder_SetChannelCount(builder, kChannels);
  if (result == AUDIOSTREAM_SUCCESS)
    result = OH_AudioStreamBuilder_SetSampleFormat(builder, AUDIOSTREAM_SAMPLE_S16LE);
  if (result == AUDIOSTREAM_SUCCESS)
    result = OH_AudioStreamBuilder_SetEncodingType(builder, AUDIOSTREAM_ENCODING_TYPE_RAW);
  if (result == AUDIOSTREAM_SUCCESS)
    result = OH_AudioStreamBuilder_SetFrameSizeInCallback(builder, kBufferFrames);
  if (result == AUDIOSTREAM_SUCCESS)
    result = OH_AudioStreamBuilder_SetRendererInfo(builder, AUDIOSTREAM_USAGE_MUSIC);
  if (result == AUDIOSTREAM_SUCCESS)
    result = OH_AudioStreamBuilder_SetRendererWriteDataCallback(builder, onDirectOhaudioWrite, &progress);
  status.configure = result;
  if (result == AUDIOSTREAM_SUCCESS)
    result = OH_AudioStreamBuilder_GenerateRenderer(builder, &renderer);
  status.generate = result;
  if (result == AUDIOSTREAM_SUCCESS)
    result = OH_AudioRenderer_Start(renderer);
  status.start = result;
  if (result == AUDIOSTREAM_SUCCESS) {
    waitForCallbacks(progress, 10);
    status.stop = OH_AudioRenderer_Stop(renderer);
  }
  if (renderer) status.release = OH_AudioRenderer_Release(renderer);
  if (builder) OH_AudioStreamBuilder_Destroy(builder);
}

int onAudio(void *output, void *input, unsigned int frameCount,
            double, RtAudioStreamStatus, void *userData)
{
  Progress *progress = static_cast<Progress *>(userData);
  if (!progress) return 2;
  progress->callbacks.fetch_add(1);
  const unsigned long long totalFrames = progress->frames.fetch_add(frameCount) + frameCount;

  if (output) {
    progress->outputCallbacks.fetch_add(1);
    int16_t *samples = static_cast<int16_t *>(output);
    unsigned long long magnitude = 0;
    for (unsigned int channel = 0; channel < progress->outputChannels; ++channel) {
      for (unsigned int frame = 0; frame < frameCount; ++frame) {
        const unsigned long long sampleIndex = progress->nonInterleaved
          ? static_cast<unsigned long long>(channel) * frameCount + frame
          : static_cast<unsigned long long>(frame) * progress->outputChannels + channel;
        const double value = progress->sawWave
          ? 12000.0 * (2.0 * std::fmod(static_cast<double>(frame + channel * 37), 200.0) / 200.0 - 1.0)
          : 12000.0 * std::sin(2.0 * kPi * 440.0 * static_cast<double>(frame) / kSampleRate);
        samples[sampleIndex] = static_cast<int16_t>(value);
        magnitude += static_cast<unsigned long long>(std::abs(static_cast<int>(samples[sampleIndex])));
      }
    }
    progress->outputMagnitude.fetch_add(magnitude);
  }
  if (input) {
    progress->inputCallbacks.fetch_add(1);
    progress->inputFrames.fetch_add(frameCount);
    const int16_t *samples = static_cast<const int16_t *>(input);
    unsigned long long magnitude = 0;
    for (unsigned int i = 0; i < frameCount * progress->inputChannels; ++i)
      magnitude += static_cast<unsigned long long>(std::abs(static_cast<int>(samples[i])));
    // Captured samples are measured and discarded here; they are never retained or written.
    progress->inputMagnitude.fetch_add(magnitude);
  }
  if (progress->callbackReturn && totalFrames >= progress->stopAfterFrames)
    return progress->callbackReturn;
  return 0;
}

bool waitForCallbacks(const Progress &progress, unsigned long long target, unsigned int timeoutMs = 4000)
{
  const auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(timeoutMs);
  while (std::chrono::steady_clock::now() < deadline) {
    if (progress.callbacks.load() >= target) return true;
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
  }
  return progress.callbacks.load() >= target;
}

bool waitForStopped(RtAudio &audio, unsigned int timeoutMs = 6000)
{
  const auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(timeoutMs);
  while (std::chrono::steady_clock::now() < deadline) {
    if (!audio.isStreamRunning()) return true;
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
  }
  return !audio.isStreamRunning();
}

void openProgressStream(RtAudio &audio, Progress &progress, bool output, bool input,
                        RtAudioCallback callback = onAudio)
{
  RtAudio::StreamParameters outParams;
  RtAudio::StreamParameters inParams;
  RtAudio::StreamParameters *out = 0;
  RtAudio::StreamParameters *in = 0;
  if (output) {
    outParams.deviceId = audio.getDefaultOutputDevice();
    outParams.nChannels = progress.outputChannels;
    outParams.firstChannel = 0;
    out = &outParams;
  }
  if (input) {
    inParams.deviceId = audio.getDefaultInputDevice();
    inParams.nChannels = progress.inputChannels;
    inParams.firstChannel = 0;
    in = &inParams;
  }
  RtAudio::StreamOptions options;
  options.flags = progress.nonInterleaved ? RTAUDIO_NONINTERLEAVED : 0;
  unsigned int frames = kBufferFrames;
  audio.openStream(out, in, RTAUDIO_SINT16, kSampleRate, &frames,
                   callback, &progress, &options);
}

struct StreamGuard {
  RtAudio &audio;
  explicit StreamGuard(RtAudio &value) : audio(value) {}
  ~StreamGuard() {
    try {
      if (audio.isStreamOpen()) {
        if (audio.isStreamRunning()) audio.stopStream();
        audio.closeStream();
      }
    } catch (...) {}
  }
};

struct RawPlayback {
  FILE *file;
  std::string path;
  std::atomic<unsigned long long> callbacks;
  std::atomic<unsigned long long> frames;
  std::atomic<unsigned long long> bytesRead;
  std::atomic<unsigned long long> magnitude;
  RawPlayback() : file(0), callbacks(0), frames(0), bytesRead(0), magnitude(0) {}
  ~RawPlayback() {
    if (file) std::fclose(file);
    if (!path.empty()) std::remove(path.c_str());
  }
};

int onRawPlayback(void *output, void *, unsigned int frameCount, double,
                  RtAudioStreamStatus, void *userData)
{
  RawPlayback *raw = static_cast<RawPlayback *>(userData);
  if (!raw || !raw->file || !output) return 2;
  int16_t *samples = static_cast<int16_t *>(output);
  const size_t read = std::fread(samples, sizeof(int16_t), frameCount, raw->file);
  unsigned long long magnitude = 0;
  for (size_t i = 0; i < read; ++i)
    magnitude += static_cast<unsigned long long>(std::abs(static_cast<int>(samples[i])));
  if (read < frameCount)
    std::memset(samples + read, 0, (frameCount - read) * sizeof(int16_t));
  raw->callbacks.fetch_add(1);
  raw->frames.fetch_add(read);
  raw->bytesRead.fetch_add(read * sizeof(int16_t));
  raw->magnitude.fetch_add(magnitude);
  return read < frameCount ? 1 : 0;
}

void addResult(std::ostringstream &report, const char *family, const std::string &id,
               bool passed, const std::string &evidence, unsigned int &passCount,
               unsigned int &totalCount)
{
  ++totalCount;
  if (passed) ++passCount;
  report << "RTAUDIO_" << family << "_TEST " << id << (passed ? "_PASS" : "_FAIL");
  if (!evidence.empty()) report << " " << evidence;
  report << '\n';
}

template <typename Test>
void runCase(std::ostringstream &report, const char *family, const char *id,
             Test test, unsigned int &passCount, unsigned int &totalCount)
{
  try {
    addResult(report, family, id, true, test(), passCount, totalCount);
  } catch (const std::exception &error) {
    std::string message(error.what());
    for (size_t i = 0; i < message.size(); ++i)
      if (message[i] == '\n' || message[i] == '\r') message[i] = ' ';
    addResult(report, family, id, false, "reason=" + message, passCount, totalCount);
  } catch (...) {
    addResult(report, family, id, false, "reason=unknown_exception", passCount, totalCount);
  }
}

std::vector<RtAudio::Api> compiledApis()
{
  std::vector<RtAudio::Api> apis;
  RtAudio::getCompiledApi(apis);
  return apis;
}

std::string runApiChecks(std::ostringstream &report, unsigned int &passed, unsigned int &total)
{
  const std::vector<RtAudio::Api> apis = compiledApis();
  const rtaudio_api_t *cApis = rtaudio_compiled_api();
  if (!cApis) throw std::runtime_error("C API returned a null compiled API list");

  runCase(report, "UPSTREAM", "U01", [&]() {
    for (size_t i = 0; i < apis.size(); ++i)
      if (RtAudio::getApiName(apis[i]).empty()) throw std::runtime_error("compiled API has no name");
    if (apis.empty()) throw std::runtime_error("no compiled API was listed");
    return "compiled_api_count=" + std::to_string(apis.size());
  }, passed, total);
  runCase(report, "UPSTREAM", "U02", [&]() {
    for (size_t i = 0; i < apis.size(); ++i)
      if (RtAudio::getApiDisplayName(apis[i]).empty()) throw std::runtime_error("compiled API has no display name");
    return "compiled_api_count=" + std::to_string(apis.size());
  }, passed, total);
  runCase(report, "UPSTREAM", "U03", []() {
    if (!RtAudio::getApiName(static_cast<RtAudio::Api>(-1)).empty())
      throw std::runtime_error("invalid API identifier returned a name");
    return std::string("invalid_api_name_empty=1");
  }, passed, total);
  runCase(report, "UPSTREAM", "U04", []() {
    if (RtAudio::getApiDisplayName(static_cast<RtAudio::Api>(-1)) != "Unknown")
      throw std::runtime_error("invalid API identifier did not return Unknown");
    return std::string("invalid_api_display=Unknown");
  }, passed, total);
  runCase(report, "UPSTREAM", "U05", [&]() {
    for (size_t i = 0; i < apis.size(); ++i) {
      const std::string name = RtAudio::getApiName(apis[i]);
      if (RtAudio::getCompiledApiByName(name) != apis[i])
        throw std::runtime_error("exact API name did not round-trip");
    }
    return "round_trips=" + std::to_string(apis.size());
  }, passed, total);
  runCase(report, "UPSTREAM", "U06", [&]() {
    for (size_t i = 0; i < apis.size(); ++i) {
      std::string mixed = RtAudio::getApiName(apis[i]);
      for (size_t j = 0; j < mixed.size(); ++j)
        mixed[j] = (j & 1) ? static_cast<char>(std::toupper(static_cast<unsigned char>(mixed[j])))
                           : static_cast<char>(std::tolower(static_cast<unsigned char>(mixed[j])));
      if (RtAudio::getCompiledApiByName(mixed) != RtAudio::UNSPECIFIED)
        throw std::runtime_error("mixed-case API name was accepted");
    }
    return "mixed_case_rejected=" + std::to_string(apis.size());
  }, passed, total);
  runCase(report, "UPSTREAM", "U07", []() {
    if (RtAudio::getCompiledApiByName("") != RtAudio::UNSPECIFIED)
      throw std::runtime_error("empty API name did not map to UNSPECIFIED");
    return std::string("empty_name_unspecified=1");
  }, passed, total);

  runCase(report, "UPSTREAM", "U08", [&]() {
    size_t count = 0;
    for (; cApis[count] != RTAUDIO_API_UNSPECIFIED; ++count) {
      const char *name = rtaudio_api_name(cApis[count]);
      if (!name || !name[0]) throw std::runtime_error("compiled C API has no name");
    }
    if (!count) throw std::runtime_error("no compiled C API was listed");
    return "compiled_api_count=" + std::to_string(count);
  }, passed, total);
  runCase(report, "UPSTREAM", "U09", [&]() {
    size_t count = 0;
    for (; cApis[count] != RTAUDIO_API_UNSPECIFIED; ++count) {
      const char *name = rtaudio_api_display_name(cApis[count]);
      if (!name || !name[0]) throw std::runtime_error("compiled C API has no display name");
    }
    return "compiled_api_count=" + std::to_string(count);
  }, passed, total);
  runCase(report, "UPSTREAM", "U10", []() {
    const char *name = rtaudio_api_name(static_cast<rtaudio_api_t>(-1));
    if (name && name[0]) throw std::runtime_error("invalid C API identifier returned a name");
    return std::string("invalid_api_name_empty=1");
  }, passed, total);
  runCase(report, "UPSTREAM", "U11", []() {
    const char *display = rtaudio_api_display_name(static_cast<rtaudio_api_t>(-1));
    if (!display || std::string(display) != "Unknown")
      throw std::runtime_error("invalid C API identifier did not return Unknown");
    return std::string("invalid_api_display=Unknown");
  }, passed, total);
  runCase(report, "UPSTREAM", "U12", [&]() {
    size_t count = 0;
    for (; cApis[count] != RTAUDIO_API_UNSPECIFIED; ++count) {
      const char *name = rtaudio_api_name(cApis[count]);
      if (rtaudio_compiled_api_by_name(name) != cApis[count])
        throw std::runtime_error("exact C API name did not round-trip");
    }
    return "round_trips=" + std::to_string(count);
  }, passed, total);
  runCase(report, "UPSTREAM", "U13", [&]() {
    size_t count = 0;
    for (; cApis[count] != RTAUDIO_API_UNSPECIFIED; ++count) {
      const char *name = rtaudio_api_name(cApis[count]);
      std::string mixed(name ? name : "");
      for (size_t j = 0; j < mixed.size(); ++j)
        mixed[j] = (j & 1) ? static_cast<char>(std::toupper(static_cast<unsigned char>(mixed[j])))
                           : static_cast<char>(std::tolower(static_cast<unsigned char>(mixed[j])));
      if (rtaudio_compiled_api_by_name(mixed.c_str()) != RTAUDIO_API_UNSPECIFIED)
        throw std::runtime_error("mixed-case C API name was accepted");
    }
    return "mixed_case_rejected=" + std::to_string(count);
  }, passed, total);
  runCase(report, "UPSTREAM", "U14", []() {
    if (rtaudio_compiled_api_by_name("") != RTAUDIO_API_UNSPECIFIED)
      throw std::runtime_error("empty C API name did not map to UNSPECIFIED");
    return std::string("empty_name_unspecified=1");
  }, passed, total);
  return "api_tests=14";
}

void runUpstreamDeviceCases(std::ostringstream &report, unsigned int &passed,
                            unsigned int &total, const std::string &temporaryDirectory,
                            const std::string &runId)
{
  runCase(report, "UPSTREAM", "U15", []() {
    RtAudio audio(RtAudio::OHOS_OHAUDIO);
    const std::vector<unsigned int> ids = audio.getDeviceIds();
    if (ids.empty()) throw std::runtime_error("no OHAudio routes enumerated");
    unsigned int inputRoutes = 0, outputRoutes = 0;
    std::string firstName;
    for (size_t i = 0; i < ids.size(); ++i) {
      const RtAudio::DeviceInfo info = audio.getDeviceInfo(ids[i]);
      if (info.name.empty()) throw std::runtime_error("enumerated route has no name");
      if (i == 0) firstName = info.name;
      if (info.inputChannels) ++inputRoutes;
      if (info.outputChannels) ++outputRoutes;
    }
    if (!inputRoutes || !outputRoutes) throw std::runtime_error("input or output route missing");
    const RtAudio::DeviceInfo outputInfo = audio.getDeviceInfo(audio.getDefaultOutputDevice());
    const RtAudio::DeviceInfo inputInfo = audio.getDeviceInfo(audio.getDefaultInputDevice());
    return "routes=" + std::to_string(ids.size()) + " input_routes=" + std::to_string(inputRoutes) +
      " output_routes=" + std::to_string(outputRoutes) + " output_channels=" +
      std::to_string(outputInfo.outputChannels) + " input_channels=" +
      std::to_string(inputInfo.inputChannels) + " rate=" +
      std::to_string(outputInfo.preferredSampleRate) + " first=" + firstName;
  }, passed, total);

  runCase(report, "UPSTREAM", "U16", []() {
    RtAudio audio(RtAudio::OHOS_OHAUDIO); StreamGuard guard(audio);
    Progress p; openProgressStream(audio, p, true, true);
    audio.startStream();
    if (!waitForCallbacks(p, 12)) throw std::runtime_error("duplex callbacks did not progress");
    audio.stopStream();
    const unsigned long long frames = p.frames.load();
    const unsigned long long inputCallbacks = p.inputCallbacks.load();
    if (frames < 4800 || !inputCallbacks || !p.outputMagnitude.load())
      throw std::runtime_error("duplex input/output callback data was incomplete");
    return "callbacks=" + std::to_string(p.callbacks.load()) + " frames=" +
      std::to_string(frames) + " input_callbacks=" + std::to_string(inputCallbacks) +
      " output_magnitude=" + std::to_string(p.outputMagnitude.load());
  }, passed, total);

  runCase(report, "UPSTREAM", "U17", [&]() {
    RawPlayback raw;
    if (temporaryDirectory.empty())
      throw std::runtime_error("application cache directory was not provided");
    raw.path = temporaryDirectory + "/rtaudio_raw_pcm_" + runId + ".s16le";
    raw.file = std::fopen(raw.path.c_str(), "wb+");
    if (!raw.file) throw std::runtime_error("temporary raw PCM fixture could not be created in app cache");
    const unsigned int fixtureFrames = 9600;
    std::vector<int16_t> fixture(fixtureFrames);
    for (unsigned int i = 0; i < fixtureFrames; ++i)
      fixture[i] = static_cast<int16_t>(10000.0 * std::sin(2.0 * kPi * 220.0 * i / kSampleRate));
    if (std::fwrite(&fixture[0], sizeof(int16_t), fixture.size(), raw.file) != fixture.size() ||
        std::fseek(raw.file, 0, SEEK_SET) != 0) {
      throw std::runtime_error("temporary raw PCM fixture could not be prepared");
    }
    RtAudio audio(RtAudio::OHOS_OHAUDIO); StreamGuard guard(audio);
    RtAudio::StreamParameters out;
    out.deviceId = audio.getDefaultOutputDevice(); out.nChannels = 1; out.firstChannel = 0;
    unsigned int frames = kBufferFrames;
    audio.openStream(&out, 0, RTAUDIO_SINT16, kSampleRate, &frames, onRawPlayback, &raw);
    audio.startStream();
    const bool completed = waitForStopped(audio, 5000);
    if (!completed || !raw.bytesRead.load() || !raw.magnitude.load()) {
      throw std::runtime_error("raw PCM playback did not consume nonzero audio data");
    }
    audio.closeStream();
    return "callbacks=" + std::to_string(raw.callbacks.load()) + " frames=" +
      std::to_string(raw.frames.load()) + " bytes_read=" +
      std::to_string(raw.bytesRead.load()) + " output_magnitude=" +
      std::to_string(raw.magnitude.load()) + " fixture=temporary_synthetic_pcm";
  }, passed, total);

  runCase(report, "UPSTREAM", "U18", []() {
    RtAudio audio(RtAudio::OHOS_OHAUDIO); StreamGuard guard(audio);
    Progress p(kChannels, 1, false, true); openProgressStream(audio, p, true, false);
    audio.startStream();
    if (!waitForCallbacks(p, 12)) throw std::runtime_error("sawtooth output callbacks did not progress");
    audio.stopStream(); audio.closeStream();
    if (!p.outputMagnitude.load()) throw std::runtime_error("sawtooth output was silent");
    return "callbacks=" + std::to_string(p.outputCallbacks.load()) + " frames=" +
      std::to_string(p.frames.load()) + " output_magnitude=" +
      std::to_string(p.outputMagnitude.load());
  }, passed, total);

  runCase(report, "UPSTREAM", "U19", []() {
    RtAudio audio(RtAudio::OHOS_OHAUDIO); StreamGuard guard(audio);
    Progress p(0, 1); p.stopAfterFrames = 9600; p.callbackReturn = 2;
    openProgressStream(audio, p, false, true); audio.startStream();
    if (!waitForStopped(audio, 6000)) throw std::runtime_error("bounded microphone capture did not stop");
    const unsigned long long frames = p.inputFrames.load();
    if (p.inputCallbacks.load() < 10 || frames < 4800)
      throw std::runtime_error("microphone capture callback/frame progress was insufficient");
    if (audio.isStreamOpen()) audio.closeStream();
    return "callbacks=" + std::to_string(p.inputCallbacks.load()) + " frames=" +
      std::to_string(frames) + " captured_data=measured_then_discarded storage=none";
  }, passed, total);

  runCase(report, "UPSTREAM", "U20", []() {
    RtAudio audio(RtAudio::OHOS_OHAUDIO); StreamGuard guard(audio);
    Progress p; openProgressStream(audio, p, true, false);
    audio.startStream(); if (!waitForCallbacks(p, 10)) throw std::runtime_error("first playback did not start");
    audio.stopStream(); if (audio.isStreamRunning()) throw std::runtime_error("stop left playback running");
    unsigned long long target = p.callbacks.load() + 8;
    audio.startStream(); if (!waitForCallbacks(p, target)) throw std::runtime_error("playback restart failed");
    audio.abortStream(); if (!waitForStopped(audio)) throw std::runtime_error("abort did not stop playback");
    target = p.callbacks.load() + 8;
    audio.startStream(); if (!waitForCallbacks(p, target)) throw std::runtime_error("second playback restart failed");
    audio.closeStream(); if (audio.isStreamOpen()) throw std::runtime_error("close left playback open");
    return "callbacks=" + std::to_string(p.callbacks.load()) + " stop_abort_restart=passed";
  }, passed, total);

  runCase(report, "UPSTREAM", "U21", []() {
    RtAudio audio(RtAudio::OHOS_OHAUDIO); StreamGuard guard(audio);
    Progress p(kChannels, 1, true, true); openProgressStream(audio, p, true, false);
    audio.startStream(); if (!waitForCallbacks(p, 12)) throw std::runtime_error("planar playback did not progress");
    audio.stopStream(); audio.closeStream();
    if (!p.outputMagnitude.load()) throw std::runtime_error("planar playback output was silent");
    return "callbacks=" + std::to_string(p.outputCallbacks.load()) + " frames=" +
      std::to_string(p.frames.load()) + " output_magnitude=" +
      std::to_string(p.outputMagnitude.load()) + " layout=non_interleaved";
  }, passed, total);

  runCase(report, "UPSTREAM", "U22", []() {
    RtAudio audio(RtAudio::OHOS_OHAUDIO); StreamGuard guard(audio);
    Progress p; openProgressStream(audio, p, true, true);
    audio.startStream(); if (!waitForCallbacks(p, 10)) throw std::runtime_error("duplex start failed");
    audio.stopStream();
    const unsigned long long target = p.callbacks.load() + 10;
    audio.startStream(); if (!waitForCallbacks(p, target)) throw std::runtime_error("duplex restart failed");
    audio.stopStream(); audio.closeStream();
    if (!p.inputCallbacks.load() || !p.outputMagnitude.load()) throw std::runtime_error("duplex directions did not both progress");
    return "callbacks=" + std::to_string(p.callbacks.load()) + " input_callbacks=" +
      std::to_string(p.inputCallbacks.load()) + " output_magnitude=" +
      std::to_string(p.outputMagnitude.load()) + " restarted=1";
  }, passed, total);

  runCase(report, "UPSTREAM", "U23", []() {
    RtAudio audio(RtAudio::OHOS_OHAUDIO); StreamGuard guard(audio);
    Progress p; openProgressStream(audio, p, true, true); audio.startStream();
    if (!waitForCallbacks(p, 10)) throw std::runtime_error("duplex stream did not start");
    audio.stopStream();
    if (audio.isStreamRunning() || p.callbacks.load() < 10)
      throw std::runtime_error("external stop did not end a progressing duplex stream");
    audio.closeStream();
    return "callbacks=" + std::to_string(p.callbacks.load()) + " input_callbacks=" +
      std::to_string(p.inputCallbacks.load()) + " external_stop=passed";
  }, passed, total);

  runCase(report, "UPSTREAM", "U24", []() {
    RtAudio audio(RtAudio::OHOS_OHAUDIO); StreamGuard guard(audio);
    Progress p; p.stopAfterFrames = 4800; p.callbackReturn = 1;
    openProgressStream(audio, p, true, true); audio.startStream();
    if (!waitForStopped(audio) || p.frames.load() < p.stopAfterFrames)
      throw std::runtime_error("callback return 1 did not stop duplex stream");
    if (audio.isStreamOpen()) audio.closeStream();
    return "callbacks=" + std::to_string(p.callbacks.load()) + " frames=" +
      std::to_string(p.frames.load()) + " callback_stop=1";
  }, passed, total);

  runCase(report, "UPSTREAM", "U25", []() {
    RtAudio audio(RtAudio::OHOS_OHAUDIO); StreamGuard guard(audio);
    Progress p; p.stopAfterFrames = 4800; p.callbackReturn = 2;
    openProgressStream(audio, p, true, true); audio.startStream();
    if (!waitForStopped(audio) || p.frames.load() < p.stopAfterFrames)
      throw std::runtime_error("callback return 2 did not abort duplex stream");
    if (audio.isStreamOpen()) audio.closeStream();
    return "callbacks=" + std::to_string(p.callbacks.load()) + " frames=" +
      std::to_string(p.frames.load()) + " callback_abort=2";
  }, passed, total);

  runCase(report, "UPSTREAM", "U26", []() {
    RtAudio audio(RtAudio::OHOS_OHAUDIO); StreamGuard guard(audio);
    Progress p;
    for (unsigned int repeat = 0; repeat < 3; ++repeat) {
      openProgressStream(audio, p, true, true); audio.startStream();
      const unsigned long long target = p.callbacks.load() + 8;
      if (!waitForCallbacks(p, target)) throw std::runtime_error("reopened duplex stream did not progress");
      audio.stopStream(); audio.closeStream();
    }
    return "reopen_cycles=3 callbacks=" + std::to_string(p.callbacks.load()) +
      " input_callbacks=" + std::to_string(p.inputCallbacks.load());
  }, passed, total);

  runCase(report, "UPSTREAM", "U27", []() {
    unsigned long long callbacks = 0;
    for (unsigned int repeat = 0; repeat < 3; ++repeat) {
      RtAudio audio(RtAudio::OHOS_OHAUDIO); StreamGuard guard(audio);
      Progress p; openProgressStream(audio, p, true, true); audio.startStream();
      if (!waitForCallbacks(p, 8)) throw std::runtime_error("new duplex instance did not progress");
      audio.stopStream(); audio.closeStream(); callbacks += p.callbacks.load();
    }
    return "instance_cycles=3 callbacks=" + std::to_string(callbacks) + " destroyed=3";
  }, passed, total);
}

void runHarmonyDeviceCases(std::ostringstream &report, unsigned int &passed, unsigned int &total)
{
  runCase(report, "DEVICE", "H01", []() {
    DirectProgress p;
    DirectProbeStatus status;
    runDirectOhaudioProbe(p, status);
    if (status.create != AUDIOSTREAM_SUCCESS || status.configure != AUDIOSTREAM_SUCCESS ||
        status.generate != AUDIOSTREAM_SUCCESS || status.start != AUDIOSTREAM_SUCCESS ||
        status.stop != AUDIOSTREAM_SUCCESS || status.release != AUDIOSTREAM_SUCCESS ||
        p.callbacks.load() < 10 || !p.bytes.load() || !p.magnitude.load()) {
      throw std::runtime_error("direct OHAudio probe statuses=create:" + std::to_string(status.create) +
        ",configure:" + std::to_string(status.configure) + ",generate:" +
        std::to_string(status.generate) + ",start:" + std::to_string(status.start) +
        ",stop:" + std::to_string(status.stop) + ",release:" +
        std::to_string(status.release) + ",callbacks:" + std::to_string(p.callbacks.load()) +
        ",bytes:" + std::to_string(p.bytes.load()) + ",magnitude:" +
        std::to_string(p.magnitude.load()));
    }
    return "api=OHAudio_renderer result=" + std::to_string(status.start) +
      " callbacks=" + std::to_string(p.callbacks.load()) + " bytes=" +
      std::to_string(p.bytes.load()) + " output_magnitude=" +
      std::to_string(p.magnitude.load()) + " generated_pcm=440Hz";
  }, passed, total);

  runCase(report, "DEVICE", "H02", []() {
    RtAudio audio(RtAudio::OHOS_OHAUDIO); StreamGuard guard(audio);
    Progress p; openProgressStream(audio, p, true, false); audio.startStream();
    if (!waitForCallbacks(p, 12)) throw std::runtime_error("RtAudio OHAudio renderer callbacks did not progress");
    audio.stopStream(); audio.closeStream();
    if (p.frames.load() < 4800 || !p.outputMagnitude.load())
      throw std::runtime_error("RtAudio OHAudio renderer produced insufficient frames or PCM");
    return "api=RtAudio_OHAudio callbacks=" + std::to_string(p.outputCallbacks.load()) +
      " frames=" + std::to_string(p.frames.load()) + " output_magnitude=" +
      std::to_string(p.outputMagnitude.load());
  }, passed, total);
}

} // namespace

int runOhosDeviceTest(const std::string &mode, const std::string &temporaryDirectory,
                      const std::string &runId, std::string &report)
{
  if (mode != "--suite") {
    report = "OHOS_SUITE_FATAL: expected --suite\n";
    return 2;
  }
  std::ostringstream output;
  unsigned int passed = 0;
  unsigned int total = 0;
  try {
    runApiChecks(output, passed, total);
    runUpstreamDeviceCases(output, passed, total, temporaryDirectory, runId);
    runHarmonyDeviceCases(output, passed, total);
    output << "RTAUDIO_SUITE_COMPLETE passed=" << passed << " total=" << total << '\n';
    report = output.str();
    return total == 29 && passed == total ? 0 : 1;
  } catch (const std::exception &error) {
    output << "OHOS_SUITE_FATAL: " << error.what() << '\n';
    report = output.str();
    return 1;
  }
}

#ifndef RTAUDIO_OHOS_APP_HOST
int main(int argc, char **argv)
{
  const std::string mode = argc > 1 ? argv[1] : "--suite";
  std::string report;
  const std::string temporaryDirectory = argc > 2 ? argv[2] : "/tmp";
  const std::string runId = argc > 3 ? argv[3] : "standalone";
  const int result = runOhosDeviceTest(mode, temporaryDirectory, runId, report);
  std::fputs(report.c_str(), stdout);
  return result;
}
#endif
