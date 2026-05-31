# ======================================
# IMPORTS
# ======================================

import os
import subprocess
import json
import time
import threading
import shutil
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

# Flask imports
from flask import Flask, request, jsonify
import requests

# ======================================
# CONFIGURATION
# ======================================

# Get from environment variables (set in Render dashboard)
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
SAVE_DIR = os.getenv("SAVE_DIR", "/tmp/downloads")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB Telegram limit
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")  # Your Render app URL

# Ensure download directory exists
os.makedirs(SAVE_DIR, exist_ok=True)

# ======================================
# FLASK APP
# ======================================

app = Flask(__name__)

# ======================================
# TELEGRAM BOT FUNCTIONS
# ======================================

def send_message(chat_id, text, parse_mode="HTML"):
    """Send message to Telegram chat"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Error sending message: {e}")
        return None

def send_document(chat_id, file_path, caption=""):
    """Send document to Telegram chat"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    
    try:
        with open(file_path, 'rb') as file:
            files = {'document': file}
            payload = {
                'chat_id': chat_id,
                'caption': caption[:1024]  # Telegram caption limit
            }
            response = requests.post(url, files=files, data=payload, timeout=120)
            return response.json()
    except Exception as e:
        print(f"Error sending document: {e}")
        send_message(chat_id, f"❌ Error sending file: {str(e)}")
        return None

def send_audio(chat_id, file_path, caption="", title=None, performer=None):
    """Send audio file to Telegram chat"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio"
    
    try:
        with open(file_path, 'rb') as file:
            files = {'audio': file}
            payload = {
                'chat_id': chat_id,
                'caption': caption[:1024]
            }
            if title:
                payload['title'] = title[:64]
            if performer:
                payload['performer'] = performer[:64]
            
            response = requests.post(url, files=files, data=payload, timeout=120)
            return response.json()
    except Exception as e:
        print(f"Error sending audio: {e}")
        send_message(chat_id, f"❌ Error sending audio: {str(e)}")
        return None

def send_video(chat_id, file_path, caption="", thumb_path=None):
    """Send video file to Telegram chat"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    
    try:
        with open(file_path, 'rb') as file:
            files = {'video': file}
            payload = {
                'chat_id': chat_id,
                'caption': caption[:1024],
                'supports_streaming': True
            }
            if thumb_path and os.path.exists(thumb_path):
                files['thumb'] = open(thumb_path, 'rb')
            
            response = requests.post(url, files=files, data=payload, timeout=120)
            return response.json()
    except Exception as e:
        print(f"Error sending video: {e}")
        send_message(chat_id, f"❌ Error sending video: {str(e)}")
        return None

def send_photo(chat_id, photo_path, caption=""):
    """Send photo to Telegram chat"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    
    try:
        with open(photo_path, 'rb') as file:
            files = {'photo': file}
            payload = {
                'chat_id': chat_id,
                'caption': caption[:1024]
            }
            response = requests.post(url, files=files, data=payload, timeout=30)
            return response.json()
    except Exception as e:
        print(f"Error sending photo: {e}")
        return None

def edit_message(chat_id, message_id, text, parse_mode="HTML"):
    """Edit existing message"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Error editing message: {e}")
        return None

