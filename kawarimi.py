"""Kawarimi no Meeting no Jutsu - webcam loop substitution.

Reads the real webcam, watches for a hand seal (index + middle finger raised
together, other fingers folded), and when it is held swaps the outgoing video
for a seamless loop of the last few seconds of you sitting still. Make the seal
again (or press SPACE in the preview window) to switch back to live video.

The result is sent to a virtual camera (OBS Virtual Camera), which you select
as your camera in Microsoft Teams or Google Meet.

Keys in the preview window:  SPACE = toggle loop,  Q or ESC = quit
"""

import argparse
import math
import sys
import time
from collections import deque

import cv2
import mediapipe as mp
import numpy as np

try:
    import pyvirtualcam
    from pyvirtualcam import PixelFormat
except Exception:  # pragma: no cover - optional at runtime
    pyvirtualcam = None

JPEG_QUALITY = 92


# ---------------------------------------------------------------- gesture ---

def _dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def is_seal(lm):
    """True when the hand shows the two-finger seal.

    Index and middle fingers extended and held together, ring and pinky folded.
    Uses distances from the wrist, so it works at any hand rotation.
    """
    wrist = lm[0]

    def extended(tip, pip):
        return _dist(lm[tip], wrist) > _dist(lm[pip], wrist) * 1.15

    palm = _dist(wrist, lm[9]) or 1e-6
    fingers_together = _dist(lm[8], lm[12]) < palm * 0.45
    return (
        extended(8, 6)
        and extended(12, 10)
        and not extended(16, 14)
        and not extended(20, 18)
        and fingers_together
    )


# ------------------------------------------------------------ loop buffer ---

class CleanFootage:
    """Keeps recent hand-free footage (JPEG-compressed) to build the loop from.

    Footage is stored as contiguous hand-free segments so the loop never
    contains the hand coming up to make the seal.
    """

    def __init__(self, max_frames, min_frames, trim_frames):
        self.max_frames = max_frames
        self.min_frames = min_frames
        self.trim_frames = trim_frames  # dropped from segment end (hand entering)
        self.current = deque(maxlen=max_frames)
        self.fallback = []

    def add(self, frame, hand_visible):
        if hand_visible:
            usable = self._usable(self.current)
            if len(usable) >= self.min_frames:
                self.fallback = usable
            self.current.clear()
            return
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        if ok:
            self.current.append(buf)

    def _usable(self, segment):
        seg = list(segment)
        return seg[: len(seg) - self.trim_frames] if len(seg) > self.trim_frames else []

    def seconds_ready(self, fps):
        return max(len(self._usable(self.current)), len(self.fallback)) / fps

    def take_loop(self):
        """Return frames for the loop, or None if there is not enough footage."""
        usable = self._usable(self.current)
        frames = usable if len(usable) >= self.min_frames else self.fallback
        if len(frames) < self.min_frames:
            return None
        return list(frames)


class LoopPlayer:
    """Plays frames forward then backward (ping-pong) so there is no seam."""

    def __init__(self, frames):
        self.frames = frames
        self.i = len(frames) - 1  # start at the most recent frame, moving back
        self.step = -1

    def next(self):
        frame = cv2.imdecode(self.frames[self.i], cv2.IMREAD_COLOR)
        if len(self.frames) > 1:
            nxt = self.i + self.step
            if nxt < 0 or nxt >= len(self.frames):
                self.step = -self.step
                nxt = self.i + self.step
            self.i = nxt
        return frame


# ------------------------------------------------------------------- main ---

def open_camera(index, width, height, fps):
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        return None
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    return cap


def open_virtual_camera(width, height, fps):
    if pyvirtualcam is None:
        print("[!] pyvirtualcam is not installed - running preview only.")
        return None
    try:
        cam = pyvirtualcam.Camera(width=width, height=height, fps=fps, fmt=PixelFormat.BGR)
        print(f"[ok] Virtual camera ready: {cam.device}")
        return cam
    except Exception as exc:
        print("[!] No virtual camera available - running PREVIEW ONLY.")
        print("    Install OBS Studio (it provides 'OBS Virtual Camera'), then restart.")
        print(f"    Details: {exc}")
        return None


