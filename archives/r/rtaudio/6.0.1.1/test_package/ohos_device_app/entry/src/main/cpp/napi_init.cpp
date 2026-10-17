#include "napi/native_api.h"

#include <new>
#include <string>

int runOhosDeviceTest(const std::string& mode, const std::string& temporaryDirectory,
                      const std::string& runId, std::string& report);

struct OHAudioTestWork {
  napi_async_work work;
  napi_deferred deferred;
  std::string runId;
  std::string temporaryDirectory;
  std::string report;
  int result;

  OHAudioTestWork() : work(nullptr), deferred(nullptr), result(1) {}
};

static void ExecuteOHAudioTest(napi_env, void *data)
{
  OHAudioTestWork *work = static_cast<OHAudioTestWork *>(data);
  work->result = runOhosDeviceTest("--suite", work->temporaryDirectory,
                                   work->runId, work->report);
}

static void CompleteOHAudioTest(napi_env env, napi_status status, void *data)
{
  OHAudioTestWork *work = static_cast<OHAudioTestWork *>(data);
  if (status == napi_ok) {
    napi_value result = nullptr;
    napi_create_string_utf8(env, work->report.c_str(), work->report.size(), &result);
    napi_resolve_deferred(env, work->deferred, result);
  } else {
    const std::string message = "HarmonyOS cancelled the OHAudio test worker.";
    napi_value text = nullptr;
    napi_value error = nullptr;
    napi_create_string_utf8(env, message.c_str(), message.size(), &text);
    napi_create_error(env, nullptr, text, &error);
    napi_reject_deferred(env, work->deferred, error);
  }
  napi_delete_async_work(env, work->work);
  delete work;
}

static napi_value RunSuite(napi_env env, napi_callback_info info)
{
  size_t argc = 2;
  napi_value argv[2] = {nullptr, nullptr};
  napi_get_cb_info(env, info, &argc, argv, nullptr, nullptr);

  OHAudioTestWork *work = new (std::nothrow) OHAudioTestWork();
  if (!work) {
    napi_throw_error(env, nullptr, "Unable to allocate the OHAudio test worker.");
    return nullptr;
  }
  if (argc > 0) {
    size_t length = 0;
    napi_get_value_string_utf8(env, argv[0], nullptr, 0, &length);
    work->runId.resize(length + 1);
    napi_get_value_string_utf8(env, argv[0], &work->runId[0], work->runId.size(), &length);
    work->runId.resize(length);
  }
  if (argc < 2) {
    delete work;
    napi_throw_type_error(env, nullptr, "An application cache directory is required.");
    return nullptr;
  }
  size_t directoryLength = 0;
  if (napi_get_value_string_utf8(env, argv[1], nullptr, 0, &directoryLength) != napi_ok) {
    delete work;
    napi_throw_type_error(env, nullptr, "The application cache directory must be a string.");
    return nullptr;
  }
  work->temporaryDirectory.resize(directoryLength + 1);
  if (napi_get_value_string_utf8(env, argv[1], &work->temporaryDirectory[0],
                                 work->temporaryDirectory.size(), &directoryLength) != napi_ok) {
    delete work;
    napi_throw_type_error(env, nullptr, "Unable to read the application cache directory.");
    return nullptr;
  }
  work->temporaryDirectory.resize(directoryLength);

  napi_value promise = nullptr;
  if (napi_create_promise(env, &work->deferred, &promise) != napi_ok) {
    delete work;
    napi_throw_error(env, nullptr, "Unable to create the OHAudio test promise.");
    return nullptr;
  }
  napi_value resourceName = nullptr;
  if (napi_create_string_utf8(env, "RtAudioOHAudioDeviceSuite", NAPI_AUTO_LENGTH,
                              &resourceName) != napi_ok ||
      napi_create_async_work(env, nullptr, resourceName, ExecuteOHAudioTest,
                             CompleteOHAudioTest, work, &work->work) != napi_ok) {
    delete work;
    napi_throw_error(env, nullptr, "Unable to queue the OHAudio test worker.");
    return nullptr;
  }
  if (napi_queue_async_work(env, work->work) != napi_ok) {
    napi_delete_async_work(env, work->work);
    delete work;
    napi_throw_error(env, nullptr, "Unable to start the OHAudio test worker.");
    return nullptr;
  }
  return promise;
}

EXTERN_C_START
static napi_value Init(napi_env env, napi_value exports)
{
  const napi_property_descriptor properties[] = {
    { "runSuite", nullptr, RunSuite, nullptr, nullptr, nullptr, napi_default, nullptr }
  };
  napi_define_properties(env, exports, sizeof(properties) / sizeof(properties[0]), properties);
  return exports;
}
EXTERN_C_END

static napi_module testModule = {
  .nm_version = 1,
  .nm_flags = 0,
  .nm_filename = nullptr,
  .nm_register_func = Init,
  .nm_modname = "entry",
  .nm_priv = nullptr,
  .reserved = { 0 },
};

extern "C" __attribute__((constructor)) void RegisterRtAudioTestModule(void)
{
  napi_module_register(&testModule);
}
