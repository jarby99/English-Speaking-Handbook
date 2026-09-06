# 泰语点读练习 App

这是一个静态 App，用本地数据和本地预生成 MP3 音频做泰语点读练习。

打开 `index.html` 即可使用。

数据来源：`learning-records/thai/*.md`，不包含 `learning-records/thai/TikTok/`。

重新生成数据和音频：

```powershell
python tools/build_thai_audio_app_assets.py
```

## 安卓安装包

GitHub Actions 会生成 `thai-audio-practice-release-apk`。

从旧的 debug 测试包切换到 release 包时，安卓可能要求先卸载一次旧版本。之后继续安装 GitHub Actions 新生成的 release APK 时，会使用同一个签名和递增版本号，可以直接覆盖更新。
