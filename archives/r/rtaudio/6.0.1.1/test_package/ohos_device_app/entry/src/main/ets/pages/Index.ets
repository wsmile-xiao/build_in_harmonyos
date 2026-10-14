import { hilog } from '@kit.PerformanceAnalysisKit';
import { abilityAccessCtrl, common } from '@kit.AbilityKit';
import rtaudioTest from 'libentry.so';

const DOMAIN = 0xD001;

@Entry
@Component
struct Index {
  @State result: string = 'Preparing microphone permission request…';

  async aboutToAppear(): Promise<void> {
    const runId = `${Date.now()}-${Math.floor(Math.random() * 1000000)}`;
    const context = getContext(this) as common.UIAbilityContext;
    hilog.info(DOMAIN, 'RTAudioOHAudioTest',
      'RTAUDIO_DEVICE_TEST_ID=%{public}s MICROPHONE_PERMISSION_REQUESTED', runId);
    try {
      const permission = await abilityAccessCtrl.createAtManager().requestPermissionsFromUser(
        context, ['ohos.permission.MICROPHONE']);
      if (!permission.authResults.length || permission.authResults[0] !== 0) {
        this.result = 'Microphone permission is required to run the input and duplex tests.';
        hilog.error(DOMAIN, 'RTAudioOHAudioTest',
          'RTAUDIO_DEVICE_TEST_ID=%{public}s MICROPHONE_PERMISSION_DENIED', runId);
        return;
      }
      this.result = 'Running 27 upstream checks and 2 HarmonyOS device checks…';
      const report = await rtaudioTest.runSuite(runId, context.cacheDir);
      const lines = report.split('\n').filter((line: string): boolean => line.length > 0);
      for (const line of lines) {
        hilog.info(DOMAIN, 'RTAudioOHAudioTest',
          'RTAUDIO_DEVICE_TEST_ID=%{public}s %{public}s', runId, line);
      }
      this.result = lines.length ? lines[lines.length - 1] : 'The device suite returned no results.';
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      this.result = `RTAUDIO_DEVICE_TEST_ID=${runId} OHOS_SUITE_FAIL: ${message}`;
      hilog.error(DOMAIN, 'RTAudioOHAudioTest', '%{public}s', this.result);
    }
  }

  build() {
    Column() {
      Text(this.result).fontSize(16)
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center)
  }
}
