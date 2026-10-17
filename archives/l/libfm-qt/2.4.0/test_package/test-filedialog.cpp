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
// Adapted from upstream src/tests/test-filedialog.cpp:
// - replaced relative includes with installed <libfm-qt6/...> headers
// - the original blocked on dlg.exec() (interactive dialog); adapted to
//   show() + QTimer auto-quit so it can run headless (offscreen)
#include <QApplication>
#include <QMainWindow>
#include <QToolBar>
#include <QTimer>
#include <QDebug>
#include <libfm-qt6/core/folder.h>
#include <libfm-qt6/foldermodel.h>
#include <libfm-qt6/folderview.h>
#include <libfm-qt6/cachedfoldermodel.h>
#include <libfm-qt6/proxyfoldermodel.h>
#include <libfm-qt6/pathedit.h>
#include <libfm-qt6/filedialog.h>
#include <libfm-qt6/libfmqt.h>


int main(int argc, char** argv) {
    QApplication app(argc, argv);
    int rc = 0;

    Fm::LibFmQt contex;

    Fm::FileDialog dlg;
    dlg.setFileMode(QFileDialog::ExistingFiles);
    dlg.setNameFilters(QStringList() << QStringLiteral("All (*)")
                                     << QStringLiteral("Text (*.txt)")
                                     << QStringLiteral("Images (*.gif *.jpeg *.jpg)"));

    // Verify the dialog object was constructed and configured.
    if(dlg.fileMode() != QFileDialog::ExistingFiles) {
        qWarning("FAIL: FileDialog::setFileMode did not stick");
        rc = 1;
    }

    dlg.show();
    QTimer::singleShot(500, &app, &QApplication::quit);
    app.exec();
    qDebug() << "selected files:" << dlg.selectedFiles();

    return rc;
}
