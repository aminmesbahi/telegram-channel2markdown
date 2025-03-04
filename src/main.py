from telethon.sync import TelegramClient
from telethon.tl.types import MessageEntityBold, MessageEntityItalic, MessageEntityTextUrl
import os
import re
import yaml
import json
from pathlib import Path
from typing import List, Dict, Set
import argparse
from openai import OpenAI
from datetime import datetime

# Configuration
CONFIG_FILE = 'config.yaml'
BASE_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = BASE_DIR / 'output'
MEDIA_DIR = OUTPUT_DIR / 'media'
HASHTAGS_JSON = OUTPUT_DIR / 'hashtags.json'
UNIQUE_HASHTAGS_FILE = OUTPUT_DIR / 'unique_hashtags.txt'

class Config:
    def __init__(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        MEDIA_DIR.mkdir(exist_ok=True)
        
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            self.data = yaml.safe_load(f)
        
        self.llm_client = None
        self.llm_service = self.data.get('llm_service', 'ollama')
        
        if self.llm_service == 'deepseek':
            self.llm_client = OpenAI(
                api_key=self.data.get('deepseek_api_key'),
                base_url="https://api.deepseek.com"
            )
        
        self.base_hashtags = self.load_base_hashtags()
        self.last_processed_id = self.load_last_processed()

    def load_base_hashtags(self) -> Set[str]:
        base_file = self.data.get('base_hashtags_file')
        if not base_file:
            return set()
        try:
            with open(base_file, 'r', encoding='utf-8') as f:
                return {line.strip().lower() for line in f if line.strip()}
        except FileNotFoundError:
            return set()

    def load_last_processed(self) -> int:
        if HASHTAGS_JSON.exists():
            with open(HASHTAGS_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return max(map(int, data.keys()), default=0)
        return 0

def sanitize_filename(text: str) -> str:
    return re.sub(r'[^\w\-_\. ]', '_', text.strip())[:50]

def convert_entities_to_markdown(text: str, entities) -> str:
    md_text = list(text)
    for entity in sorted(entities, key=lambda e: -e.offset):
        if isinstance(entity, MessageEntityBold):
            md = '**'
        elif isinstance(entity, MessageEntityItalic):
            md = '*'
        elif isinstance(entity, MessageEntityTextUrl):
            md = f'[{text[entity.offset:entity.offset+entity.length]}]({entity.url})'
            md_text[entity.offset:entity.offset+entity.length] = [''] * entity.length
            md_text.insert(entity.offset, md)
            continue
        else:
            continue
        md_text.insert(entity.offset + entity.length, md)
        md_text.insert(entity.offset, md)
    return ''.join(md_text)

def generate_hashtags(text: str, config: Config) -> List[str]:
    prompt = f"""
    Analyze this post and suggest 1-3 relevant hashtags. 
    Consider these base hashtags if relevant: {', '.join(config.base_hashtags)}
    Follow these rules:
    1. Use existing base hashtags when applicable
    2. Create new hashtags only when necessary
    3. Use lowercase with underscores
    4. Prioritize specificity
    
    Post content: {text[:2000]}
    
    Respond ONLY with comma-separated hashtags (e.g., #example1,#example2).
    """
    
    if config.llm_service == 'deepseek':
        response = config.llm_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=50
        )
        hashtags = response.choices[0].message.content.strip().split(',')
    else:
        hashtags = []  # Fallback if no LLM service
    
    processed = []
    for tag in hashtags:
        tag = tag.strip().lower().replace(' ', '_')
        if not tag.startswith('#'):
            tag = '#' + tag
        if tag in config.base_hashtags:
            processed.append(tag)
        else:
            processed.append(tag)
    
    return processed[:3]

def update_hashtag_data(post_id: int, hashtags: List[str], post_date: datetime):
    data = {}
    if HASHTAGS_JSON.exists():
        with open(HASHTAGS_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
    
    data[str(post_id)] = {
        'hashtags': hashtags,
        'date': post_date.isoformat(),
        'timestamp': datetime.now().isoformat()
    }
    
    with open(HASHTAGS_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    # Update unique hashtags
    unique = set()
    for entry in data.values():
        unique.update(entry['hashtags'])
    with open(UNIQUE_HASHTAGS_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(sorted(unique)))

async def process_message(client, message, config: Config, mode: str):
    text = message.text
    if not text:
        return
    
    # Save post content
    md_content = convert_entities_to_markdown(text, message.entities or [])
    date_str = message.date.strftime('%Y-%m-%d')
    filename = f"post_{message.id}__{date_str}.md"
    file_path = OUTPUT_DIR / filename
    file_path.write_text(md_content, encoding='utf-8')
    
    if mode == 'extract':
        hashtags = generate_hashtags(text, config)
        print(f"Post {message.id}: {hashtags}")
        update_hashtag_data(message.id, hashtags, message.date)
    elif mode == 'update':
        if message.id > config.last_processed_id:
            hashtags = generate_hashtags(text, config)
            new_text = f"{text}\n\n{' '.join(hashtags)}"
            await client.edit_message(message.peer_id, message.id, new_text)  # This needs async context
            update_hashtag_data(message.id, hashtags, message.date)

async def main(args):
    config = Config()
    async with TelegramClient('session', config.data['api_id'], config.data['api_hash']) as client:
        channel = await client.get_entity(config.data['channel_name'])
        
        async for message in client.iter_messages(channel, min_id=config.last_processed_id):
            if args.post_id and message.id != args.post_id:
                continue
            
            await process_message(client, message, config, args.mode)  # Proper async call
            
            if args.post_id:
                break

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Telegram Post Manager')
    parser.add_argument('mode', choices=['extract', 'update'], 
                      help='extract: save posts and hashtags, update: modify posts')
    parser.add_argument('--post-id', type=int, help='Process specific post')
    
    args = parser.parse_args()
    
    import asyncio
    asyncio.run(main(args))