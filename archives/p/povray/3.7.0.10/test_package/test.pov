// POV-Ray 3.7 smoke-render scene (OHOS adaptation test)
// Minimal but non-trivial: camera + light + checkered plane + sphere with
// pigment/finish (exercises parser, scene library include, shading, PNG output).
#version 3.7;
#include "colors.inc"

global_settings { assumed_gamma 1.0 }

camera {
  location <0, 2, -5>
  look_at <0, 1, 0>
  right x * image_width / image_height
}

light_source { <-10, 10, -10> color White }

plane {
  y, 0
  pigment { checker color Black color White }
}

sphere {
  <0, 1, 0>, 1
  pigment { color Red }
  finish { phong 1.0 reflection 0.2 }
}
