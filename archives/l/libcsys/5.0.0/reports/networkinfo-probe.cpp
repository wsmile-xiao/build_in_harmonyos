// Root-cause probe for the NetworkInfo::getIOBytes() SIGSEGV (libcsys 5.0.0).
//
// Replicates BOTH parse implementations verbatim and runs them over crafted
// /proc/net/dev inputs, so the undefined-behaviour paths can be observed
// (QList::removeFirst() on an empty list, QList::at() out of range).
//
//   ./probe <input-file> old     -> upstream 5.0.0 logic
//   ./probe <input-file> new     -> patched logic
//
// Usage is read-only: it never touches the real /proc/net/dev.
#include <QCoreApplication>
#include <QDebug>
#include <QFile>
#include <QList>
#include <QRegularExpression>
#include <QString>
#include <QStringList>
#include <QTextStream>

static QStringList readListFromFileLikeUpstream(const QString& path)
{
	QFile file(path);
	QString data;
	if (file.open(QIODevice::ReadOnly)) {
		QTextStream out(&file);
		data = out.readAll();
		file.close();
	}
	QString fileStr = data.trimmed();
	if (fileStr.length())
		return fileStr.split("\n");
	return QStringList();
}

static QList<quint64> oldLogic(const QString& path)
{
	QList<quint64> iobytes;
	iobytes << 0 << 0;

	QStringList data = readListFromFileLikeUpstream(path);

	// ── upstream 5.0.0, verbatim ──
	data.removeFirst();
	data.removeFirst();
	data.removeFirst();

	Q_FOREACH (QString line, data) {
		QStringList bytes = line.trimmed().split(QRegularExpression("\\s+"));
		iobytes[0] += bytes.at(1).toULongLong();
		iobytes[1] += bytes.at(9).toULongLong();
	}
	return iobytes;
}

static QList<quint64> newLogic(const QString& path)
{
	QList<quint64> iobytes;
	iobytes << 0 << 0;

	QStringList data = readListFromFileLikeUpstream(path);

	// ── patched logic ──
	Q_FOREACH (QString line, data) {
		QString row = line.trimmed();
		if (!row.contains(':'))
			continue;
		QStringList bytes = row.split(QRegularExpression("\\s+"));
		if (bytes.size() < 10)
			continue;
		iobytes[0] += bytes.at(1).toULongLong();
		iobytes[1] += bytes.at(9).toULongLong();
	}
	return iobytes;
}

int main(int argc, char** argv)
{
	QCoreApplication app(argc, argv);
	if (argc < 3) {
		qInfo() << "usage: probe <file> old|new";
		return 2;
	}
	QString path = QString::fromLocal8Bit(argv[1]);
	QString mode = QString::fromLocal8Bit(argv[2]);
	QList<quint64> r = (mode == "old") ? oldLogic(path) : newLogic(path);
	qInfo().noquote() << QString("RESULT rx=%1 tx=%2").arg(r.at(0)).arg(r.at(1));
	return 0;
}
