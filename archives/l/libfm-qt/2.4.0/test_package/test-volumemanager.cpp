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
// Adapted from upstream src/tests/test-volumemanager.cpp:
// - replaced relative includes with installed <libfm-qt6/...> headers
// - original blocked on app.exec() with no auto-quit; added QTimer auto-quit
//   and a non-null check so it can run headless (offscreen)
#include <QApplication>
#include <QTimer>
#include <QDir>
#include <QDebug>
#include <libfm-qt6/core/volumemanager.h>

int main(int argc, char** argv) {
    QApplication app(argc, argv);
    int rc = 0;

    auto vm = Fm::VolumeManager::globalInstance();
    if(!vm) {
        qWarning("FAIL: VolumeManager::globalInstance() returned null");
        rc = 1;
    }
    else {
        QObject::connect(vm.get(), &Fm::VolumeManager::volumeAdded, [=](const Fm::Volume& vol) {
            qDebug() << "volume added:" << vol.name().get();
        });
        QObject::connect(vm.get(), &Fm::VolumeManager::volumeRemoved, [=](const Fm::Volume& vol) {
            qDebug() << "volume removed:" << vol.name().get();
        });

        for(auto& item : vm->volumes()) {
            auto name = item.name();
            qDebug() << "list volume:" << name.get();
        }
    }

    QTimer::singleShot(500, &app, &QApplication::quit);
    app.exec();
    return rc;
}