def answer_callback(callback_id, text=""):
    """Answer callback query"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    payload = {
        "callback_query_id": callback_id,
        "text": text
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Error answering callback: {e}")

def send_chat_action(chat_id, action="typing"):
    """Send chat action (typing, upload_document, etc.)"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendChatAction"
    payload = {
        "chat_id": chat_id,
        "action": action
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Error sending chat action: {e}")

def delete_message(chat_id, message_id):
    """Delete a message"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Error deleting message: {e}")

# ======================================
# YOUTUBE DOWNLOAD FUNCTIONS
# ======================================

def is_valid_url(url):
    """Check if URL is valid"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def get_video_info(url):
    """Get video information"""
    try:
        cmd = [
            "yt-dlp",
            "-j",
            "--no-playlist",
            "--no-warnings",
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
        return None
    except Exception as e:
        print(f"Error getting video info: {e}")
        return None

def get_playlist_info(url):
    """Get playlist information"""
    try:
        cmd = [
            "yt-dlp",
            "-j",
            "--flat-playlist",
            "--no-warnings",
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and result.stdout:
            videos = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    videos.append(json.loads(line))
            return videos
        return None
    except Exception as e:
        print(f"Error getting playlist info: {e}")
        return None

def format_duration(seconds):
    """Format duration in seconds to readable string"""
    if not seconds:
        return "Unknown"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"

def format_size(size_bytes):
    """Format bytes to human readable"""
    if not size_bytes:
        return "Unknown"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def download_video(url, format_type, quality, chat_id, message_id):
    """Download video/audio and send to user"""
    
    temp_dir = os.path.join(SAVE_DIR, str(chat_id), datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # Get video info first
        info = get_video_info(url)
        if not info:
            send_message(chat_id, "❌ Could not fetch video information. Check the URL.")
            return
        
        title = info.get('title', 'Unknown')[:100]
        duration = format_duration(info.get('duration'))
        uploader = info.get('uploader', 'Unknown')
        
        # Update status
        edit_message(chat_id, message_id, 
            f"📥 <b>Downloading:</b> {title}\n"
            f"⏱ <b>Duration:</b> {duration}\n"
            f"👤 <b>Uploader:</b> {uploader}\n\n"
            f"<i>Please wait...</i>")
        
        send_chat_action(chat_id, "upload_document")
        
        # Build command based on format
        output_template = os.path.join(temp_dir, "%(title)s.%(ext)s")
        
        if format_type == "audio":
            quality_map = {
                "best": "0",
                "320k": "0",
                "256k": "5",
                "192k": "7",
                "128k": "7"
            }
            
            cmd = [
                "yt-dlp",
                "--no-playlist",
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", quality_map.get(quality, "0"),
                "--embed-thumbnail",
                "--embed-metadata",
                "-o", output_template,
                url
            ]
            
            if quality == "320k":
                cmd.extend(["--postprocessor-args", "-b:a 320k"])
            elif quality == "256k":
                cmd.extend(["--postprocessor-args", "-b:a 256k"])
            elif quality == "192k":
                cmd.extend(["--postprocessor-args", "-b:a 192k"])
            elif quality == "128k":
                cmd.extend(["--postprocessor-args", "-b:a 128k"])
        
        else:  # video
            quality_map = {
                "best": "bestvideo+bestaudio/best",
                "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
                "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
                "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
                "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]"
            }
            
            cmd = [
                "yt-dlp",
                "--no-playlist",
                "-f", quality_map.get(quality, "best"),
                "--merge-output-format", "mp4",
                "--embed-metadata",
                "-o", output_template,
                url
            ]
        
        # Execute download
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            error_msg = result.stderr[:500] if result.stderr else "Unknown error"
            send_message(chat_id, f"❌ Download failed:\n<code>{error_msg}</code>")
            return
        
        # Find downloaded file
        downloaded_files = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(('.mp3', '.mp4', '.mkv', '.webm')):
                    downloaded_files.append(os.path.join(root, file))
        
        if not downloaded_files:
            send_message(chat_id, "❌ No files were downloaded")
            return
        
        # Send files
        for file_path in downloaded_files:
            file_size = os.path.getsize(file_path)
            
            if file_size > MAX_FILE_SIZE:
                send_message(chat_id, 
                    f"⚠️ File too large ({format_size(file_size)}).\n"
                    f"Telegram limit: 50MB\n"
                    f"Try lower quality or shorter video.")
                continue
            
            edit_message(chat_id, message_id, 
                f"📤 <b>Uploading:</b> {title}\n"
                f"📦 <b>Size:</b> {format_size(file_size)}\n\n"
                f"<i>Uploading to Telegram...</i>")
            
            send_chat_action(chat_id, "upload_document")
            
            if format_type == "audio":
                send_audio(chat_id, file_path, 
                    caption=f"🎵 {title}\n👤 {uploader}\n⏱ {duration}",
                    title=title,
                    performer=uploader)
            else:
                # Try to find thumbnail
                thumb_path = None
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file.endswith(('.jpg', '.webp')):
                            thumb_path = os.path.join(root, file)
                            break
                
                send_video(chat_id, file_path,
                    caption=f"🎬 {title}\n👤 {uploader}\n⏱ {duration}",
                    thumb_path=thumb_path)
            
            time.sleep(2)  # Avoid hitting rate limits
        
        # Send success message
        delete_message(chat_id, message_id)
        send_message(chat_id, 
            f"✅ <b>Download complete!</b>\n\n"
            f"📹 <b>Title:</b> {title}\n"
            f"👤 <b>Uploader:</b> {uploader}\n"
            f"⏱ <b>Duration:</b> {duration}")
        
    except subprocess.TimeoutExpired:
        send_message(chat_id, "❌ Download timed out")
    except Exception as e:
        send_message(chat_id, f"❌ Error: {str(e)}")
    finally:
        # Cleanup temp files
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass

def download_playlist(url, format_type, quality, chat_id, message_id):
    """Download playlist items and send to user"""
    
    temp_dir = os.path.join(SAVE_DIR, str(chat_id), f"playlist_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # Get playlist info
        videos = get_playlist_info(url)
        if not videos:
            send_message(chat_id, "❌ Could not fetch playlist information.")
            return
        
        total_videos = len(videos)
        if total_videos > 10:
            send_message(chat_id, 
                f"⚠️ Playlist has {total_videos} videos. "
                f"I'll download the first 10 to avoid timeouts.\n"
                f"Use a shorter playlist for more videos.")
            videos = videos[:10]
        
        edit_message(chat_id, message_id,
            f"📋 <b>Downloading Playlist:</b>\n"
            f"📹 <b>Videos:</b> {len(videos)}/{total_videos}\n\n"
            f"<i>This may take a while...</i>")
        
        send_chat_action(chat_id, "upload_document")
        
        # Download each video
        for i, video in enumerate(videos, 1):
            video_url = video.get('url') or f"https://youtube.com/watch?v={video.get('id')}"
            video_title = video.get('title', f'Video {i}')[:80]
            
            # Update progress
            edit_message(chat_id, message_id,
                f"📥 <b>Downloading:</b> {i}/{len(videos)}\n"
                f"📹 <b>Title:</b> {video_title}\n\n"
                f"<code>{'█' * (i * 20 // len(videos))}{'░' * (20 - i * 20 // len(videos))}</code>\n"
                f"<i>Progress: {i}/{len(videos)}</i>")
            
            # Download single video
            output_template = os.path.join(temp_dir, f"{i:03d}_%(title)s.%(ext)s")
            
            if format_type == "audio":
                cmd = [
                    "yt-dlp",
                    "--no-playlist",
                    "-x",
                    "--audio-format", "mp3",
                    "--audio-quality", "0",
                    "--embed-thumbnail",
                    "--embed-metadata",
                    "-o", output_template,
                    video_url
                ]
            else:
                cmd = [
                    "yt-dlp",
                    "--no-playlist",
                    "-f", quality if quality else "best",
                    "--merge-output-format", "mp4",
                    "--embed-metadata",
                    "-o", output_template,
                    video_url
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                continue
        
        # Send all downloaded files
        downloaded_files = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(('.mp3', '.mp4', '.mkv', '.webm')):
                    downloaded_files.append(os.path.join(root, file))
        
        downloaded_files.sort()  # Sort by filename (which includes index)
        
        edit_message(chat_id, message_id,
            f"📤 <b>Uploading:</b> {len(downloaded_files)} files\n\n"
            f"<i>Sending to Telegram...</i>")
        
        for file_path in downloaded_files:
            file_size = os.path.getsize(file_path)
            
            if file_size > MAX_FILE_SIZE:
                send_message(chat_id, 
                    f"⚠️ Skipping large file: {os.path.basename(file_path)} "
                    f"({format_size(file_size)})")
                continue
            
            send_chat_action(chat_id, "upload_document")
            
            if format_type == "audio":
                send_audio(chat_id, file_path)
            else:
                send_video(chat_id, file_path)
            
            time.sleep(1)  # Rate limit
        
        delete_message(chat_id, message_id)
        send_message(chat_id, 
            f"✅ <b>Playlist download complete!</b>\n"
            f"📹 <b>Files sent:</b> {len(downloaded_files)}")
        
    except Exception as e:
        send_message(chat_id, f"❌ Error: {str(e)}")
    finally:
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass

# ======================================
# KEYBOARD BUILDERS
# ======================================

def build_main_keyboard():
    """Build main menu keyboard"""
    keyboard = {
        "inline_keyboard": [
            [{"text": "🎵 Download Audio", "callback_data": "menu_audio"}],
            [{"text": "🎬 Download Video", "callback_data": "menu_video"}],
            [{"text": "📋 Download Playlist", "callback_data": "menu_playlist"}],
            [{"text": "ℹ️ Help", "callback_data": "menu_help"}]
        ]
    }
    return keyboard

def build_quality_keyboard(format_type):
    """Build quality selection keyboard"""
    if format_type == "audio":
        keyboard = {
            "inline_keyboard": [
                [{"text": "🎵 Best Quality (320kbps)", "callback_data": f"dl_audio_best"}],
                [{"text": "🎵 High (256kbps)", "callback_data": f"dl_audio_256k"}],
                [{"text": "🎵 Medium (192kbps)", "callback_data": f"dl_audio_192k"}],
                [{"text": "🎵 Standard (128kbps)", "callback_data": f"dl_audio_128k"}],
                [{"text": "🔙 Back", "callback_data": "menu_back"}]
            ]
        }
    else:
        keyboard = {
            "inline_keyboard": [
                [{"text": "🎯 Best Quality", "callback_data": f"dl_video_best"}],
                [{"text": "📺 1080p", "callback_data": f"dl_video_1080p"}],
                [{"text": "📱 720p", "callback_data": f"dl_video_720p"}],
                [{"text": "📱 480p", "callback_data": f"dl_video_480p"}],
                [{"text": "📱 360p", "callback_data": f"dl_video_360p"}],
                [{"text": "🔙 Back", "callback_data": "menu_back"}]
            ]
        }
    return keyboard

# ======================================
# COMMAND HANDLERS
# ======================================

def handle_start(chat_id, user_first_name):
    """Handle /start command"""
    welcome_text = (
        f"👋 <b>Welcome {user_first_name}!</b>\n\n"
        f"🎬 <b>YouTube Downloader Bot</b>\n\n"
        f"<b>Features:</b>\n"
        f"• 🎵 Download YouTube audio as MP3\n"
        f"• 🎬 Download YouTube videos\n"
        f"• 📋 Download entire playlists\n"
        f"• 🏷️ High quality with metadata\n\n"
        f"<b>How to use:</b>\n"
        f"1. Send me a YouTube link\n"
        f"2. Choose format (audio/video)\n"
        f"3. Select quality\n"
        f"4. Wait for your download!\n\n"
        f"<i>Send /help for more information.</i>"
    )
    
    send_message(chat_id, welcome_text, reply_markup=build_main_keyboard())

def handle_help(chat_id):
    """Handle /help command"""
    help_text = (
        f"📖 <b>Help Guide</b>\n\n"
        f"<b>Available Commands:</b>\n"
        f"/start - Start the bot\n"
        f"/help - Show this help\n"
        f"/about - About the bot\n\n"
        f"<b>How to Download:</b>\n\n"
        f"1️⃣ <b>Send a YouTube URL</b>\n"
        f"Simply paste any YouTube link\n\n"
        f"2️⃣ <b>Choose Format</b>\n"
        f"Select Audio or Video\n\n"
        f"3️⃣ <b>Select Quality</b>\n"
        f"Choose your preferred quality\n\n"
        f"4️⃣ <b>Get Your File</b>\n"
        f"Wait for download and upload\n\n"
        f"<b>Tips:</b>\n"
        f"• For best audio, choose 320kbps\n"
        f"• Large files may take time\n"
        f"• Playlists limited to 10 videos\n"
        f"• Max file size: 50MB\n\n"
        f"<b>Supported Platforms:</b>\n"
        f"YouTube, YouTube Music, and more!"
    )
    send_message(chat_id, help_text)

def handle_about(chat_id):
    """Handle /about command"""
    about_text = (
        f"🤖 <b>YouTube Downloader Bot</b>\n\n"
        f"<b>Version:</b> 2.0\n"
        f"<b>Powered by:</b> yt-dlp\n"
        f"<b>Hosted on:</b> Render\n\n"
        f"<b>Features:</b>\n"
        f"• High-quality audio (320kbps)\n"
        f"• Video up to 1080p\n"
        f"• Playlist support\n"
        f"• Metadata embedding\n\n"
        f"<i>Created with ❤️ using Python</i>"
    )
    send_message(chat_id, about_text)

# ======================================
# URL PROCESSING
# ======================================

# Store user states temporarily
user_states = {}

def process_url(chat_id, url):
    """Process a YouTube URL"""
    if not is_valid_url(url):
        send_message(chat_id, "❌ Invalid URL. Please send a valid YouTube link.")
        return
    
    # Check if URL is playlist
    is_playlist = "playlist" in url.lower() or "&list=" in url
    
    # Store URL in user state
    user_states[chat_id] = {
        "url": url,
        "is_playlist": is_playlist,
        "timestamp": time.time()
    }
    
    # Get info
    if is_playlist:
        videos = get_playlist_info(url)
        if videos:
            count = len(videos)
            text = (
                f"📋 <b>Playlist Detected!</b>\n\n"
                f"📹 <b>Videos:</b> {count}\n"
                f"ℹ️ Max 10 will be downloaded\n\n"
                f"<b>Choose download format:</b>"
            )
        else:
            text = "❌ Could not fetch playlist info."
    else:
        info = get_video_info(url)
        if info:
            title = info.get('title', 'Unknown')[:80]
            duration = format_duration(info.get('duration'))
            uploader = info.get('uploader', 'Unknown')
            
            text = (
                f"📹 <b>Video Found!</b>\n\n"
                f"<b>Title:</b> {title}\n"
                f"<b>Duration:</b> {duration}\n"
                f"<b>Uploader:</b> {uploader}\n\n"
                f"<b>Choose download format:</b>"
            )
        else:
            text = "❌ Could not fetch video info."
    
    # Send format selection keyboard
    keyboard = {
        "inline_keyboard": [
            [{"text": "🎵 Download as Audio", "callback_data": "format_audio"}],
            [{"text": "🎬 Download as Video", "callback_data": "format_video"}],
            [{"text": "❌ Cancel", "callback_data": "menu_cancel"}]
        ]
    }
    
    send_message(chat_id, text, reply_markup=keyboard)

# ======================================
# CALLBACK HANDLER
# ======================================

def handle_callback(callback):
    """Handle inline keyboard callbacks"""
    callback_id = callback.get('id')
    chat_id = callback['message']['chat']['id']
    message_id = callback['message']['message_id']
    data = callback.get('data', '')
    
    # Answer callback to remove loading state
    answer_callback(callback_id)
    
    # Main menu callbacks
    if data == "menu_back":
        send_message(chat_id, "🏠 <b>Main Menu</b>", reply_markup=build_main_keyboard())
        delete_message(chat_id, message_id)
    
    elif data == "menu_cancel":
        delete_message(chat_id, message_id)
        if chat_id in user_states:
            del user_states[chat_id]
    
    elif data == "menu_audio":
        # Prompt for URL
        msg = send_message(chat_id, 
            "🎵 <b>Audio Download</b>\n\n"
            "Send me a YouTube URL to download as audio.")
        # Store that we're waiting for audio URL
        user_states[chat_id] = {"waiting_for": "audio_url", "timestamp": time.time()}
        delete_message(chat_id, message_id)
    
    elif data == "menu_video":
        msg = send_message(chat_id,
            "🎬 <b>Video Download</b>\n\n"
            "Send me a YouTube URL to download as video.")
        user_states[chat_id] = {"waiting_for": "video_url", "timestamp": time.time()}
        delete_message(chat_id, message_id)
    
    elif data == "menu_playlist":
        msg = send_message(chat_id,
            "📋 <b>Playlist Download</b>\n\n"
            "Send me a YouTube playlist URL.")
        user_states[chat_id] = {"waiting_for": "playlist_url", "timestamp": time.time()}
        delete_message(chat_id, message_id)
    
    elif data == "menu_help":
        handle_help(chat_id)
        delete_message(chat_id, message_id)
    
    # Format selection
    elif data == "format_audio":
        if chat_id in user_states:
            user_states[chat_id]['format'] = 'audio'
            edit_message(chat_id, message_id,
                "🎵 <b>Select Audio Quality:</b>",
                reply_markup=build_quality_keyboard("audio"))
    
    elif data == "format_video":
        if chat_id in user_states:
            user_states[chat_id]['format'] = 'video'
            edit_message(chat_id, message_id,
                "🎬 <b>Select Video Quality:</b>",
                reply_markup=build_quality_keyboard("video"))
    
    # Download callbacks
    elif data.startswith("dl_"):
        if chat_id not in user_states or 'url' not in user_states[chat_id]:
            answer_callback(callback_id, "Session expired. Please send URL again.")
            delete_message(chat_id, message_id)
            return
        
        parts = data.split('_')
        format_type = parts[1]  # audio or video
        quality = parts[2] if len(parts) > 2 else "best"
        
        url = user_states[chat_id]['url']
        is_playlist = user_states[chat_id].get('is_playlist', False)
        
        # Start download in background thread
        edit_message(chat_id, message_id, 
            f"⏳ <b>Starting download...</b>\n\n"
            f"<i>Please wait...</i>")
        
        if is_playlist:
            thread = threading.Thread(
                target=download_playlist,
                args=(url, format_type, quality, chat_id, message_id)
            )
        else:
            thread = threading.Thread(
                target=download_video,
                args=(url, format_type, quality, chat_id, message_id)
            )
        thread.start()
        
        # Clean up state
        if chat_id in user_states:
            del user_states[chat_id]

# ======================================
# WEBHOOK ENDPOINT
# ======================================

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming updates from Telegram"""
    try:
        update = request.get_json()
        
        # Handle message
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            
            # Handle text messages
            if 'text' in message:
                text = message['text'].strip()
                
                # Commands
                if text == '/start':
                    handle_start(chat_id, message['from'].get('first_name', 'User'))
                
                elif text == '/help':
                    handle_help(chat_id)
                
                elif text == '/about':
                    handle_about(chat_id)
                
                # Check if waiting for URL
                elif chat_id in user_states and user_states[chat_id].get('waiting_for'):
                    waiting_for = user_states[chat_id]['waiting_for']
                    
                    if is_valid_url(text):
                        process_url(chat_id, text)
                    else:
                        send_message(chat_id, "❌ Invalid URL. Please send a valid YouTube link.")
                    
                    # Clear waiting state
                    if chat_id in user_states:
                        del user_states[chat_id]
                
                # Default: treat as URL
                elif is_valid_url(text):
                    process_url(chat_id, text)
                
                else:
                    send_message(chat_id, 
                        "Please send a valid YouTube URL or use /start to begin.",
                        reply_markup=build_main_keyboard())
        
        # Handle callback queries
        elif 'callback_query' in update:
            handle_callback(update['callback_query'])
        
        return jsonify({"status": "ok"})
    
    except Exception as e:
        print(f"Error in webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/')
def index():
    """Health check endpoint"""
    return jsonify({
        "status": "running",
        "bot": "YouTube Downloader",
        "version": "2.0"
    })

# ======================================
# SETUP WEBHOOK
# ======================================

def setup_webhook():
    """Setup Telegram webhook"""
    if not WEBHOOK_URL:
        print("WEBHOOK_URL not set. Skipping webhook setup.")
        return
    
    webhook_endpoint = f"{WEBHOOK_URL}/webhook"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    payload = {"url": webhook_endpoint}
    
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        if result.get('ok'):
            print(f"Webhook set to: {webhook_endpoint}")
        else:
            print(f"Failed to set webhook: {result}")
    except Exception as e:
        print(f"Error setting webhook: {e}")

# ======================================
# MAIN
# ======================================

if __name__ == "__main__":
    # Verify bot token
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("ERROR: Please set your BOT_TOKEN environment variable!")
        exit(1)
    
    # Setup webhook
    setup_webhook()
    
    # Start Flask server
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
