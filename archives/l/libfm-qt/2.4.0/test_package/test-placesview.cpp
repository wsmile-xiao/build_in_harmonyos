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
// Adapted from upstream src/tests/test-placesview.cpp:
// - replaced relative includes with installed <libfm-qt6/...> headers
// - original blocked on app.exec() with no auto-quit; added QTimer auto-quit
//   so it can run headless (offscreen)
#include <QApplication>
#include <QMainWindow>
#include <QTimer>
#include <QDir>
#include <QDebug>
#include <libfm-qt6/placesview.h>
#include <libfm-qt6/libfmqt.h>

int main(int argc, char** argv) {
    QApplication app(argc, argv);

    Fm::LibFmQt contex;
    QMainWindow win;

    Fm::PlacesView view;
    win.setCentralWidget(&view);

    win.show();
    QTimer::singleShot(500, &app, &QApplication::quit);
    app.exec();
    return 0;
}
