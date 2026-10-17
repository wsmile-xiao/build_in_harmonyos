/*
 * Copyright (C) 2017  Hong Jen Yee (PCMan) <pcman.tw@gmail.com>
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
 *
 */
// Adapted from upstream src/tests/test-folder.cpp:
// - replaced relative includes with installed <libfm-qt6/...> headers
// - added QTimer auto-quit + result code so it runs headless (offscreen)
#include <QApplication>
#include <QDebug>
#include <QTimer>
#include <libfm-qt6/core/folder.h>

int main(int argc, char** argv) {
    QApplication app(argc, argv);
    int rc = 0;

    auto home = Fm::FilePath::homeDir();
    auto folder = Fm::Folder::fromPath(home);
    if(!folder) {
        qWarning("FAIL: Folder::fromPath(homeDir()) returned null");
        rc = 1;
    }
    else {
        qDebug() << "home dir:" << home.toString().get();
        for(auto& item : folder->files()) {
            // FileInfo::displayName() returns const QString& in 2.4.0
            qDebug() << item->displayName();
        }
    }

    QTimer::singleShot(500, &app, &QApplication::quit);
    app.exec();
    return rc;
}