def draw_status(img, text, colour):
    cv2.rectangle(img, (0, 0), (img.shape[1], 44), (0, 0, 0), -1)
    cv2.putText(img, text, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, colour, 2, cv2.LINE_AA)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--camera", type=int, default=0, help="webcam index (default 0)")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--loop-seconds", type=float, default=6.0, help="length of the loop footage")
    ap.add_argument("--hold", type=float, default=0.5, help="seconds the seal must be held")
    ap.add_argument("--fade", type=float, default=0.4, help="crossfade seconds between live and loop")
    ap.add_argument("--no-preview", action="store_true", help="do not show the preview window")
    ap.add_argument("--check", action="store_true", help="test camera, detector and virtual camera, then exit")
    args = ap.parse_args()

    cap = open_camera(args.camera, args.width, args.height, args.fps)
    if cap is None:
        sys.exit(f"Could not open webcam {args.camera}. Is another app (Teams/Meet) using it?")
    ok, frame = cap.read()
    if not ok:
        sys.exit("Webcam opened but returned no image. Close other apps using the camera.")
    height, width = frame.shape[:2]
    fps = args.fps
    print(f"[ok] Webcam {args.camera}: {width}x{height} @ {fps}fps")

    vcam = open_virtual_camera(width, height, fps)
    hands = mp.solutions.hands.Hands(
        max_num_hands=2, model_complexity=0,
        min_detection_confidence=0.6, min_tracking_confidence=0.5,
    )

    footage = CleanFootage(
        max_frames=int(args.loop_seconds * fps),
        min_frames=int(1.5 * fps),
        trim_frames=int(0.5 * fps),
    )
    player = None          # LoopPlayer while substituted
    fade_frames = max(1, int(args.fade * fps))
    fade_left = 0          # frames remaining in the current crossfade
    seal_since = None
    armed = True           # seal must be released before it can trigger again
    notice, notice_until = "", 0.0
    frames_done = 0

    def toggle():
        nonlocal player, fade_left, notice, notice_until
        if player is None:
            loop = footage.take_loop()
            if loop is None:
                notice, notice_until = "Not enough footage yet - sit still a moment", time.time() + 2.5
                return
            player = LoopPlayer(loop)
            print(f"[jutsu] Substituted with a {len(loop) / fps:.1f}s loop")
        else:
            player = None
            print("[jutsu] Released - live video")
        fade_left = fade_frames

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("[!] Lost the webcam.")
                break

            result = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            hand_list = result.multi_hand_landmarks or []
            seal = any(is_seal(h.landmark) for h in hand_list)

            now = time.time()
            if seal:
                seal_since = seal_since or now
                if armed and now - seal_since >= args.hold:
                    armed = False
                    toggle()
            else:
                seal_since = None
                armed = True

            if player is None:
                footage.add(frame, hand_visible=bool(hand_list))

            # Compose the outgoing frame, crossfading at each switch.
            if player is not None:
                out = player.next()
                if fade_left > 0:
                    a = fade_left / fade_frames          # live weight fades out
                    out = cv2.addWeighted(frame, a, out, 1 - a, 0)
                    fade_left -= 1
            else:
                out = frame
                fade_left = 0

            if vcam is not None:
                vcam.send(out)

            if not args.no_preview and not args.check:
                view = out.copy()
                if now < notice_until:
                    draw_status(view, notice, (0, 200, 255))
                elif player is not None:
                    draw_status(view, "LOOP - others see the substitute (seal or SPACE to return)", (0, 0, 255))
                else:
                    ready = footage.seconds_ready(fps)
                    draw_status(view, f"LIVE - loop footage ready: {ready:.1f}s (seal or SPACE)", (0, 220, 0))
                if player is not None:  # small live inset so you can see yourself
                    inset = cv2.resize(frame, (width // 4, height // 4))
                    view[-inset.shape[0] - 10:-10, -inset.shape[1] - 10:-10] = inset
                cv2.imshow("Kawarimi no Meeting no Jutsu (preview)", view)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                if key == ord(" "):
                    toggle()

            frames_done += 1
            if args.check and frames_done >= 45:
                print(f"[ok] Processed {frames_done} frames; hand detector ran without errors.")
                print("[ok] Virtual camera: " + ("working" if vcam else "NOT available (preview only)"))
                break
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        hands.close()
        if vcam is not None:
            vcam.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
