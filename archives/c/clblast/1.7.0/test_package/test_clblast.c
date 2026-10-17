#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CL_TARGET_OPENCL_VERSION 120
#define CL_USE_DEPRECATED_OPENCL_1_2_APIS  // to disable deprecation warnings

// Includes the CLBlast library (C interface) and the OpenCL headers
#include <clblast_c.h>

// =================================================================================================
// Consumer smoke test: runs CLBlastSaxpy on the first available OpenCL device and
// verifies y = alpha * x + y on the host side. This genuinely exercises the
// libclblast API (device buffers + kernel launch + read-back).
// =================================================================================================
int main(void) {
  const size_t platform_id = 0;
  const size_t device_id = 0;
  const size_t n = 1024;
  const float alpha = 2.0f;

  // Initializes the OpenCL platform
  cl_uint num_platforms = 0;
  if (clGetPlatformIDs(0, NULL, &num_platforms) != CL_SUCCESS || num_platforms == 0) {
    fprintf(stderr, "No OpenCL platform found\n");
    return 1;
  }
  cl_platform_id* platforms = (cl_platform_id*)malloc(num_platforms * sizeof(cl_platform_id));
  clGetPlatformIDs(num_platforms, platforms, NULL);
  cl_platform_id platform = platforms[platform_id];

  // Initializes the OpenCL device
  cl_uint num_devices = 0;
  if (clGetDeviceIDs(platform, CL_DEVICE_TYPE_ALL, 0, NULL, &num_devices) != CL_SUCCESS ||
      num_devices == 0) {
    fprintf(stderr, "No OpenCL device found on the platform\n");
    return 1;
  }
  cl_device_id* devices = (cl_device_id*)malloc(num_devices * sizeof(cl_device_id));
  clGetDeviceIDs(platform, CL_DEVICE_TYPE_ALL, num_devices, devices, NULL);
  cl_device_id device = devices[device_id];

  // Creates the OpenCL context and queue
  cl_context context = clCreateContext(NULL, 1, &device, NULL, NULL, NULL);
  cl_command_queue queue = clCreateCommandQueue(context, device, 0, NULL);
  if (!context || !queue) {
    fprintf(stderr, "Failed to create OpenCL context/queue\n");
    return 1;
  }

  // Host data: x = 1.0, y = 0.0  ->  y = alpha * x + y = 2.0
  float* host_x = (float*)malloc(sizeof(float) * n);
  float* host_y = (float*)malloc(sizeof(float) * n);
  for (size_t i = 0; i < n; ++i) {
    host_x[i] = 1.0f;
    host_y[i] = 0.0f;
  }

  // Device buffers
  cl_mem device_x = clCreateBuffer(context, CL_MEM_READ_WRITE, n * sizeof(float), NULL, NULL);
  cl_mem device_y = clCreateBuffer(context, CL_MEM_READ_WRITE, n * sizeof(float), NULL, NULL);
  clEnqueueWriteBuffer(queue, device_x, CL_TRUE, 0, n * sizeof(float), host_x, 0, NULL, NULL);
  clEnqueueWriteBuffer(queue, device_y, CL_TRUE, 0, n * sizeof(float), host_y, 0, NULL, NULL);

  // Call the SAXPY routine
  cl_event event = NULL;
  CLBlastStatusCode status = CLBlastSaxpy(n, alpha, device_x, 0, 1, device_y, 0, 1, &queue, &event);
  if (status != CLBlastSuccess) {
    fprintf(stderr, "CLBlastSaxpy failed with status %d\n", (int)status);
    return 1;
  }
  clWaitForEvents(1, &event);

  // Read back and verify
  float* result = (float*)malloc(sizeof(float) * n);
  clEnqueueReadBuffer(queue, device_y, CL_TRUE, 0, n * sizeof(float), result, 0, NULL, NULL);
  int failures = 0;
  for (size_t i = 0; i < n; ++i) {
    if (result[i] != 2.0f) {
      failures++;
    }
  }

  // Cleanup
  clReleaseMemObject(device_x);
  clReleaseMemObject(device_y);
  clReleaseCommandQueue(queue);
  clReleaseContext(context);
  free(platforms);
  free(devices);
  free(host_x);
  free(host_y);
  free(result);

  if (failures > 0) {
    fprintf(stderr, "SAXPY verification failed for %d element(s)\n", failures);
    return 1;
  }
  printf("clblast test_package: CLBlastSaxpy passed (%zu elements, alpha=%.1f)\n", n, alpha);
  return 0;
}
