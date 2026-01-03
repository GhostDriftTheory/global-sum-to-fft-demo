import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Rectangle
import numpy as np

# ==============================================================================
# CONFIGURATION
# ==============================================================================
OUTPUT_FILENAME = "ghost_drift_demo.gif"
FPS = 20
DURATION_SEC = 10.5
TOTAL_FRAMES = int(DURATION_SEC * FPS)

# Layout (1792 x 1024)
FIG_W_PX = 1792
FIG_H_PX = 1024
DPI = 100
FIG_W_IN = FIG_W_PX / DPI
FIG_H_IN = FIG_H_PX / DPI

# Colors
COLOR_TERM_BG = "#0e0e0e"
COLOR_TERM_FG = "#f0f0f0"
COLOR_TERM_ACCENT = "#00ff9c"
COLOR_PANEL_BG = "#ffffff"
COLOR_HIGHLIGHT = "#e6f2ff"  # Subtle background highlight
COLOR_PASS = "#28a745"
COLOR_SPEEDUP = "#d00000"

# Fonts
FONT_MONO = "monospace"
FONT_SANS = "sans-serif"

# ==============================================================================
# STORYBOARD DATA
# ==============================================================================

TERMINAL_EVENTS = [
    # Frame 0: Header
    (0.0, "header_main", "Global sum -> finite FFT replacement (one-shot demo)"),
    (0.0, "header_sub", "Same quantity. Same tolerance. Less cost."),

    # Frame 1: Baseline
    (0.6, "cmd", "$ python demo.py --mode baseline --N 2000000 --eps 1e-6"),
    # Merged context & baseline start into one line to prevent redundancy
    (1.5, "print", "\n[baseline] target: smoothed long-range aggregate (reference)"),
    (2.0, "print", "N=2,000,000   eps=1e-6"),
    (2.5, "print", "time: 12.84 s"),
    (2.6, "print", "result: 0.123456789"),

    # Frame 2: Divider
    (3.0, "print", "\n--- replacing global sum with finite FY window + FFT convolution ---"),

    # Frame 3: FFT Replacement
    (3.6, "cmd", "$ python demo.py --mode fft --eps 1e-6"),
    (4.2, "print", "\n[fft-replacement] FY window + FFT convolution"),
    (4.4, "print", "grid M=262144  (FFT)"), # <--- Simpler notation (was next_pow2)
    (4.6, "print", "window: Fejer-Yukawa"),
    (4.8, "print", "time: 0.41 s"),
    (5.0, "print", "result: 0.123456781"),
    (5.2, "print", "|Δresult|: 8.0e-09   (<= eps)"), # <--- Explicit Delta
    (5.4, "print", "speedup: 31.3x"),

    # Frame 4: Reproduce
    (6.8, "cmd", "$ python demo.py --reproduce  (prints exact params + seeds + hash)"),
    (7.5, "print", " > Params: M=262144, window=FY, eps=1e-6"),
    (7.7, "print", " > Hash:   a1b2c3d4... (verified)"),
]

PANEL_EVENTS = [
    # Frame 1: Baseline
    (2.5, "baseline_val", "BASELINE: 12.84s", "normal"),
    (2.5, "baseline_meta", "eps=1e-6, N=2M", "sub"),
    
    # Frame 3: FFT
    (4.8, "fft_val", "FFT REPLACEMENT: 0.41s", "bold_highlight"),
    (5.4, "speedup", "SPEEDUP: 31.3x", "big_bold_highlight"),
    
    # Error / Delta
    (5.2, "error", "|Δresult|: 8.0e-09", "pass_highlight"), # <--- Delta notation
    (5.2, "pass_badge", "PASS (|Δ| <= eps)", "pass_badge"), # <--- Math notation for strict check

    # Frame 4: Repro
    (7.0, "repro", "Reproducible params:\nM, window, eps, hash", "footer"),
]

# ==============================================================================
# PRECOMPILATION & ANIMATION
# ==============================================================================

def precompute_frames():
    """
    Pre-calculates the text state for every frame to avoid heavy string ops during animation.
    Returns: list of dicts { 'term_lines': str, 'panel_updates': {key: (text, style, highlight_active)} }
    """
    frames_data = []
    
    # Current state
    term_lines = []
    active_cmd = None # (start_time, text)
    panel_state = {} # key -> (text, style)
    
    for f in range(TOTAL_FRAMES):
        t = f / FPS
        
        # 1. Terminal State
        # Check for new prints
        for start, etype, text in TERMINAL_EVENTS:
            if t >= start and t < start + (1/FPS): # Trigger once
                if etype == "print":
                    term_lines.append(text)
                elif etype == "cmd":
                    active_cmd = (start, text)
        
        # Handle typing
        display_lines = term_lines.copy()
        cursor = ""
        if active_cmd:
            start, text = active_cmd
            duration = 0.5
            progress = (t - start) / duration
            if progress < 1.0:
                char_count = int(len(text) * progress)
                display_lines.append(text[:char_count])
                if int(t * 10) % 2 == 0: cursor = "\u2588" # Blink
            else:
                display_lines.append(text)
                active_cmd = None # Done typing
        else:
            # Idle cursor blinking at end
            if t < DURATION_SEC - 0.5 and int(t * 2) % 2 == 0:
                cursor = "\u2588"

        term_str = "\n".join(display_lines) + cursor
        
        # 2. Panel State
        panel_updates = {}
        for start, key, val, style in PANEL_EVENTS:
            if t >= start:
                highlight = False
                # Highlight logic (background flash) for 0.2s
                if 0 <= (t - start) < 0.25:
                    if "highlight" in style:
                        highlight = True
                
                panel_updates[key] = {
                    "text": val,
                    "style": style,
                    "highlight": highlight
                }

        frames_data.append({
            "term_str": term_str,
            "panel_updates": panel_updates
        })
        
    return frames_data

