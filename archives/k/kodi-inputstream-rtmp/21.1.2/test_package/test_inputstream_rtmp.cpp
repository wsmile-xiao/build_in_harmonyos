/*
 * Consumer-side test for the inputstream.rtmp add-on module.
 *
 * Part 1 (linked entry points)
 * ---------------------------
 * Links against the packaged shared library and executes the C entry points
 * that ADDONCREATOR() (kodi/AddonBase.h) exports from the add-on:
 *
 *   const char* ADDON_GetTypeVersion(int type)
 *   const char* ADDON_GetTypeMinVersion(int type)
 *
 * Both are pure functions (a switch over the Kodi instance types compiled in
 * through kodi/versions.h), so they are callable without a Kodi host. They
 * prove the vendored kodi-dev-kit headers were compiled into the module and
 * that the module loads (all DT_NEEDED — OpenSSL/zlib — resolve at exec).
 *
 * Part 2 (full consumer flow through the C ABI factory, review rule12)
 * --------------------------------------------------------------------
 * dlopen()s the module, dlsym()s the ADDONCREATOR-generated factory export
 * ADDON_Create(), and drives a real declaration/open session as a minimal
 * Kodi host stub:
 *
 *   1. host fills AddonGlobalInterface (stub toKodi callbacks, empty toAddon)
 *   2. ADDON_Create() instantiates the real CMyAddon (CAddonBase) and the
 *      addon wires its KodiToAddonFuncTable_Addon
 *   3. toAddon->create_instance() for ADDON_INSTANCE_INPUTSTREAM constructs
 *      the real CInputStreamRTMP instance and wires its inputstream function
 *      table (open/close/get_capabilities/...) and the instance handle
 *   4. get_capabilities() must report exactly
 *      INPUTSTREAM_SUPPORTS_IPOSTIME|SEEK|PAUSE — the upstream
 *      CInputStreamRTMP::GetCapabilities implementation
 *   5. open() on an invalid RTMP URL and on an unreachable RTMP server
 *      (loopback, port 1 → connection refused) must fail in a controlled
 *      way: return false through the real librtmp session path
 *      (RTMP_Alloc → RTMP_Init → RTMP_SetupURL/RTMP_Connect → RTMP_Close)
 *      without crashing, and leave the instance reusable
 *   6. close() + destroy_instance() + destroy() + dlclose() tear everything
 *      down cleanly
 *
 * Expected version values are the ADDON_GLOBAL_VERSION_* /
 * ADDON_INSTANCE_VERSION_* macros of xbmc 21.3-Omega kodi/versions.h
 * (inputstream instance 3.3.0). The C ABI structs below are transcribed
 * from the kodi-dev-kit c-api headers (kodi/c-api/addon_base.h,
 * kodi/c-api/addon-instance/inputstream.h) — the package installs no
 * headers, a binary add-on consumer/host talks to the module through this
 * stable C ABI only. static_asserts guard the transcription against struct
 * drift.
 */
#include <dlfcn.h>

#include <cstdint>
#include <cstdio>
#include <cstring>

extern "C" {
const char* ADDON_GetTypeVersion(int type);
const char* ADDON_GetTypeMinVersion(int type);
}

/* ==========================================================================
 * C ABI transcription (kodi/c-api/addon_base.h + inputstream.h)
 * ==========================================================================
 */
typedef void* KODI_ADDON_HDL;
typedef void* KODI_ADDON_BACKEND_HDL;
typedef void* KODI_ADDON_INSTANCE_HDL;
typedef void* KODI_ADDON_INSTANCE_BACKEND_HDL;
typedef int KODI_ADDON_INSTANCE_TYPE;

/* ADDON_STATUS — only ADDON_STATUS_OK (first member, 0) is asserted. */
enum { ADDON_STATUS_OK = 0 };
typedef int ADDON_STATUS_R;

/* ADDON_TYPE ids from kodi/versions.h */
static const int kAddonGlobalMain = 0;             /* ADDON_GLOBAL_MAIN       */
static const int kAddonGlobalGeneral = 3;          /* ADDON_GLOBAL_GENERAL    */
static const int kAddonInstanceInputstream = 105;  /* ADDON_INSTANCE_INPUTSTREAM */

