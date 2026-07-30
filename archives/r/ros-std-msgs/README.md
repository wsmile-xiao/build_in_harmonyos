# ros-std-msgs

`ros-std-msgs` packages the standard ROS 1 message schemas from the upstream
`std_msgs` project.

## Features

- 32 primitive, array, metadata, time, and color message definitions
- Exact upstream schemas for downstream ROS message generators
- Package metadata for downstream ROS tooling

## OpenHarmony adaptation

The source archive contains message schemas rather than a standalone native
library. The Conan recipe validates and packages those platform-independent
resources without requiring Catkin on the target. No upstream source patch is
needed.

## Dependencies

There are no Conan package dependencies. The upstream helper headers depend on
Catkin-generated message bindings, so this archive intentionally does not
publish them as standalone C++ interfaces. Consumers must use a ROS 1 message
generator when language-specific bindings are required.

## References

- https://github.com/ros/std_msgs
- https://index.ros.org/r/std_msgs/