def create_animation():
    fig = plt.figure(figsize=(FIG_W_IN, FIG_H_IN), dpi=DPI)
    
    # --- Layout ---
    ax_term = fig.add_axes([0, 0, 0.65, 1], facecolor=COLOR_TERM_BG)
    ax_term.set_xticks([]); ax_term.set_yticks([]); 
    for s in ax_term.spines.values(): s.set_visible(False)

    ax_panel = fig.add_axes([0.65, 0, 0.35, 1], facecolor=COLOR_PANEL_BG)
    ax_panel.set_xticks([]); ax_panel.set_yticks([]); 
    for s in ax_panel.spines.values(): s.set_visible(False)

    # --- Static Headers ---
    # Retrieve header text from data
    h_main = next(e[2] for e in TERMINAL_EVENTS if e[1] == "header_main")
    h_sub = next(e[2] for e in TERMINAL_EVENTS if e[1] == "header_sub")
    
    ax_term.text(0.05, 0.92, h_main, color=COLOR_TERM_FG, 
                 fontfamily=FONT_MONO, fontsize=20, fontweight='bold', transform=ax_term.transAxes)
    ax_term.text(0.05, 0.88, h_sub, color="#888888", 
                 fontfamily=FONT_MONO, fontsize=14, transform=ax_term.transAxes)
    
    # --- Dynamic Objects ---
    term_text_obj = ax_term.text(0.05, 0.80, "", color=COLOR_TERM_FG, 
                                 fontfamily=FONT_MONO, fontsize=16, va="top", transform=ax_term.transAxes)
    
    panel_objs = {}
    # Init panel text objects (invisible initially)
    # Baseline
    panel_objs['baseline_val'] = ax_panel.text(0.1, 0.85, "", color="#333", fontsize=24, fontweight='bold', transform=ax_panel.transAxes)
    panel_objs['baseline_meta'] = ax_panel.text(0.1, 0.81, "", color="#666", fontsize=16, transform=ax_panel.transAxes)
    # FFT
    panel_objs['fft_val'] = ax_panel.text(0.1, 0.60, "", color="#333", fontsize=24, transform=ax_panel.transAxes)
    panel_objs['speedup'] = ax_panel.text(0.1, 0.50, "", color="#000", fontsize=50, fontweight='bold', transform=ax_panel.transAxes)
    
    # Error (Raised y to 0.42 to be closer to SPEEDUP as requested)
    panel_objs['error'] = ax_panel.text(0.1, 0.42, "", color="#333", fontsize=18, transform=ax_panel.transAxes)
    
    # Pass badge
    panel_objs['pass_badge'] = ax_panel.text(0.1, 0.30, "", color=COLOR_PASS, fontsize=20, fontweight='bold', transform=ax_panel.transAxes)
    # Footer
    panel_objs['repro'] = ax_panel.text(0.1, 0.10, "", color="#999", fontsize=14, transform=ax_panel.transAxes)

    # Precompute frames
    print("Pre-compiling frames...")
    frames_data = precompute_frames()
    print("Done.")

    def update(frame_idx):
        data = frames_data[frame_idx]
        
        # 1. Update Terminal
        term_text_obj.set_text(data["term_str"])
        
        # 2. Update Panel
        updates = data["panel_updates"]
        for key, p_data in updates.items():
            obj = panel_objs.get(key)
            if not obj: continue
            
            # Content
            obj.set_text(p_data["text"])
            
            # Style & Highlight
            style = p_data["style"]
            is_highlight = p_data["highlight"]
            
            # Reset bbox first
            bbox_props = dict(facecolor='none', edgecolor='none', pad=2.0)
            
            # Background Highlight (Subtle flash)
            if is_highlight:
                bbox_props['facecolor'] = COLOR_HIGHLIGHT
            
            obj.set_bbox(bbox_props)
            
            # Font Colors & Weights
            if "big_bold" in style:
                obj.set_fontsize(48)
                obj.set_color(COLOR_SPEEDUP)
            elif "pass" in style:
                if key == "pass_badge": obj.set_color(COLOR_PASS)
                elif key == "error": obj.set_color("#333") # Error val itself is dark
            elif "bold" in style:
                obj.set_weight("bold")
                obj.set_color("#333")
            elif "sub" in style:
                obj.set_color("#666")
            elif "footer" in style:
                obj.set_color("#999")
            else:
                obj.set_color("#333")

        return [term_text_obj] + list(panel_objs.values())

    anim = animation.FuncAnimation(
        fig, update, frames=TOTAL_FRAMES, interval=1000/FPS, blit=True
    )
    
    print(f"Generating GIF ({TOTAL_FRAMES} frames)...")
    try:
        anim.save(OUTPUT_FILENAME, writer='pillow', fps=FPS)
        print(f"Success! Saved to {OUTPUT_FILENAME}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_animation()