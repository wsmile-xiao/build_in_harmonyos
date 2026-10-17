import qt6UidProbe from 'libqt6uidprobe.so';

@Entry
@Component
struct Index {
  @State fullServerName: string = '';
  @State report: string = 'Start a native abstract AF_UNIX listener here, then connect to it from SSH.';

  build() {
    Column({ space: 16 }) {
      Text('Qt 6 HarmonyOS cross-UID probe')
        .fontSize(24)
        .fontWeight(FontWeight.Bold)
      Text('This app can probe an SSH Qt server or expose a raw listener for a reverse-direction UID check.')
        .fontSize(16)
      Button('Start app-UID raw listener')
        .onClick(() => {
          try {
            this.report = qt6UidProbe.startServer();
          } catch (error) {
            this.report = `INCONCLUSIVE: native listener threw ${JSON.stringify(error)}`;
          }
        })
      Button('Refresh app listener status')
        .onClick(() => {
          try {
            this.report = qt6UidProbe.serverStatus();
          } catch (error) {
            this.report = `INCONCLUSIVE: status query threw ${JSON.stringify(error)}`;
          }
        })
      Button('Stop app listener')
        .onClick(() => {
          this.report = qt6UidProbe.stopServer();
        })
      Button('Start Qt QLocalServer')
        .onClick(() => {
          try {
            this.report = qt6UidProbe.startQtServer();
          } catch (error) {
            this.report = `INCONCLUSIVE: Qt server threw ${JSON.stringify(error)}`;
          }
        })
      Button('Refresh Qt server status')
        .onClick(() => {
          try {
            this.report = qt6UidProbe.qtServerStatus();
          } catch (error) {
            this.report = `INCONCLUSIVE: Qt server status threw ${JSON.stringify(error)}`;
          }
        })
      Button('Stop Qt QLocalServer')
        .onClick(() => {
          this.report = qt6UidProbe.stopQtServer();
        })
      Text('To test an SSH Qt server, paste its SERVER_FULL_NAME below.')
        .fontSize(14)
      TextInput({ text: this.fullServerName, placeholder: '@qt6:<server-uid>:<sha256>' })
        .width('100%')
        .onChange((value: string) => {
          this.fullServerName = value.trim();
        })
      Button('Probe raw AF_UNIX socket')
        .onClick(() => {
          if (this.fullServerName.length === 0) {
            this.report = 'INCONCLUSIVE: enter SERVER_FULL_NAME first.';
            return;
          }
          try {
            this.report = qt6UidProbe.probe(
              this.fullServerName,
              'QT6-HARMONYOS-CROSS-UID-PROBE-2026'
            );
          } catch (error) {
            this.report = `INCONCLUSIVE: native probe threw ${JSON.stringify(error)}`;
          }
        })
      Button('Probe Qt QLocalSocket')
        .onClick(() => {
          if (this.fullServerName.length === 0) {
            this.report = 'INCONCLUSIVE: enter SERVER_FULL_NAME first.';
            return;
          }
          try {
            this.report = qt6UidProbe.qtProbe(
              this.fullServerName,
              'QT6-HARMONYOS-QLocalSocket-CROSS-UID-PROBE-2026'
            );
          } catch (error) {
            this.report = `INCONCLUSIVE: Qt local socket probe threw ${JSON.stringify(error)}`;
          }
        })
      Text(this.report)
        .fontSize(14)
        .width('100%')
        .textAlign(TextAlign.Start)
    }
    .padding(24)
    .width('100%')
    .height('100%')
  }
}
