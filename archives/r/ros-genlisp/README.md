# ros-genlisp

Common Lisp message and service generator support package for ROS 1.

## Version

- 0.4.18

## Build notes

- This is a target-independent ROS generator resource package.
- The recipe validates the expected Python modules, generator script, message/service templates, CMake extra file, and `package.xml` metadata.
- Python modules are packaged under `lib/python/genlisp`; generator scripts and templates are packaged under `share/ros-genlisp`.

## Test notes

The Conan `test_package` verifies the installed package layout and metadata without requiring a full ROS/genmsg runtime.