/* INPUTSTREAM_SUPPORTS_* from kodi/c-api/addon-instance/inputstream.h */
static const uint32_t kSupportsIPostime = 1u << 1;
static const uint32_t kSupportsSeek = 1u << 3;
static const uint32_t kSupportsPause = 1u << 4;

#define STREAM_MAX_PROPERTY_COUNT 30

struct INPUTSTREAM_CAPABILITIES
{
  uint32_t m_mask;
};

struct INPUTSTREAM_PROPERTY
{
  const char* m_strURL;
  const char* m_mimeType;

  unsigned int m_nCountInfoValues;
  struct LISTITEMPROPERTY
  {
    const char* m_strKey;
    const char* m_strValue;
  } m_ListItemProperties[STREAM_MAX_PROPERTY_COUNT];

  const char* m_libFolder;
  const char* m_profileFolder;
};

struct INPUTSTREAM_IDS;
struct INPUTSTREAM_INFO;
struct INPUTSTREAM_TIMES;
struct DEMUX_PACKET;

struct AddonInstance_InputStream;

struct KodiToAddonFuncTable_InputStream
{
  void* addonInstance;

  bool (*open)(const struct AddonInstance_InputStream* instance,
               struct INPUTSTREAM_PROPERTY* props);
  void (*close)(const struct AddonInstance_InputStream* instance);
  const char* (*get_path_list)(const struct AddonInstance_InputStream* instance);
  void (*get_capabilities)(const struct AddonInstance_InputStream* instance,
                           struct INPUTSTREAM_CAPABILITIES* capabilities);

  // IDemux
  bool (*get_stream_ids)(const struct AddonInstance_InputStream* instance,
                         struct INPUTSTREAM_IDS* ids);
  bool (*get_stream)(const struct AddonInstance_InputStream* instance,
                     int streamid,
                     struct INPUTSTREAM_INFO* info,
                     void** demuxStream,
                     void* (*transfer_stream)(void* handle, int streamId, struct INPUTSTREAM_INFO* stream));
  void (*enable_stream)(const struct AddonInstance_InputStream* instance,
                        int streamid,
                        bool enable);
  bool (*open_stream)(const struct AddonInstance_InputStream* instance, int streamid);
  void (*demux_reset)(const struct AddonInstance_InputStream* instance);
  void (*demux_abort)(const struct AddonInstance_InputStream* instance);
  void (*demux_flush)(const struct AddonInstance_InputStream* instance);
  struct DEMUX_PACKET* (*demux_read)(const struct AddonInstance_InputStream* instance);
  bool (*demux_seek_time)(const struct AddonInstance_InputStream* instance,
                          double time,
                          bool backwards,
                          double* startpts);
  void (*demux_set_speed)(const struct AddonInstance_InputStream* instance, int speed);
  void (*set_video_resolution)(const struct AddonInstance_InputStream* instance,
                               unsigned int width,
                               unsigned int height,
                               unsigned int maxWidth,
                               unsigned int maxHeight);

  // IDisplayTime
  int (*get_total_time)(const struct AddonInstance_InputStream* instance);
  int (*get_time)(const struct AddonInstance_InputStream* instance);

  // ITime
  bool (*get_times)(const struct AddonInstance_InputStream* instance,
                    struct INPUTSTREAM_TIMES* times);

  // IPosTime
  bool (*pos_time)(const struct AddonInstance_InputStream* instance, int ms);

  int (*read_stream)(const struct AddonInstance_InputStream* instance,
                     uint8_t* buffer,
                     unsigned int bufferSize);
  long long (*seek_stream)(const struct AddonInstance_InputStream* instance,
                           long long position,
                           int whence);
  long long (*position_stream)(const struct AddonInstance_InputStream* instance);
  long long (*length_stream)(const struct AddonInstance_InputStream* instance);
  bool (*is_real_time_stream)(const struct AddonInstance_InputStream* instance);

  // IChapter
  int (*get_chapter)(const struct AddonInstance_InputStream* instance);
  int (*get_chapter_count)(const struct AddonInstance_InputStream* instance);
  const char* (*get_chapter_name)(const struct AddonInstance_InputStream* instance, int ch);
  long long (*get_chapter_pos)(const struct AddonInstance_InputStream* instance, int ch);
  bool (*seek_chapter)(const struct AddonInstance_InputStream* instance, int ch);

