// test_package/test_libheif_openh264.cpp — libheif-openh264 1.23.0 消费者测试（鸿蒙特有）
//
// R34：真实调用被测包交付面的 API，不是空壳测试。
// R40（多媒体/编解码类）：不做只查版本的浅测——本程序既证明交付的插件模块真被宿主
// dlopen 并注册了 AVC 解码器，又对同一条运行时链路上的 libopenh264 做了一次真实的
// H.264 编码→解码回环（I420 帧进出、校验解码尺寸）。
//
// 本包交付面 = libheif 宿主（lib/libheif.so）+ OpenH264 解码插件模块
// （lib/libheif/libheif-openh264dec.so，上游目标 heif-openh264dec）。插件是运行期由宿主
// dlopen 的 MODULE，所以判据不是"能链接"，而是"插件真被宿主装载并注册了 AVC 解码器"：
//   heif_init() → heif_get_plugin_directories() → heif_have_decoder_for_format(AVC)。
//
// 检查数与结果由程序自报（LIBSHEIF_OPENH264_CONSUMER checks_total=… checks_passed=…），
// conanfile.py 不硬编码数字；任一检查失败即返回 1，conan create 判 FAIL。
#include <cstdio>
#include <cstring>
#include <vector>

#include <libheif/heif.h>
#include <wels/codec_api.h>
#include <wels/codec_ver.h>

static int checks_total = 0;
static int checks_passed = 0;

static void check(bool condition, const char* what)
{
  checks_total++;
  if (condition) {
    checks_passed++;
    std::printf("  [ ok ] %s\n", what);
  }
  else {
    std::printf("  [FAIL] %s\n", what);
  }
}

