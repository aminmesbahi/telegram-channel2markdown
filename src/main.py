from telethon.sync import TelegramClient
from telethon.tl.types import MessageEntityBold, MessageEntityItalic, MessageEntityTextUrl
import os
import re

# Configuration
API_ID = 'YOUR_API_ID'  # Replace with your API ID
API_HASH = 'YOUR_API_HASH'  # Replace with your API Hash
CHANNEL_NAME = 'YOUR_CHANNEL_USERNAME'  # e.g., @my_channel
OUTPUT_DIR = 'output'  # Directory to save Markdown files
MEDIA_DIR = os.path.join(OUTPUT_DIR, 'media')  # Directory for downloaded media

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(MEDIA_DIR, exist_ok=True)

def sanitize_filename(text):
    """Clean text to create safe filenames."""
    return re.sub(r'[^\w\-_\. ]', '_', text.strip())[:50]

def convert_entities_to_markdown(text, entities):
    """Convert Telegram message entities to Markdown."""
    md_text = list(text)
    # Process entities in reverse order to avoid offset issues
    for entity in sorted(entities, key=lambda e: -e.offset):
        if isinstance(entity, MessageEntityBold):
            md = '**'
        elif isinstance(entity, MessageEntityItalic):
            md = '*'
        elif isinstance(entity, MessageEntityTextUrl):
            md = f'[{text[entity.offset:entity.offset+entity.length]}]({entity.url})'
            # Replace the original text with the markdown link
            md_text[entity.offset:entity.offset+entity.length] = ['' for _ in range(entity.length)]
            md_text.insert(entity.offset, md)
            continue
        else:
            continue  # Handle other entities (e.g., URLs) as needed
        # Insert markdown at offsets
        md_text.insert(entity.offset + entity.length, md)
        md_text.insert(entity.offset, md)
    return ''.join(md_text)

async def main():
    async with TelegramClient('session_name', API_ID, API_HASH) as client:
        channel = await client.get_entity(CHANNEL_NAME)
        async for message in client.iter_messages(channel):
            if not message.text:
                continue
            # Process text and entities
            text = message.text
            entities = message.entities or []
            md_content = convert_entities_to_markdown(text, entities)
            # Download media (if any)
            media_path = None
            if message.media:
                media_path = await client.download_media(message.media, file=MEDIA_DIR)
            # Add media link to Markdown
            if media_path:
                md_content += f'\n\n![Media]({os.path.relpath(media_path, OUTPUT_DIR)})'
            # Generate filename (using date + first few words)
            date = message.date.strftime('%Y-%m-%d_%H-%M')
            sanitized_text = sanitize_filename(text[:30])
            filename = f"{date}_{sanitized_text}.md".replace(' ', '_')
            # Save to file
            with open(os.path.join(OUTPUT_DIR, filename), 'w', encoding='utf-8') as f:
                f.write(md_content)
            print(f"Saved: {filename}")

import asyncio
asyncio.run(main())