  int (*block_size_stream)(const struct AddonInstance_InputStream* instance);
};

struct AddonProps_InputStream
{
  int dummy;
};

struct AddonToKodiFuncTable_InputStream
{
  void* kodiInstance;
  struct DEMUX_PACKET* (*allocate_demux_packet)(void* kodiInstance, int data_size);
  struct DEMUX_PACKET* (*allocate_encrypted_demux_packet)(void* kodiInstance,
                                                          unsigned int data_size,
                                                          unsigned int encrypted_subsample_count);
  void (*free_demux_packet)(void* kodiInstance, struct DEMUX_PACKET* packet);
};

struct AddonInstance_InputStream
{
  struct AddonProps_InputStream* props;
  struct AddonToKodiFuncTable_InputStream* toKodi;
  struct KodiToAddonFuncTable_InputStream* toAddon;
};

struct KODI_ADDON_INSTANCE_FUNC
{
  ADDON_STATUS_R (*instance_setting_change_string)(const KODI_ADDON_INSTANCE_HDL hdl,
                                                   const char* name,
                                                   const char* value);
  ADDON_STATUS_R (*instance_setting_change_boolean)(const KODI_ADDON_INSTANCE_HDL hdl,
                                                    const char* name,
                                                    bool value);
  ADDON_STATUS_R (*instance_setting_change_integer)(const KODI_ADDON_INSTANCE_HDL hdl,
                                                    const char* name,
                                                    int value);
  ADDON_STATUS_R (*instance_setting_change_float)(const KODI_ADDON_INSTANCE_HDL hdl,
                                                  const char* name,
                                                  float value);
};

struct KODI_ADDON_INSTANCE_FUNC_CB
{
  char* (*get_instance_user_path)(const KODI_ADDON_INSTANCE_BACKEND_HDL hdl);
  bool (*is_instance_setting_using_default)(const KODI_ADDON_INSTANCE_BACKEND_HDL hdl,
                                            const char* id);

  bool (*get_instance_setting_bool)(const KODI_ADDON_INSTANCE_BACKEND_HDL hdl,
                                    const char* id,
                                    bool* value);
  bool (*get_instance_setting_int)(const KODI_ADDON_INSTANCE_BACKEND_HDL hdl,
                                   const char* id,
                                   int* value);
  bool (*get_instance_setting_float)(const KODI_ADDON_INSTANCE_BACKEND_HDL hdl,
                                     const char* id,
                                     float* value);
  bool (*get_instance_setting_string)(const KODI_ADDON_INSTANCE_BACKEND_HDL hdl,
                                      const char* id,
                                      char** value);

  bool (*set_instance_setting_bool)(const KODI_ADDON_INSTANCE_BACKEND_HDL hdl,
                                    const char* id,
                                    bool value);
  bool (*set_instance_setting_int)(const KODI_ADDON_INSTANCE_BACKEND_HDL hdl,
                                   const char* id,
                                   int value);
  bool (*set_instance_setting_float)(const KODI_ADDON_INSTANCE_BACKEND_HDL hdl,
                                     const char* id,
                                     float value);
  bool (*set_instance_setting_string)(const KODI_ADDON_INSTANCE_BACKEND_HDL hdl,
                                      const char* id,
                                      const char* value);
};

struct KODI_ADDON_INSTANCE_INFO
{
  KODI_ADDON_INSTANCE_TYPE type;
  uint32_t number;
  const char* id;
  const char* version;
  KODI_ADDON_INSTANCE_BACKEND_HDL kodi;
  KODI_ADDON_INSTANCE_HDL parent;
  bool first_instance;

  struct KODI_ADDON_INSTANCE_FUNC_CB* functions;
};

struct KODI_ADDON_INSTANCE_STRUCT
{
  const KODI_ADDON_INSTANCE_INFO* info;

  KODI_ADDON_INSTANCE_HDL hdl;
  struct KODI_ADDON_INSTANCE_FUNC* functions;
  union
  {
    void* dummy;
    struct AddonInstance_InputStream* inputstream;
  };
};

struct AddonToKodiFuncTable_Addon
{
  KODI_ADDON_BACKEND_HDL kodiBase;