// --- 真实的 H.264 编码→解码回环（走交付包运行期解析到的 libopenh264）-------------
static int openh264_roundtrip(int* out_width, int* out_height)
{
  const int kWidth = 320;
  const int kHeight = 240;

  // ① 编码一帧 I420
  ISVCEncoder* encoder = nullptr;
  if (WelsCreateSVCEncoder(&encoder) != 0 || encoder == nullptr) {
    std::fprintf(stderr, "WelsCreateSVCEncoder failed\n");
    return -1;
  }

  SEncParamBase param;
  std::memset(&param, 0, sizeof(param));
  param.iUsageType = CAMERA_VIDEO_REAL_TIME;
  param.iPicWidth = kWidth;
  param.iPicHeight = kHeight;
  param.iTargetBitrate = 200000;
  param.fMaxFrameRate = 15.0f;

  if (encoder->Initialize(&param) != 0) {
    std::fprintf(stderr, "ISVCEncoder::Initialize failed\n");
    WelsDestroySVCEncoder(encoder);
    return -1;
  }

  std::vector<unsigned char> frame(static_cast<size_t>(kWidth) * kHeight * 3 / 2);
  for (int y = 0; y < kHeight; ++y) {                    // 非均匀画面，避免码流退化
    std::memset(&frame[static_cast<size_t>(y) * kWidth], y & 0xFF, kWidth);
  }
  std::memset(&frame[static_cast<size_t>(kWidth) * kHeight], 0x80,
              static_cast<size_t>(kWidth) * kHeight / 4);
  std::memset(&frame[static_cast<size_t>(kWidth) * kHeight * 5 / 4], 0x40,
              static_cast<size_t>(kWidth) * kHeight / 4);

  SSourcePicture picture;
  std::memset(&picture, 0, sizeof(picture));
  picture.iColorFormat = videoFormatI420;
  picture.iPicWidth = kWidth;
  picture.iPicHeight = kHeight;
  picture.iStride[0] = kWidth;
  picture.iStride[1] = kWidth / 2;
  picture.iStride[2] = kWidth / 2;
  picture.pData[0] = frame.data();
  picture.pData[1] = frame.data() + static_cast<size_t>(kWidth) * kHeight;
  picture.pData[2] = frame.data() + static_cast<size_t>(kWidth) * kHeight * 5 / 4;

  SFrameBSInfo info;
  std::memset(&info, 0, sizeof(info));
  if (encoder->EncodeFrame(&picture, &info) != cmResultSuccess ||
      info.eFrameType == videoFrameTypeSkip) {
    std::fprintf(stderr, "ISVCEncoder::EncodeFrame produced no bitstream\n");
    encoder->Uninitialize();
    WelsDestroySVCEncoder(encoder);
    return -1;
  }

  std::vector<unsigned char> bitstream;
  for (int layer = 0; layer < info.iLayerNum; ++layer) {
    const SLayerBSInfo& layer_info = info.sLayerInfo[layer];
    int layer_size = 0;
    for (int nal = 0; nal < layer_info.iNalCount; ++nal) {
      layer_size += layer_info.pNalLengthInByte[nal];
    }
    bitstream.insert(bitstream.end(), layer_info.pBsBuf,
                     layer_info.pBsBuf + layer_size);
  }
  encoder->Uninitialize();
  WelsDestroySVCEncoder(encoder);

  if (bitstream.empty()) {
    std::fprintf(stderr, "openh264 produced empty bitstream\n");
    return -1;
  }
  std::printf("  openh264 encoder: %d.%d.%d, %zu bytes, %d layer(s)\n",
              OPENH264_MAJOR, OPENH264_MINOR, OPENH264_REVISION,
              bitstream.size(), info.iLayerNum);

  // ② 解码同一码流
  ISVCDecoder* decoder = nullptr;
  if (WelsCreateDecoder(&decoder) != 0 || decoder == nullptr) {
    std::fprintf(stderr, "WelsCreateDecoder failed\n");
    return -1;
  }

  SDecodingParam decoding_param;
  std::memset(&decoding_param, 0, sizeof(decoding_param));
  decoding_param.sVideoProperty.eVideoBsType = VIDEO_BITSTREAM_AVC;
  decoding_param.eEcActiveIdc = ERROR_CON_SLICE_COPY;

  if (decoder->Initialize(&decoding_param) != 0) {
    std::fprintf(stderr, "ISVCDecoder::Initialize failed\n");
    WelsDestroyDecoder(decoder);
    return -1;
  }

  unsigned char* decoded[3] = {nullptr, nullptr, nullptr};
  SBufferInfo buffer_info;
  std::memset(&buffer_info, 0, sizeof(buffer_info));
  const DECODING_STATE state =
      decoder->DecodeFrameNoDelay(bitstream.data(),
                                  static_cast<int>(bitstream.size()),
                                  decoded, &buffer_info);
  const int ready = (state == dsErrorFree && buffer_info.iBufferStatus == 1);
  *out_width = ready ? buffer_info.UsrData.sSystemBuffer.iWidth : -1;
  *out_height = ready ? buffer_info.UsrData.sSystemBuffer.iHeight : -1;
  if (!ready) {
    std::fprintf(stderr, "DecodeFrameNoDelay state=%d bufferStatus=%d\n",
                 static_cast<int>(state), buffer_info.iBufferStatus);
  }
  decoder->Uninitialize();
  WelsDestroyDecoder(decoder);
  return ready ? 0 : -1;
}

