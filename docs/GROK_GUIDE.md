# Grok Imagine Suite - Usage Guide

Download and manage images/videos from [Grok Imagine](https://grok.com/imagine).

## 🔑 Authentication

The tool requires an active Grok session. Use the passive monitor to capture your cookies from Chrome:

```bash
# Launch Chrome, capture cookies automatically, and close when done
python scripts/grok-cookie-monitor.py --launch --auto --close
```

Once captured, cookies are saved to `config/grok_profiles.json`. You can see your profiles using:
```bash
# List profiles if you have multiple
# (Manual check of config/grok_profiles.json)
```

## 🖼️ Generating Images

Generate a batch of images from a text prompt.

```bash
# Default (6 images, 16:9)
python scripts/grok-imagine.py generate "a futuristic city with neon lights"

# Custom aspect ratio and count
python scripts/grok-imagine.py generate "mountain sunrise" --aspect 2:3 --count 12
```

### How to get the `post-id`
The CLI will print the generated IDs directly to your terminal:
```text
Generated 6 images:
  1. 0bce8a6d-be3e-4cbd-a5b6-160172786a84  downloads\grok-imagine\0bce8a6d_...
```
The string `0bce8a6d-be3e-4cbd-a5b6-160172786a84` is your **post-id**.

## 🎬 Generating Videos

You can generate videos from any existing image post.

### 💡 The "Stability" Requirement
Grok's video generator is most reliable when the image is "stable" in your gallery. If you just generated an image and it's not showing up in `gallery list`, run this before making the video:

```bash
# 1. Save the image to your gallery first to stabilize it
python scripts/grok-imagine.py gallery save https://imagine-public.x.ai/imagine-public/images/<POST-ID>.jpg

# 2. Generate the video
python scripts/grok-imagine.py video generate <POST-ID> --mode custom --prompt "camera pans slowly"
```

### Video Generation Modes
- **Normal Mode**: Standard AI animation of the image.
  ```bash
  python scripts/grok-imagine.py video generate <POST-ID>
  ```
- **Custom Mode**: Animate with a specific motion prompt.
  ```bash
  python scripts/grok-imagine.py video generate <POST-ID> --mode custom --prompt "cinematic slow zoom"
  ```

## 🏛️ Gallery Management

```bash
# List your liked posts
python scripts/grok-imagine.py gallery list --limit 20

# Download a specific post (image or video)
python scripts/grok-imagine.py gallery download <post-id>

# Like a post to keep it in your history
python scripts/grok-imagine.py gallery like <post-id>
```

## 🛠️ Troubleshooting

### Stream stuck at 95%
The CLI includes a self-healing mechanism for this. If the server skips the final 100% event, the tool will automatically construct the deterministic asset URL and attempt to download the video.

### Auth Errors (401/403)
Your SSO cookie has likely expired. Run the `grok-cookie-monitor.py` script again to refresh your session.
