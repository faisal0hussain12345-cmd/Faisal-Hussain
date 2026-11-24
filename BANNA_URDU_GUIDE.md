# BANNA — استعمال کی اردو رہنمائی

## سافٹ ویئر کیا کرتا ہے؟
BANNA آپ کی تیار شدہ وائس اوور MP3/WAV کو بنیاد بنا کر 1920×1080، 30 FPS ڈاکیومنٹری MP4 تیار کرتا ہے۔ ویڈیو میں اصل stock video clips استعمال نہیں ہوتے؛ صرف still photographs، generated still illustrations، animated evidence-board camera movement، maps اور vintage 2D inserts استعمال ہوتے ہیں۔

## API Key محفوظ طریقے سے شامل کرنا
1. GitHub پر BANNA repository کھولیں۔
2. **Settings → Secrets and variables → Actions** کھولیں۔
3. **New repository secret** منتخب کریں۔
4. نام میں بالکل یہ لکھیں: `GEMINI_API_KEY`
5. اپنی Gemini API key کو Value میں ڈال کر Save کریں۔

API key کو Python فائل، README، یا Git commit میں نہ لکھیں اور چیٹ میں بھی نہ بھیجیں۔

## ڈاکیومنٹری تیار کرنے کا طریقہ
1. ChatGPT میں `Use BANNA` لکھیں۔ Audience، زبان، category اور duration منتخب کریں۔
2. BANNA پہلے تحقیق، حقائق اور narration script تیار کرے گا۔
3. اپنی مکمل voice-over MP3/WAV فراہم کریں۔
4. منظور شدہ visual storyboard تیار ہونے کے بعد GitHub Actions میں **BANNA Documentary Render** کھولیں۔
5. **Run workflow** دبائیں اور story-specific `storyboard.json` منتخب کریں۔
6. کامیاب render کے بعد workflow کے **Artifacts** سے MP4، QC contact sheet، QC report اور word timing report حاصل کریں۔

## ویڈیو کی مقررہ حدیں
- 60 سیکنڈ سے 20 منٹ تک
- 1920×1080
- 30 FPS
- وائس اوور کا دورانیہ final video کا master duration ہوگا
- دو cloud workers سے parallel visual rendering

## پانچ visual surfaces
- `map_board`
- `paper_press`
- `scrapbook_dossier`
- `chalk_case_board`
- `digital_coda`

یہ surface منتخب شدہ story کے انداز کے مطابق `storyboard.json` کے `project.surface` میں درج ہوگی۔

## اہم نوٹ
GitHub Actions اور Gemini API کی free quota، rate limits، runtime اور storage کی حدیں ان کے متعلقہ plans پر منحصر ہیں۔ BANNA لامحدود مفت استعمال کی ضمانت نہیں دیتا۔ حقیقی image generation کے لیے فعال Gemini API access ضروری ہے۔
