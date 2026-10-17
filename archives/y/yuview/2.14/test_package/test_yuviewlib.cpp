// Consumer test for the YUView package.
//
// The test links the packaged YUViewLib static library, calls its public API and
// verifies a real round trip through the pixel format model. It fails to link
// when the packaged library is missing and fails at runtime when the library is
// broken, so it cannot pass against an empty package.

#include <iostream>
#include <string>
#include <vector>

#include <video/yuv/PixelFormatYUV.h>

int main()
{
  int failures = 0;

  // Build a planar 4:2:0 8-bit format through the public constructor.
  video::yuv::PixelFormatYUV format(video::yuv::Subsampling::YUV_420, 8);

  if (!format.isValid())
  {
    std::cerr << "FAIL: constructed 4:2:0 8-bit format is not valid" << std::endl;
    return 1;
  }

  const std::string name = format.getName();
  std::cout << "format name: " << name << std::endl;
  if (name.empty() || name == "Invalid")
  {
    std::cerr << "FAIL: getName() returned an unusable name" << std::endl;
    ++failures;
  }

  if (format.getBitsPerSample() != 8)
  {
    std::cerr << "FAIL: getBitsPerSample() = " << format.getBitsPerSample()
              << ", expected 8" << std::endl;
    ++failures;
  }

  // The name must describe exactly the same format again.
  video::yuv::PixelFormatYUV roundTrip(name);
  if (!(roundTrip == format))
  {
    std::cerr << "FAIL: round trip through getName() changed the format" << std::endl;
    ++failures;
  }

  // Another bit depth must produce a different format.
  video::yuv::PixelFormatYUV highBitDepth(video::yuv::Subsampling::YUV_420, 10);
  if (highBitDepth == format)
  {
    std::cerr << "FAIL: 10-bit format compares equal to the 8-bit format" << std::endl;
    ++failures;
  }

  if (failures != 0)
  {
    std::cerr << failures << " assertion(s) failed" << std::endl;
    return 1;
  }

  std::cout << "YUViewLib consumer assertions passed" << std::endl;
  return 0;
}
