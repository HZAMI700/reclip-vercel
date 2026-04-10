import os
import yt_dlp
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# Check if cookies.txt exists in the root directory
COOKIES_FILE = os.path.join(os.path.dirname(__file__), "cookies.txt")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/info", methods=["POST"])
def get_info():
    data = request.json
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extractor_args': {'youtube': ['player_client=android,ios,web']}
    }
    
    if os.path.exists(COOKIES_FILE):
        ydl_opts['cookiefile'] = COOKIES_FILE
    
    try:
        # TIKTOK BYPASS
        if "tiktok.com" in url:
            import urllib.request, urllib.parse, json
            req = urllib.request.Request("https://tikwm.com/api/", data=urllib.parse.urlencode({"url": url, "hd": 1}).encode(), headers={"User-Agent": "Mozilla/5.0"})
            resp = json.loads(urllib.request.urlopen(req).read().decode())
            data = resp.get("data", {})
            return jsonify({
                "title": data.get("title", "TikTok Video"),
                "thumbnail": data.get("origin_cover", ""),
                "duration": data.get("duration", 0),
                "uploader": data.get("author", {}).get("unique_id", ""),
                "formats": [
                    {"id": "video", "label": "Video (MP4)", "height": 1080},
                    {"id": "audio", "label": "Audio (MP3)", "height": 0}
                ]
            })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
        best_by_height = {}
        for f in info.get("formats", []):
            height = f.get("height")
            if height and f.get("vcodec", "none") != "none":
                tbr = f.get("tbr") or 0
                if height not in best_by_height or tbr > (best_by_height[height].get("tbr") or 0):
                    best_by_height[height] = f
                    
        formats = []
        for height, f in best_by_height.items():
            formats.append({
                "id": f["format_id"],
                "label": f"{height}p",
                "height": height,
            })
        formats.sort(key=lambda x: x["height"], reverse=True)

        return jsonify({
            "title": info.get("title", ""),
            "thumbnail": info.get("thumbnail", ""),
            "duration": info.get("duration"),
            "uploader": info.get("uploader", ""),
            "formats": formats,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/download", methods=["POST"])
def start_download():
    data = request.json
    url = data.get("url", "").strip()
    format_choice = data.get("format", "video")

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extractor_args': {'youtube': ['player_client=android,ios,web']}
    }
    
    if os.path.exists(COOKIES_FILE):
        ydl_opts['cookiefile'] = COOKIES_FILE
    
    if format_choice == "audio":
        ydl_opts['format'] = 'bestaudio/best'
    else:
        ydl_opts['format'] = 'best[ext=mp4]/best'

    try:
        # TIKTOK BYPASS
        if "tiktok.com" in url:
            import urllib.request, urllib.parse, json
            req = urllib.request.Request("https://tikwm.com/api/", data=urllib.parse.urlencode({"url": url, "hd": 1}).encode(), headers={"User-Agent": "Mozilla/5.0"})
            resp = json.loads(urllib.request.urlopen(req).read().decode())
            data = resp.get("data", {})
            direct_url = data.get("music") if format_choice == "audio" else data.get("play")
            ext = ".mp3" if format_choice == "audio" else ".mp4"
            safe_title = "".join(c for c in data.get('title', 'tiktok') if c.isalnum() or c in " -_").strip()[:30]
            if not direct_url:
                return jsonify({"error": "TikTok API failed to return media."}), 400
            return jsonify({
                "status": "done",
                "direct_url": direct_url,
                "filename": f"{safe_title}{ext}"
            })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            direct_url = info.get('url')
            
            # If the bestaudio doesn't provide a direct url, try to find it from formats
            if not direct_url and "formats" in info:
                for f in reversed(info["formats"]):
                    if format_choice == "audio" and f.get("acodec") != "none" and f.get("vcodec") == "none":
                        direct_url = f.get("url")
                        break
                    elif format_choice == "video" and f.get("ext") == "mp4" and f.get("acodec") != "none":
                        direct_url = f.get("url")
                        break
                        
            # absolute fallback
            if not direct_url and "formats" in info and len(info["formats"]) > 0:
                direct_url = info["formats"][-1].get("url")

            if not direct_url:
                return jsonify({"error": "Could not extract direct download link. Platform might be blocking Vercel Datacenter IPs."}), 400

            ext = ".mp3" if format_choice == "audio" else ".mp4"
            safe_title = "".join(c for c in info.get('title', 'video') if c.isalnum() or c in " -_").strip()
            
            return jsonify({
                "status": "done",
                "direct_url": direct_url,
                "filename": f"{safe_title}{ext}"
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8899)
