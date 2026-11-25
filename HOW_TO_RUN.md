# How to run Kawarimi no Meeting no Jutsu

## What it does

The program watches your webcam for a hand seal and, when you hold it, swaps your outgoing video for a loop of you sitting still. Microsoft Teams and Google Meet see the loop through a virtual camera. Make the seal again to go back to live video.

It changes video only. Your microphone is not touched, so mute yourself separately.

## Before you start

Everything except the virtual camera is already installed in `C:\meet`. The one missing piece is OBS Studio, which provides the "OBS Virtual Camera" device that Teams and Meet read from.

| Item | Status |
| --- | --- |
| Program (`kawarimi.py`) and launcher (`run.bat`) | Ready in `C:\meet` |
| Python 3.12 environment with OpenCV, MediaPipe, pyvirtualcam | Installed in `C:\meet\.venv` |
| Webcam (Integrated Webcam, 1280x720) | Tested, working |
| OBS Studio (virtual camera) | Not installed (Step 1) |

Without OBS the program still runs, but only shows a preview window. Teams and Meet cannot see it.

## Setting up on a new PC

Skip this section on the PC where `C:\meet` is already set up. On any other Windows 10 or 11 PC, do this once, then continue with Step 1.

1. **Install Python 3.12.** Open PowerShell and run:

   ```
   winget install Python.Python.3.12
   ```

   Use 3.12 specifically. The hand-tracking library this script pins (MediaPipe 0.10.14) does not install on Python 3.13 or newer. Close and reopen PowerShell afterwards.

2. **Copy the project files.** Create a folder such as `C:\meet` on the new PC and copy these three files into it:

   - `kawarimi.py`
   - `requirements.txt`
   - `run.bat`

   Do not copy the `.venv` folder. It only works on the PC it was created on.

3. **Create the Python environment.** In PowerShell:

   ```
   cd C:\meet
   py -3.12 -m venv .venv
   ```

