# ros-std-msgs 0.5.14 adaptation notes

## Package model

The upstream ROS 1 `std_msgs` package contains 32 `.msg` interface definitions.
Its helper headers include Catkin-generated message bindings that are absent
until `message_generation` runs. Because Catkin is not part of this archive,
the recipe packages only the authoritative schemas and package metadata as
platform-independent resources. It does not expose the incomplete helper
headers as a standalone C++ interface.

## Source and patches

- Source: official `ros/std_msgs` tag `0.5.14`
- SHA256: `adf1e84d5fa3d7e5e817230171d0147f042992c96eaa69c440cd739ff73b9f32`
- Patches: none

## Upstream tests

The official 0.5.14 tag contains no test directory, test target, or test
dependency. The CMake project only registers 32 message files, invokes
`generate_messages()`, and installs the helper headers.

## Consumer validation

The Conan consumer test reads the files from the final package and performs 35
checks. It verifies the exact 32-file inventory, parses every non-comment field
declaration, rejects unresolved message types, compares every complete public
schema with the authoritative 0.5.14 definition, and checks the package name
and version.

The test is intentionally host-executed during a cross build because the
package consists solely of platform-independent text schemas and metadata; it
does not execute a target binary.

Native Windows `conan create` completed successfully and the packaged consumer
reported 35/35 checks. The local upstream Conan 2.29.1 distribution does not
recognize the competition worker's `os=OHOS` extension, so the official OHOS
Profile could not be executed locally. The official competition CI remains the
authoritative OHOS validation.

## Known limitations

The package does not generate C++, Python, or other ROS language bindings.
Consumers still need a ROS 1 message generator if generated bindings are
required.