  void (*free_string)(const KODI_ADDON_BACKEND_HDL hdl, char* str);
  void (*free_string_array)(const KODI_ADDON_BACKEND_HDL hdl, char** arr, int numElements);
  void (*addon_log_msg)(const KODI_ADDON_BACKEND_HDL hdl, const int loglevel, const char* msg);

  void* kodi;
  void* kodi_addon;
  void* kodi_audioengine;
  void* kodi_filesystem;
  void* kodi_gui;
  void* kodi_network;
};

struct KodiToAddonFuncTable_Addon
{
  ADDON_STATUS_R (*create)(const KODI_ADDON_INSTANCE_BACKEND_HDL first_instance, KODI_ADDON_HDL* hdl);
  void (*destroy)(const KODI_ADDON_HDL hdl);
  ADDON_STATUS_R (*create_instance)(const KODI_ADDON_HDL hdl, struct KODI_ADDON_INSTANCE_STRUCT* instance);
  void (*destroy_instance)(const KODI_ADDON_HDL hdl, struct KODI_ADDON_INSTANCE_STRUCT* instance);
  ADDON_STATUS_R (*setting_change_string)(const KODI_ADDON_HDL hdl, const char* name, const char* value);
  ADDON_STATUS_R (*setting_change_boolean)(const KODI_ADDON_HDL hdl, const char* name, bool value);
  ADDON_STATUS_R (*setting_change_integer)(const KODI_ADDON_HDL hdl, const char* name, int value);
  ADDON_STATUS_R (*setting_change_float)(const KODI_ADDON_HDL hdl, const char* name, float value);
};

struct AddonGlobalInterface
{
  struct KODI_ADDON_INSTANCE_STRUCT* firstKodiInstance;
  KODI_ADDON_HDL addonBase;
  KODI_ADDON_INSTANCE_HDL globalSingleInstance;
  AddonToKodiFuncTable_Addon* toKodi;
  KodiToAddonFuncTable_Addon* toAddon;
};

/* Guards for the C ABI transcription (aarch64 LP64: pointers 8 bytes). */
static_assert(sizeof(AddonGlobalInterface) == 5 * 8, "AddonGlobalInterface layout drift");
static_assert(sizeof(AddonToKodiFuncTable_Addon) == 10 * 8, "AddonToKodiFuncTable_Addon layout drift");
static_assert(sizeof(KodiToAddonFuncTable_Addon) == 8 * 8, "KodiToAddonFuncTable_Addon layout drift");
static_assert(sizeof(KODI_ADDON_INSTANCE_INFO) == 7 * 8, "KODI_ADDON_INSTANCE_INFO layout drift");
static_assert(sizeof(KODI_ADDON_INSTANCE_FUNC) == 4 * 8, "KODI_ADDON_INSTANCE_FUNC layout drift");
static_assert(sizeof(KODI_ADDON_INSTANCE_FUNC_CB) == 10 * 8, "KODI_ADDON_INSTANCE_FUNC_CB layout drift");
static_assert(sizeof(KODI_ADDON_INSTANCE_STRUCT) == 4 * 8, "KODI_ADDON_INSTANCE_STRUCT layout drift");
static_assert(sizeof(AddonInstance_InputStream) == 3 * 8, "AddonInstance_InputStream layout drift");
static_assert(sizeof(AddonToKodiFuncTable_InputStream) == 4 * 8, "AddonToKodiFuncTable_InputStream layout drift");
static_assert(sizeof(KodiToAddonFuncTable_InputStream) == 31 * 8, "KodiToAddonFuncTable_InputStream layout drift");
static_assert(sizeof(INPUTSTREAM_CAPABILITIES) == 4, "INPUTSTREAM_CAPABILITIES layout drift");
static_assert(sizeof(INPUTSTREAM_PROPERTY) == 520, "INPUTSTREAM_PROPERTY layout drift");

/* ==========================================================================
 * Check helpers
 * ==========================================================================
 */
static int failures = 0;

static void check(bool cond, const char* msg)
{
  std::printf("%s: %s\n", cond ? "ok" : "FAIL", msg);
  if (!cond)
    failures++;
}

static void check_str(const char* got, const char* want, const char* msg)
{
  check(got != nullptr, msg);
  if (got != nullptr)
    check(std::strcmp(got, want) == 0, msg);
}

