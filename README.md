# telegram-channel2markdown
Python script to extract markdown files, from a Telegram channel's posts

## 1. Set Up Telegram API Credentials
- Go to [my.telegram.org](https://my.telegram.org) and create an app.

- Note your API ID and API Hash.

## 2. Install requirements

```bash
pip install -r requirements.txt
```
## 3. Run the code
```bash
python3 main.py
```

## Key Features:
- **Markdown Conversion:** Handles bold, italic, and links from Telegram entities.

- **Media Handling:** Downloads images/files to a media subfolder and links them in Markdown.

- **Sanitized Filenames:** Uses timestamps and message snippets for filenames.

## Notes:
- **First Run:** You’ll be prompted to log in with your Telegram account.

- **Rate Limits:** Telethon handles Telegram’s API rate limits automatically.

- **Extended Formatting:** Add more entity handlers (e.g., MessageEntityCode) as needed.

