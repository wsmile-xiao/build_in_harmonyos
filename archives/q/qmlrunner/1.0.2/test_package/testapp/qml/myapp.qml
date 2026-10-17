import QtQuick 2.0
import QtQuick.Window 2.0

Window {
    visible: true
    width: 320
    height: 200
    title: "qmlrunner consumer test"

    Timer {
        interval: 300
        running: true
        repeat: false
        onTriggered: Qt.quit()
    }
}
