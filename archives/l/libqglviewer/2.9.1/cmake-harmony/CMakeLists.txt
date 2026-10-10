cmake_minimum_required(VERSION 3.16)
project(libQGLViewer VERSION 2.9.1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(qgl_src "${QGLVIEWER_UPSTREAM}/QGLViewer")
set(qt_includes
    "${QT5_PREFIX}/include"
    "${QT5_PREFIX}/include/QtCore"
    "${QT5_PREFIX}/include/QtGui"
    "${QT5_PREFIX}/include/QtWidgets"
    "${QT5_PREFIX}/include/QtXml"
    "${QT5_PREFIX}/include/QtOpenGL")

# The published Qt5 package's CMake extras contain stale build-prefix
# mkspec paths. Use its real installed headers, libraries, moc and uic.
set(qgl_generated)
foreach(class camera frame keyFrameInterpolator manipulatedCameraFrame
              manipulatedFrame qglviewer)
    set(header "${qgl_src}/${class}.h")
    set(generated "${CMAKE_CURRENT_BINARY_DIR}/moc_${class}.cpp")
    add_custom_command(OUTPUT "${generated}"
        COMMAND "${QT5_PREFIX}/bin/moc" "${header}" -o "${generated}"
        DEPENDS "${header}" VERBATIM)
    list(APPEND qgl_generated "${generated}")
endforeach()
add_custom_command(OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/ui_ImageInterface.h"
    COMMAND "${QT5_PREFIX}/bin/uic" "${qgl_src}/ImageInterface.ui"
            -o "${CMAKE_CURRENT_BINARY_DIR}/ui_ImageInterface.h"
    DEPENDS "${qgl_src}/ImageInterface.ui" VERBATIM)

add_library(QGLViewer SHARED
    "${qgl_src}/camera.cpp"
    "${qgl_src}/constraint.cpp"
    "${qgl_src}/frame.cpp"
    "${qgl_src}/keyFrameInterpolator.cpp"
    "${qgl_src}/manipulatedCameraFrame.cpp"
    "${qgl_src}/manipulatedFrame.cpp"
    "${qgl_src}/mouseGrabber.cpp"
    "${qgl_src}/qglviewer.cpp"
    "${qgl_src}/quaternion.cpp"
    "${qgl_src}/saveSnapshot.cpp"
    "${qgl_src}/vec.cpp"
    "${CMAKE_CURRENT_BINARY_DIR}/ui_ImageInterface.h"
    ${qgl_generated})
target_include_directories(QGLViewer PRIVATE
    "${qgl_src}" "${CMAKE_CURRENT_BINARY_DIR}" ${qt_includes}
    "${GLU_INCLUDE_DIR}" "${MESA_INCLUDE_DIR}")
target_compile_definitions(QGLViewer PRIVATE NO_VECTORIAL_RENDER
    QT_CORE_LIB QT_GUI_LIB QT_WIDGETS_LIB QT_XML_LIB QT_OPENGL_LIB)
target_link_libraries(QGLViewer PRIVATE
    "${QT5_PREFIX}/lib/libQt5Core.so"
    "${QT5_PREFIX}/lib/libQt5Gui.so"
    "${QT5_PREFIX}/lib/libQt5Widgets.so"
    "${QT5_PREFIX}/lib/libQt5Xml.so"
    "${QT5_PREFIX}/lib/libQt5OpenGL.so"
    "${GLU_LIBRARY}" "${MESA_LIBRARY}")
set_target_properties(QGLViewer PROPERTIES
    VERSION 2.9.1 SOVERSION 2 OUTPUT_NAME "QGLViewer-qt5")

install(TARGETS QGLViewer LIBRARY DESTINATION lib)
install(FILES
    "${qgl_src}/qglviewer.h"
    "${qgl_src}/camera.h"
    "${qgl_src}/manipulatedFrame.h"
    "${qgl_src}/manipulatedCameraFrame.h"
    "${qgl_src}/frame.h"
    "${qgl_src}/constraint.h"
    "${qgl_src}/keyFrameInterpolator.h"
    "${qgl_src}/mouseGrabber.h"
    "${qgl_src}/quaternion.h"
    "${qgl_src}/vec.h"
    "${qgl_src}/domUtils.h"
    "${qgl_src}/config.h"
    DESTINATION include/QGLViewer)