4. **Install the libraries.** This downloads a few hundred MB and takes a few minutes:

   ```
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

5. **Install OBS Studio.** Follow Step 1 below.

6. **Test the setup.** The webcam light flashes for a couple of seconds:

   ```
   .venv\Scripts\python.exe kawarimi.py --check
   ```

   A working setup ends with these lines (a few TensorFlow warnings before them are normal):

   ```
   [ok] Webcam 0: 1280x720 @ 30fps
   [ok] Virtual camera ready: OBS Virtual Camera
   [ok] Processed 45 frames; hand detector ran without errors.
   [ok] Virtual camera: working
   ```

If the folder is not `C:\meet`, everything still works; `run.bat` uses whatever folder it sits in. The script is Windows-only as written.

| Setup problem | Fix |
| --- | --- |
| `py` is not recognised | Reopen PowerShell after installing Python, or reinstall Python with the "py launcher" option ticked. |
| `pip install` fails with "No matching distribution found for mediapipe" | The environment was made with the wrong Python version. Delete `.venv` and repeat from step 3 with `py -3.12`. |
| `pip install` cannot reach the internet | A company proxy or firewall is blocking it. Ask IT for the pip proxy settings. |
| Windows asks whether Python may use the camera | Allow it. Also check **Settings > Privacy & security > Camera > Let desktop apps access your camera** is on. |
| The check shows the wrong webcam | Try another one with `--camera 1`. |

## Step 1: Install OBS Studio (one time)

OBS only needs to be installed. You never have to open it.

1. Open PowerShell or Command Prompt.
2. Run this command:

   ```
   winget install OBSProject.OBSStudio
   ```

3. Approve the Windows admin prompt if one appears.
4. Restart Teams and your browser so they pick up the new camera.

The install needs admin rights. On a managed work laptop it may be blocked; in that case request OBS Studio from IT or the company software portal.

## Step 2: Start the program

1. Close any app that is using the webcam (Teams calls, Meet tabs, the Camera app). Only one app can hold the real webcam at a time.
2. Open the `C:\meet` folder in File Explorer.
3. Double-click `run.bat`.
4. Wait a few seconds. A black console window opens first, then a preview window titled "Kawarimi no Meeting no Jutsu (preview)".
5. Check the console window for this line:

   ```
   [ok] Virtual camera ready: OBS Virtual Camera
   ```

If it says "No virtual camera available - running PREVIEW ONLY" instead, OBS is not installed correctly. Go back to Step 1.

Keep both windows open for the whole meeting. You can minimise them.

## Step 3: Pick the virtual camera in your meeting app

Start the program first (Step 2), then choose "OBS Virtual Camera" as the camera. The apps remember this choice, so you normally do it once.

### Microsoft Teams

1. Open Teams and select the three dots next to your profile picture, then **Settings**.
2. Open **Devices**.
3. Under **Camera**, choose **OBS Virtual Camera**.
4. In a meeting you can also switch it from the arrow beside the camera button.

### Google Meet

1. Join or open a meeting in the browser.
2. Select the three dots, then **Settings**.
3. Open **Video**.
4. Under **Camera**, choose **OBS Virtual Camera**.

To go back to normal, pick "Integrated Webcam" in the same place.

## Step 4: Use the substitution

1. **Build up footage.** Sit still in your normal position with your hands out of view. The green bar at the top of the preview shows "loop footage ready" in seconds. You need at least 1.5 seconds; it fills up to 6.
2. **Make the seal.** Hold up your index and middle fingers pressed together, with the other fingers folded, where the webcam can see the hand. Hold for half a second.
3. **Check the switch.** The bar turns red and says "LOOP". Others now see the loop. A small live picture of you appears in the corner of the preview only.
4. **Do what you need to.** The loop keeps playing until you end it.
5. **Return.** Sit back in the same position, then make the seal again or press Space in the preview window. The video fades back to live.
6. **Quit.** Press Q or Esc in the preview window when the meeting is over.

| Action | How |
| --- | --- |
| Switch to loop / back to live | Hand seal held 0.5 s, or Space |
| Quit | Q or Esc |

Space, Q and Esc only work while the preview window is the active window. A peace sign with the fingers spread apart does not trigger the switch.

The loop looks most convincing when the lighting stays the same and nobody is talking to you directly.

## Options

Add options after `run.bat` in a Command Prompt opened in `C:\meet`, for example:

```
run.bat --hold 0.8 --loop-seconds 10
```

| Option | Default | What it changes |
| --- | --- | --- |
| `--hold` | 0.5 | Seconds the seal must be held. Raise it if the switch triggers by accident. |
| `--loop-seconds` | 6 | Maximum length of the loop footage. |
| `--fade` | 0.4 | Seconds of crossfade between live and loop. |
| `--camera` | 0 | Which webcam to use, if you have more than one. |
| `--width`, `--height` | 1280, 720 | Video resolution. |
| `--fps` | 30 | Frames per second. |
| `--no-preview` | off | Run without the preview window (seal only, no keys). |
| `--check` | off | Test the webcam, hand detector and virtual camera, then exit. |

## Troubleshooting

| Problem | Fix |
| --- | --- |
| "Could not open webcam 0" | Another app is using the webcam. Close Teams calls, Meet tabs and the Camera app, then run again. In Teams, make sure the camera is set to OBS Virtual Camera, not Integrated Webcam. |
| "No virtual camera available - running PREVIEW ONLY" | OBS Studio is not installed. Do Step 1, then restart the program. |
| "OBS Virtual Camera" is missing from the Teams or Meet camera list | Restart Teams or the browser after installing OBS. |
| Others see a blank or OBS placeholder picture | The program is not running. Start `run.bat` and keep it open. |
| "Not enough footage yet - sit still a moment" | Keep your hands out of view for a couple of seconds, then try again. |
| The seal does not trigger | Face your palm or the back of your hand to the camera in good light, fingers pressed together, and hold still. Use Space as a backup. |
| The switch triggers by accident | Start with a longer hold: `run.bat --hold 1.0`. |
| The picture in Teams looks mirrored to you | That is only your own preview in Teams; others see it the right way round. |
| Video is choppy | Lower the resolution: `run.bat --width 640 --height 480`. |