/* ==========================================================================
 * Host stub callbacks (part 2): the tested flow never reaches Kodi-side
 * calls; the two stubs prove the toKodi direction is plumbable.
 * ==========================================================================
 */
static void stub_free_string(const KODI_ADDON_BACKEND_HDL /*hdl*/, char* str)
{
  /* Kodi-owned string buffers; nothing to release in the stub. */
  (void)str;
}

static void stub_addon_log_msg(const KODI_ADDON_BACKEND_HDL /*hdl*/,
                               const int loglevel,
                               const char* msg)
{
  std::printf("[host-stub log lvl %d] %s\n", loglevel, msg ? msg : "(null)");
}

int main(void)
{
  /* ------------------------------------------------------------------
   * Part 1 — linked entry points: version reporting (no host needed)
   * ------------------------------------------------------------------ */
  check_str(ADDON_GetTypeVersion(kAddonInstanceInputstream), "3.3.0",
            "inputstream instance API version reported by the add-on");
  check_str(ADDON_GetTypeMinVersion(kAddonInstanceInputstream), "3.3.0",
            "inputstream instance API min version reported by the add-on");
  check_str(ADDON_GetTypeVersion(kAddonGlobalGeneral), "1.0.5",
            "general API version reported by the add-on");
  check_str(ADDON_GetTypeMinVersion(kAddonGlobalGeneral), "1.0.4",
            "general API min version reported by the add-on");
  check_str(ADDON_GetTypeVersion(kAddonGlobalMain), "2.0.2",
            "main API version reported by the add-on");
  check_str(ADDON_GetTypeMinVersion(kAddonGlobalMain), "2.0.0",
            "main API min version reported by the add-on");

  /* ------------------------------------------------------------------
   * Part 2 — full consumer flow through the C ABI factory (dlopen)
   * ------------------------------------------------------------------ */
  /* The test binary links the module, so the loader has already mapped it
   * via its DT_SONAME (the recipe sets -Wl,-soname,libinputstream.rtmp.so;
   * CI gate L5a asserts it). dlopen by that soname therefore attaches to the
   * loaded module deterministically — exactly how a binary-add-on host
   * obtains a module handle before dlsym'ing the ADDONCREATOR factory. */
  void* mod = dlopen("libinputstream.rtmp.so", RTLD_NOW);
  check(mod != nullptr, "dlopen of the packaged libinputstream.rtmp.so succeeds");
  if (mod == nullptr)
  {
    const char* err = dlerror();
    std::printf("dlopen error: %s\n", err ? err : "(unknown)");
    std::printf("test kodi-inputstream-rtmp 21.1.2: %d failures\n", failures);
    return 1;
  }

  typedef ADDON_STATUS_R (*PFN_ADDON_Create)(void* addonInterface);
  PFN_ADDON_Create addonCreate =
      reinterpret_cast<PFN_ADDON_Create>(dlsym(mod, "ADDON_Create"));
  check(addonCreate != nullptr, "dlsym ADDON_Create (ADDONCREATOR factory export)");

  typedef const char* (*PFN_ADDON_GetTypeVersion)(int type);
  PFN_ADDON_GetTypeVersion modGetTypeVersion =
      reinterpret_cast<PFN_ADDON_GetTypeVersion>(dlsym(mod, "ADDON_GetTypeVersion"));
  check_str(modGetTypeVersion ? modGetTypeVersion(kAddonInstanceInputstream) : nullptr, "3.3.0",
            "dlsym'd module reports inputstream API 3.3.0");

  /* Host side of the add-on interface (what Kodi fills before ADDON_Create) */
  AddonToKodiFuncTable_Addon toKodi = {};
  toKodi.kodiBase = &toKodi; /* opaque backend handle, unused by the stubs */
  toKodi.free_string = stub_free_string;
  toKodi.addon_log_msg = stub_addon_log_msg;

  KodiToAddonFuncTable_Addon toAddon = {};
  AddonGlobalInterface global = {};
  global.toKodi = &toKodi;
  global.toAddon = &toAddon;
  /* firstKodiInstance stays null: CInputStreamRTMP is created through the
   * multi-instance path (CMyAddon::CreateInstance), like Kodi does. */

  ADDON_STATUS_R status = addonCreate(&global);
  check(status == ADDON_STATUS_OK, "ADDON_Create instantiates the real add-on base");
  check(global.addonBase != nullptr, "ADDON_Create published the addonBase handle");
  check(toAddon.create_instance != nullptr && toAddon.destroy_instance != nullptr &&
            toAddon.destroy != nullptr,
        "add-on wired KodiToAddonFuncTable_Addon during CAddonBase construction");

  /* Host side of the inputstream instance (what Kodi fills before
   * create_instance) */
  KODI_ADDON_INSTANCE_FUNC_CB instanceFuncCb = {};
  KODI_ADDON_INSTANCE_INFO info = {};
  info.type = kAddonInstanceInputstream;
  info.number = 0;
  info.id = "inputstream.rtmp";
  info.version = "3.3.0";
  info.kodi = &instanceFuncCb; /* backend handle, unused by the tested flow */
  info.parent = nullptr;
  info.first_instance = true;
  info.functions = &instanceFuncCb;

  AddonProps_InputStream streamProps = {};
  AddonToKodiFuncTable_InputStream isToKodi = {};
  KodiToAddonFuncTable_InputStream isToAddon = {};
  AddonInstance_InputStream inputStream = {};
  inputStream.props = &streamProps;
  inputStream.toKodi = &isToKodi;
  inputStream.toAddon = &isToAddon;

  KODI_ADDON_INSTANCE_FUNC instanceFunc = {};
  KODI_ADDON_INSTANCE_STRUCT instance = {};
  instance.info = &info;
  instance.functions = &instanceFunc;
  instance.inputstream = &inputStream;

  status = toAddon.create_instance(global.addonBase, &instance);
  check(status == ADDON_STATUS_OK, "create_instance declares the real inputstream instance");
  check(instance.hdl != nullptr, "create_instance published the instance handle");
  check(isToAddon.open != nullptr && isToAddon.close != nullptr &&
            isToAddon.get_capabilities != nullptr,
        "instance wired KodiToAddonFuncTable_InputStream (open/close/get_capabilities)");
  check(isToAddon.addonInstance != nullptr && isToAddon.addonInstance == instance.hdl,
        "instance handle resolves to the created CInstanceInputStream subobject");

  INPUTSTREAM_CAPABILITIES caps = {};
  isToAddon.get_capabilities(&inputStream, &caps);
  check(caps.m_mask == (kSupportsIPostime | kSupportsSeek | kSupportsPause),
        "GetCapabilities reports exactly IPOSTIME|SEEK|PAUSE (upstream CInputStreamRTMP)");

  /* Real Open flow: invalid RTMP URL must fail in a controlled way through
   * the upstream path RTMP_Alloc → RTMP_Init → RTMP_SetupURL → RTMP_Close */
  INPUTSTREAM_PROPERTY openProps = {};
  openProps.m_strURL = "this-is-not-an-rtmp-url";
  bool opened = isToAddon.open(&inputStream, &openProps);
  check(!opened, "Open(invalid RTMP URL) fails in a controlled way (false, no crash)");

  /* Real Open flow against an unreachable server: loopback port 1 refuses,
   * exercising RTMP_Connect failure propagation */
  openProps.m_strURL = "rtmp://127.0.0.1:1/live";
  opened = isToAddon.open(&inputStream, &openProps);
  check(!opened, "Open(unreachable RTMP server) propagates the connection failure");

  isToAddon.close(&inputStream);

  INPUTSTREAM_CAPABILITIES capsAfter = {};
  isToAddon.get_capabilities(&inputStream, &capsAfter);
  check(capsAfter.m_mask == caps.m_mask,
        "instance stays consistent after failed Open + Close (GetCapabilities stable)");

  /* Tear down exactly like the Kodi host: instance first, then base */
  toAddon.destroy_instance(global.addonBase, &instance);
  toAddon.destroy(global.addonBase);
  dlclose(mod);
  check(true, "destroy_instance + destroy + dlclose completed without crash");

  if (failures == 0)
  {
    std::printf("test kodi-inputstream-rtmp 21.1.2: all checks OK (6 version + 15 consumer flow)\n");
    return 0;
  }
  std::printf("test kodi-inputstream-rtmp 21.1.2: %d failures\n", failures);
  return 1;
}