int main()
{
  std::printf("libheif-openh264 1.23.0 consumer test\n");

  /* --- 1. 版本指纹：链接到的宿主必须就是本包交付的 1.23.0 --- */
  const char* version = heif_get_version();
  std::printf("  heif_get_version() = %s\n", version ? version : "(null)");
  check(version != nullptr && std::strcmp(version, "1.23.0") == 0,
        "heif_get_version() == \"1.23.0\"");
  check(heif_get_version_number_major() == 1 &&
            heif_get_version_number_minor() == 23 &&
            heif_get_version_number_maintenance() == 0,
        "heif_get_version_number_major/minor/maintenance == 1/23/0");

  /* --- 2. 初始化：上游文档明确 heif_init() 才装载默认插件目录下的外部插件 --- */
  const heif_error init_error = heif_init(nullptr);
  std::printf("  heif_init(NULL) -> code=%d (%s)\n", static_cast<int>(init_error.code),
              init_error.message ? init_error.message : "");
  check(init_error.code == heif_error_Ok, "heif_init(NULL) == heif_error_Ok");

  /* --- 3. 插件搜索目录：由配方 package_info() 的 runenv_info 经
   *        LIBHEIF_PLUGIN_PATH 导出（libheif/init.cc 优先读它） --- */
  const char* const* dirs = heif_get_plugin_directories();
  int dir_count = 0;
  bool dir_is_package_libheif = false;
  const char* first_dir = nullptr;
  if (dirs != nullptr) {
    for (int i = 0; dirs[i] != nullptr; ++i) {
      dir_count++;
      std::printf("  plugin dir[%d] = %s\n", i, dirs[i]);
      if (first_dir == nullptr) {
        first_dir = dirs[i];
      }
      if (std::strstr(dirs[i], "libheif") != nullptr) {
        dir_is_package_libheif = true;
      }
    }
  }
  check(dir_count >= 1, "heif_get_plugin_directories() 返回 >= 1 个插件目录");
  check(dir_is_package_libheif,
        "插件目录指向交付的 <pkg>/lib/libheif（LIBHEIF_PLUGIN_PATH 生效）");

  /* --- 4. 核心判据：openh264 插件模块已装载并注册 AVC 解码器 --- */
  check(heif_have_decoder_for_format(heif_compression_AVC) == 1,
        "heif_have_decoder_for_format(AVC) == 1（libheif-openh264dec.so 已装载）");

  /* --- 5. 直接证据：交付目录里的 .so 是可被 libheif 装载的插件（plugin_info 可解析） --- */
  if (first_dir != nullptr) {
    const heif_plugin_info* loaded[8] = {nullptr};
    int loaded_count = 0;
    const heif_error load_error =
        heif_load_plugins(first_dir, loaded, &loaded_count, 8);
    bool has_decoder_plugin = false;
    for (int i = 0; i < loaded_count; ++i) {
      if (loaded[i] != nullptr && loaded[i]->type == heif_plugin_type_decoder) {
        has_decoder_plugin = true;
      }
    }
    std::printf("  heif_load_plugins -> code=%d loaded=%d\n",
                static_cast<int>(load_error.code), loaded_count);
    check(load_error.code == heif_error_Ok && loaded_count >= 1,
          "heif_load_plugins(交付插件目录) 装载 >= 1 个插件");
    check(has_decoder_plugin, "装载到的插件里有 heif_plugin_type_decoder");
  }

  /* --- 6. 反证：本包未启用其它后端 --- */
  check(heif_have_decoder_for_format(heif_compression_HEVC) == 0,
        "heif_have_decoder_for_format(HEVC) == 0（无 HEVC 解码后端）");
  check(heif_have_decoder_for_format(heif_compression_AV1) == 0,
        "heif_have_decoder_for_format(AV1) == 0（无 AV1 解码后端）");
  check(heif_have_encoder_for_format(heif_compression_AVC) == 0,
        "heif_have_encoder_for_format(AVC) == 0（上游未启用 OpenH264 编码后端）");

  /* --- 7. R40：交付链路运行期真实编解码回环（libopenh264 由本包依赖解析到） --- */
  int decoded_width = -1;
  int decoded_height = -1;
  const int roundtrip = openh264_roundtrip(&decoded_width, &decoded_height);
  check(roundtrip == 0, "openh264 H.264 编码→解码回环成功（dsErrorFree 且出帧）");
  std::printf("  decoded frame = %dx%d\n", decoded_width, decoded_height);
  check(decoded_width == 320 && decoded_height == 240,
        "解码帧尺寸 == 320x240（与编码输入一致）");

  /* --- 8. 宿主 API 可用性：context 生命周期 --- */
  struct heif_context* ctx = heif_context_alloc();
  check(ctx != nullptr, "heif_context_alloc() != nullptr");
  if (ctx != nullptr) {
    heif_context_free(ctx);
  }

  /* --- 9. 反初始化（与 heif_init 引用计数配对） --- */
  heif_deinit();

  std::printf("LIBSHEIF_OPENH264_CONSUMER checks_total=%d checks_passed=%d\n",
              checks_total, checks_passed);
  if (checks_passed != checks_total) {
    std::printf("RESULT: FAIL\n");
    return 1;
  }
  std::printf("RESULT: PASS\n");
  return 0;
}
