# 泰语点读练习 App

这是一个静态 App，用本地数据和本地预生成 MP3 音频做泰语点读练习。

打开 `index.html` 即可使用。

数据来源：`learning-records/thai/*.md`，不包含 `learning-records/thai/TikTok/`。

重新生成数据和音频：

```powershell
python tools/build_thai_audio_app_assets.py
```
