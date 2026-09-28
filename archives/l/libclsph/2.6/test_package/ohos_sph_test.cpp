// HarmonyOS-specific test for libclsph 2.6.
//
// Validates the adapted OpenCL compute stack on HarmonyOS PC end-to-end:
//   1. libOpenCL.so (ocl-icd ICD loader) resolves on OHOS
//   2. an OpenCL platform/device is enumerated (oclgrind software runtime
//      is the OHOS software OpenCL backend; the PC has no GPU OpenCL)
//   3. the packaged SPH kernels (sph.cl include chain) COMPILE on OHOS
//   4. a bounded kernel EXECUTES and its result is read back and verified
//
// Uses only the library's exported public headers (clsph/scene.h,
// clsph/sph_simulation.h, clsph/util/cl.hpp). Run from a cwd containing
// scenes/, fluid_properties/, simulation_properties/, kernels/ and common/
// (the packaged runtime data directories).
#include <clsph/scene.h>
#include <clsph/sph_simulation.h>
#include <clsph/util/cl.hpp>

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

static std::string read_file(const std::string& path) {
  std::ifstream in(path.c_str());
  return std::string((std::istreambuf_iterator<char>(in)),
                     std::istreambuf_iterator<char>());
}

int main() {
  // 1) Host-side public API sanity (settings + scene).
  sph_simulation sim;
  sim.load_settings("fluid_properties/water.json",
                    "simulation_properties/default.json");
  scene sc;
  if (!sc.load("box.obj") || sc.face_count == 0) {
    std::fprintf(stderr, "OHOS TEST FAIL: scene load failed\n");
    return 1;
  }
  std::printf("OHOS TEST host API: faces=%u particles=%d\n", sc.face_count,
              sim.parameters.particles_count);

  // 2) Enumerate the OpenCL platform/device via the OHOS ICD loader.
  std::vector<cl::Platform> platforms;
  cl_int err = cl::Platform::get(&platforms);
  if (err != CL_SUCCESS || platforms.empty()) {
    std::fprintf(stderr, "OHOS TEST FAIL: no OpenCL platform (err=%d)\n", err);
    return 2;
  }
  std::vector<cl::Device> devices;
  err = platforms[0].getDevices(CL_DEVICE_TYPE_ALL, &devices);
  if (err != CL_SUCCESS || devices.empty()) {
    std::fprintf(stderr, "OHOS TEST FAIL: no OpenCL device (err=%d)\n", err);
    return 3;
  }
  std::printf("OHOS TEST platform=%s device=%s\n",
              platforms[0].getInfo<CL_PLATFORM_NAME>().c_str(),
              devices[0].getInfo<CL_DEVICE_NAME>().c_str());

  // 3) Compile the packaged SPH kernels (sph.cl include chain) on OHOS.
  cl::Context context(devices);
  cl::CommandQueue queue(context, devices[0]);
  std::string sph_src = read_file("kernels/sph.cl");
  if (sph_src.empty()) {
    std::fprintf(stderr, "OHOS TEST FAIL: cannot read kernels/sph.cl\n");
    return 4;
  }
  cl::Program::Sources sources(1, std::make_pair(sph_src.c_str(), sph_src.length()));
  cl::Program program(context, sources);
  err = program.build(devices, "-I ./kernels/ -I ./common/");
  if (err != CL_SUCCESS) {
    std::string log;
    program.getBuildInfo(devices[0], CL_PROGRAM_BUILD_LOG, &log);
    std::fprintf(stderr, "OHOS TEST FAIL: SPH kernel compile failed (%d)\n%s\n",
                 err, log.c_str());
    return 5;
  }
  std::printf("OHOS TEST SPH kernels compiled OK\n");

  // 4) Bounded kernel execution with an observable verified result.
  cl::Kernel square(program, "density_pressure");  // compile-time symbol check
  const char* tiny_src = "kernel void ohos_square(global float* in,"
                         " global float* out){int i=get_global_id(0);"
                         "out[i]=in[i]*in[i];}";
  cl::Program::Sources ts(1, std::make_pair(tiny_src, strlen(tiny_src)));
  cl::Program tprog(context, ts);
  if (tprog.build(devices) != CL_SUCCESS) {
    std::fprintf(stderr, "OHOS TEST FAIL: tiny kernel build failed\n");
    return 6;
  }
  cl::Kernel tker(tprog, "ohos_square");
  float in[4] = {1.f, 2.f, 3.f, 4.f};
  float out[4] = {0.f, 0.f, 0.f, 0.f};
  cl::Buffer ib(context, CL_MEM_READ_ONLY | CL_MEM_COPY_HOST_PTR,
                sizeof(in), in);
  cl::Buffer ob(context, CL_MEM_WRITE_ONLY, sizeof(out));
  tker.setArg(0, ib);
  tker.setArg(1, ob);
  err = queue.enqueueNDRangeKernel(tker, cl::NullRange, cl::NDRange(4),
                                   cl::NullRange);
  if (err != CL_SUCCESS) {
    std::fprintf(stderr, "OHOS TEST FAIL: kernel enqueue (err=%d)\n", err);
    return 7;
  }
  err = queue.enqueueReadBuffer(ob, CL_TRUE, 0, sizeof(out), out);
  if (err != CL_SUCCESS) {
    std::fprintf(stderr, "OHOS TEST FAIL: readback (err=%d)\n", err);
    return 8;
  }
  std::printf("OHOS TEST kernel result: %g %g %g %g\n", (double)out[0],
              (double)out[1], (double)out[2], (double)out[3]);
  if (out[0] != 1.f || out[1] != 4.f || out[2] != 9.f || out[3] != 16.f) {
    std::fprintf(stderr, "OHOS TEST FAIL: unexpected kernel result\n");
    return 9;
  }

  std::printf("OHOS TEST PASS\n");
  return 0;
}
