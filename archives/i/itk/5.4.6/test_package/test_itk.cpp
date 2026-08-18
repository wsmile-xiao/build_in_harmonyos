#include <stdexcept>

#include "itkImage.h"

int main() {
  using ImageType = itk::Image<unsigned char, 2>;
  ImageType::RegionType region;
  ImageType::IndexType start;
  start.Fill(0);
  ImageType::SizeType size;
  size[0] = 3;
  size[1] = 2;
  region.SetIndex(start);
  region.SetSize(size);

  auto image = ImageType::New();
  image->SetRegions(region);
  image->Allocate();
  image->FillBuffer(7);

  ImageType::IndexType pixel_index;
  pixel_index[0] = 2;
  pixel_index[1] = 1;
  image->SetPixel(pixel_index, 42);

  if (image->GetBufferedRegion().GetNumberOfPixels() != 6) {
    throw std::runtime_error("unexpected image size");
  }
  if (image->GetPixel(pixel_index) != 42) {
    throw std::runtime_error("explicit pixel write was not preserved");
  }
  pixel_index[0] = 0;
  pixel_index[1] = 0;
  if (image->GetPixel(pixel_index) != 7) {
    throw std::runtime_error("fill buffer value was not preserved");
  }
  if (image->GetReferenceCount() == 0) {
    throw std::runtime_error("ITK object reference count is invalid");
  }

  return 0;
}
