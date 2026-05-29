"""
4-Stroke Engine Simulation using PyOpenGL
Simulates: Intake → Compression → Power (Combustion) → Exhaust

Controls:
  SPACE  - Pause/Resume
  +/-    - Speed up / Slow down
  R      - Reset
  ESC/Q  - Quit
"""

import sys
import math
import time

try:
    from OpenGL.GL import *
    from OpenGL.GLUT import *
    from OpenGL.GLU import *
except ImportError:
    print("PyOpenGL not found. Install with: pip install PyOpenGL PyOpenGL_accelerate")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────
#  Global state
# ─────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 900, 700

angle        = 0.0          # crankshaft angle in degrees (0-720 cycle)
speed        = 2.0          # degrees per frame
paused       = False
stroke_names = ["INTAKE", "COMPRESSION", "POWER (Combustion)", "EXHAUST"]
explosion    = 0.0          # 0-1 flash intensity
last_time    = time.time()

# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────
def deg2rad(d): return d * math.pi / 180.0

def set_color(r, g, b, a=1.0):
    glColor4f(r, g, b, a)

def draw_rect(x, y, w, h):
    glBegin(GL_QUADS)
    glVertex2f(x,     y)
    glVertex2f(x + w, y)
    glVertex2f(x + w, y + h)
    glVertex2f(x,     y + h)
    glEnd()

def draw_rect_outline(x, y, w, h, lw=2.0):
    glLineWidth(lw)
    glBegin(GL_LINE_LOOP)
    glVertex2f(x,     y)
    glVertex2f(x + w, y)
    glVertex2f(x + w, y + h)
    glVertex2f(x,     y + h)
    glEnd()

def draw_circle(cx, cy, r, segments=60, filled=True):
    if filled:
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(cx, cy)
    else:
        glLineWidth(2.0)
        glBegin(GL_LINE_LOOP)
    for i in range(segments + 1):
        a = 2 * math.pi * i / segments
        glVertex2f(cx + r * math.cos(a), cy + r * math.sin(a))
    glEnd()

def draw_line(x1, y1, x2, y2, lw=2.0):
    glLineWidth(lw)
    glBegin(GL_LINES)
    glVertex2f(x1, y1)
    glVertex2f(x2, y2)
    glEnd()

def render_text(x, y, text, scale=0.12, spacing=8):
    """Simple bitmap text using GLUT."""
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))

def render_text_small(x, y, text):
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(ch))

# ─────────────────────────────────────────────────────────────
#  Engine 
# ─────────────────────────────────────────────────────────────
BORE          = 70.0    # cylinder bore width
STROKE_LEN    = 100.0   # piston travel distance
CON_ROD_LEN   = 130.0   # connecting rod length
CRANK_RADIUS  = STROKE_LEN / 2.0   # = 50

CYL_X         = 420.0   # cylinder left edge
CYL_TOP       = 260.0   # cylinder top (fixed)
CYL_BOTTOM    = CYL_TOP + STROKE_LEN + 60   # extra room
CYL_MID       = CYL_X + BORE / 2.0

CRANK_CX      = CYL_MID
CRANK_CY      = CYL_BOTTOM + 20.0

def piston_y_from_angle(a_deg):
    """
    a_deg: crankshaft angle (0 = TDC)
    Returns Y position of piston top.
    Standard slider-crank formula.
    """
    a = deg2rad(a_deg)
    # distance from crank center to piston pin along cylinder axis
    r = CRANK_RADIUS
    l = CON_ROD_LEN
    y_offset = r * math.cos(a) + math.sqrt(l**2 - (r * math.sin(a))**2)
    # y_offset is distance above crank center, map to screen coords
    piston_top = CRANK_CY - y_offset - 20   # 20 = piston height half
    return piston_top

def get_stroke(a_deg):
    """Return 0-3 for the current stroke based on crankshaft angle (0-720)."""
    a = a_deg % 720
    if a < 180:   return 0  # Intake
    if a < 360:   return 1  # Compression
    if a < 540:   return 2  # Power
    return 3                # Exhaust

# ─────────────────────────────────────────────────────────────
#  Drawing sub-components
# ─────────────────────────────────────────────────────────────
def draw_background():
    # Dark industrial background
    glClearColor(0.08, 0.08, 0.12, 1.0)
    glClear(GL_COLOR_BUFFER_BIT)

    # Grid lines
    set_color(0.15, 0.15, 0.22)
    glLineWidth(1.0)
    for gx in range(0, WIDTH, 40):
        draw_line(gx, 0, gx, HEIGHT, 1.0)
    for gy in range(0, HEIGHT, 40):
        draw_line(0, gy, WIDTH, gy, 1.0)

def draw_cylinder(stroke, expl):
    cx = CYL_X
    cy = CYL_TOP
    w  = BORE
    h  = STROKE_LEN + 60

    # Cylinder walls - steel look
    set_color(0.3, 0.35, 0.4)
    draw_rect(cx - 12, cy, 12, h)
    draw_rect(cx + w,  cy, 12, h)

    # Cylinder head (top)
    set_color(0.25, 0.3, 0.35)
    draw_rect(cx - 12, cy - 28, w + 24, 28)

    # Head bolt details
    set_color(0.4, 0.45, 0.5)
    for bx in [cx - 6, cx + w + 2]:
        for by in [cy - 22, cy - 8]:
            draw_circle(bx, by, 4)

    # ── Valves ──
    intake_open  = stroke == 0
    exhaust_open = stroke == 3
    valve_y      = cy - 2

    # Intake valve (left)
    set_color(0.2, 0.7, 0.3) if intake_open else set_color(0.2, 0.4, 0.25)
    draw_rect(cx + 8, valve_y - (8 if intake_open else 0), 14, 8)
    set_color(0.15, 0.55, 0.25) if intake_open else set_color(0.15, 0.3, 0.2)
    draw_circle(cx + 15, valve_y - (8 if intake_open else 0), 5)

    # Exhaust valve (right)
    set_color(0.8, 0.3, 0.2) if exhaust_open else set_color(0.4, 0.2, 0.15)
    draw_rect(cx + BORE - 22, valve_y - (8 if exhaust_open else 0), 14, 8)
    set_color(0.65, 0.25, 0.15) if exhaust_open else set_color(0.3, 0.15, 0.1)
    draw_circle(cx + BORE - 15, valve_y - (8 if exhaust_open else 0), 5)

    # ── Spark plug ──
    set_color(0.9, 0.85, 0.2)
    draw_rect(cx + BORE//2 - 3, cy - 28, 6, 14)
    set_color(0.95, 0.95, 0.95)
    draw_circle(cx + BORE//2, cy - 24, 4)

    # Spark if power stroke starts
    if expl > 0.05:
        set_color(1.0, 0.9, 0.2, expl)
        for sa in range(0, 360, 45):
            sr = deg2rad(sa)
            ex = cx + BORE//2 + 12 * math.cos(sr) * expl
            ey = cy - 20  + 12 * math.sin(sr) * expl
            draw_line(cx + BORE//2, cy - 20, ex, ey, 2.5)

    # ── Combustion chamber gas color ──
    gas_y  = cy
    pist_y = piston_y_from_angle(angle)
    gas_h  = max(0, pist_y - gas_y)

    if stroke == 0:   # Intake - fresh air+fuel (blue-ish)
        set_color(0.2, 0.4, 0.8, 0.35)
    elif stroke == 1:  # Compression - brighter
        set_color(0.3, 0.5, 0.9, 0.5)
    elif stroke == 2:  # Power - hot orange/red
        t = expl
        set_color(0.9 + 0.1*t, 0.3 + 0.3*(1-t), 0.05, 0.6)
    else:              # Exhaust - dark grey
        set_color(0.35, 0.35, 0.35, 0.4)

    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    if gas_h > 0:
        draw_rect(cx, gas_y, w, gas_h)
    glDisable(GL_BLEND)

    # Cylinder wall outline
    set_color(0.55, 0.6, 0.65)
    draw_rect_outline(cx, cy, w, h, 2.0)

def draw_piston(py):
    px = CYL_X
    pw = BORE
    ph = 22

    # Piston body
    set_color(0.55, 0.58, 0.62)
    draw_rect(px + 2, py, pw - 4, ph)

    # Piston rings
    set_color(0.75, 0.78, 0.82)
    draw_rect(px + 2, py + 4,  pw - 4, 3)
    draw_rect(px + 2, py + 9,  pw - 4, 3)
    draw_rect(px + 2, py + 14, pw - 4, 3)

    # Piston pin
    set_color(0.4, 0.42, 0.45)
    draw_circle(CYL_MID, py + ph//2, 5)

    # Piston outline
    set_color(0.7, 0.73, 0.78)
    draw_rect_outline(px + 2, py, pw - 4, ph, 1.5)

def draw_connecting_rod(py):
    pin_x = CYL_MID
    pin_y = py + 11   # piston pin

    a = deg2rad(angle)
    crank_pin_x = CRANK_CX + CRANK_RADIUS * math.sin(a)
    crank_pin_y = CRANK_CY - CRANK_RADIUS * math.cos(a)

    # Rod body
    set_color(0.45, 0.48, 0.52)
    draw_line(pin_x, pin_y, crank_pin_x, crank_pin_y, 6.0)

    # Big end
    set_color(0.5, 0.52, 0.55)
    draw_circle(crank_pin_x, crank_pin_y, 9)
    set_color(0.3, 0.32, 0.35)
    draw_circle(crank_pin_x, crank_pin_y, 4)

    # Small end
    set_color(0.5, 0.52, 0.55)
    draw_circle(pin_x, pin_y, 7)
    set_color(0.3, 0.32, 0.35)
    draw_circle(pin_x, pin_y, 3)

def draw_crankshaft():
    a = deg2rad(angle)
    crank_pin_x = CRANK_CX + CRANK_RADIUS * math.sin(a)
    crank_pin_y = CRANK_CY - CRANK_RADIUS * math.cos(a)

    # Main journal
    set_color(0.35, 0.38, 0.42)
    draw_circle(CRANK_CX, CRANK_CY, 16)
    set_color(0.5, 0.53, 0.57)
    draw_circle(CRANK_CX, CRANK_CY, 16, filled=False)

    # Crank arm
    set_color(0.4, 0.42, 0.46)
    draw_line(CRANK_CX, CRANK_CY, crank_pin_x, crank_pin_y, 8.0)

    # Counterweight (opposite side)
    cw_x = CRANK_CX - CRANK_RADIUS * 0.6 * math.sin(a)
    cw_y = CRANK_CY + CRANK_RADIUS * 0.6 * math.cos(a)
    set_color(0.32, 0.35, 0.38)
    draw_line(CRANK_CX, CRANK_CY, cw_x, cw_y, 12.0)

    # Center dot
    set_color(0.7, 0.72, 0.75)
    draw_circle(CRANK_CX, CRANK_CY, 5)

def draw_flywheel():
    a = deg2rad(angle / 2.0)   # visual rotation marker
    fx = CRANK_CX + 85
    fy = CRANK_CY

    # Flywheel body
    set_color(0.28, 0.30, 0.33)
    draw_circle(fx, fy, 42)
    set_color(0.38, 0.40, 0.43)
    draw_circle(fx, fy, 42, filled=False)

    # Spokes
    set_color(0.35, 0.37, 0.40)
    for i in range(6):
        sa = a + i * math.pi / 3
        draw_line(fx, fy,
                  fx + 36 * math.cos(sa),
                  fy + 36 * math.sin(sa), 3.0)

    # Rim detail
    set_color(0.45, 0.47, 0.50)
    draw_circle(fx, fy, 38, filled=False)

    # Hub
    set_color(0.5, 0.52, 0.55)
    draw_circle(fx, fy, 10)

    # Timing mark
    mx = fx + 36 * math.cos(a)
    my = fy + 36 * math.sin(a)
    set_color(1.0, 0.8, 0.1)
    draw_circle(mx, my, 4)

def draw_exhaust_pipe():
    # Exhaust pipe on the right
    ex = CYL_X + BORE + 12
    ey = CYL_TOP + 10
    set_color(0.35, 0.30, 0.25)
    draw_rect(ex, ey, 40, 12)
    draw_rect(ex + 40, ey - 20, 12, 32)
    draw_rect_outline(ex, ey, 40, 12, 1.5)
    draw_rect_outline(ex + 40, ey - 20, 12, 32, 1.5)

def draw_intake_pipe():
    # Intake pipe on the left with filter
    ix = CYL_X - 12
    iy = CYL_TOP + 10
    set_color(0.25, 0.35, 0.45)
    draw_rect(ix - 40, iy, 40, 12)
    # Air filter
    set_color(0.3, 0.45, 0.35)
    draw_rect(ix - 55, iy - 8, 18, 28)
    draw_rect_outline(ix - 55, iy - 8, 18, 28, 1.5)
    set_color(0.25, 0.35, 0.45)
    draw_rect_outline(ix - 40, iy, 40, 12, 1.5)

def draw_stroke_indicator(stroke):
    colors = [
        (0.2, 0.5, 0.9),   # Intake   - blue
        (0.8, 0.7, 0.1),   # Compress - yellow
        (0.9, 0.3, 0.1),   # Power    - red
        (0.5, 0.5, 0.5),   # Exhaust  - grey
    ]
    descriptions = [
        "Piston moves DOWN, intake valve OPEN",
        "Piston moves UP, both valves CLOSED",
        "Spark ignites fuel, piston forced DOWN",
        "Piston moves UP, exhaust valve OPEN",
    ]

    bx, by = 30, HEIGHT - 220
    bw, bh = 250, 200

    # Panel background
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    set_color(0.08, 0.10, 0.14, 0.88)
    draw_rect(bx, by, bw, bh)
    glDisable(GL_BLEND)

    set_color(0.4, 0.45, 0.5)
    draw_rect_outline(bx, by, bw, bh, 1.5)

    # Title
    set_color(0.75, 0.78, 0.82)
    render_text(bx + 10, by + bh - 22, "STROKE INDICATOR")

    # Four stroke boxes
    box_w = 52
    for i in range(4):
        bxi = bx + 10 + i * (box_w + 6)
        byi = by + bh - 70

        # Highlight active
        if i == stroke:
            set_color(*colors[i])
            draw_rect(bxi, byi, box_w, 36)
        else:
            set_color(0.15, 0.17, 0.20)
            draw_rect(bxi, byi, box_w, 36)

        set_color(0.5, 0.55, 0.6) if i != stroke else set_color(1,1,1)
        draw_rect_outline(bxi, byi, box_w, 36, 1.5)
        set_color(1, 1, 1) if i == stroke else set_color(0.4, 0.42, 0.45)
        render_text_small(bxi + 4, byi + 23, str(i + 1))
        render_text_small(bxi + 4, byi + 8, stroke_names[i][:6])

    # Active description
    r, g, b = colors[stroke]
    set_color(r, g, b)
    render_text(bx + 10, by + bh - 90, stroke_names[stroke])
    set_color(0.65, 0.68, 0.72)
    # word-wrap manually
    desc = descriptions[stroke]
    words = desc.split()
    line, lines = "", []
    for w in words:
        if len(line) + len(w) < 30:
            line += w + " "
        else:
            lines.append(line.strip())
            line = w + " "
    lines.append(line.strip())
    for li, ln in enumerate(lines):
        render_text_small(bx + 10, by + bh - 115 - li * 16, ln)

def draw_rpm_gauge():
    # Crankshaft angle display
    px, py = WIDTH - 210, HEIGHT - 130
    set_color(0.7, 0.73, 0.77)
    render_text(px, py, f"Crank: {int(angle % 360):3d}\u00b0")
    render_text(px, py - 22, f"Cycle: {int(angle % 720):3d}/720\u00b0")
    spd_pct = int((speed / 8.0) * 100)
    render_text(px, py - 44, f"Speed: {spd_pct}%")
    set_color(0.4, 0.45, 0.5)
    render_text_small(px, py - 65, "+/- keys to change speed")
    render_text_small(px, py - 80, "SPACE to pause  R to reset")

def draw_title():
    set_color(0.85, 0.88, 0.92)
    render_text(WIDTH//2 - 130, HEIGHT - 35, "4-STROKE ENGINE SIMULATION")
    set_color(0.4, 0.45, 0.5)
    render_text_small(WIDTH//2 - 80, HEIGHT - 55, "PyOpenGL Visualization")

def draw_paused_overlay():
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    set_color(0.0, 0.0, 0.0, 0.45)
    draw_rect(0, 0, WIDTH, HEIGHT)
    glDisable(GL_BLEND)
    set_color(1.0, 0.85, 0.2)
    render_text(WIDTH//2 - 45, HEIGHT//2, "PAUSED")
    set_color(0.7, 0.72, 0.75)
    render_text_small(WIDTH//2 - 65, HEIGHT//2 - 25, "Press SPACE to resume")

# ─────────────────────────────────────────────────────────────
#  GLUT callbacks
# ─────────────────────────────────────────────────────────────
def display():
    global explosion

    stroke = get_stroke(angle)

    # Explosion flash at start of power stroke (angle ~360)
    cycle_angle = angle % 720
    if 360 <= cycle_angle < 380:
        explosion = 1.0 - (cycle_angle - 360) / 20.0
    else:
        explosion = max(0.0, explosion - 0.05)

    py = piston_y_from_angle(angle)

    draw_background()

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0, WIDTH, 0, HEIGHT)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    draw_title()
    draw_intake_pipe()
    draw_exhaust_pipe()
    draw_cylinder(stroke, explosion)
    draw_piston(py)
    draw_connecting_rod(py)
    draw_crankshaft()
    draw_flywheel()
    draw_stroke_indicator(stroke)
    draw_rpm_gauge()

    if paused:
        draw_paused_overlay()

    glutSwapBuffers()

def update(value):
    global angle
    if not paused:
        angle = (angle + speed) % 720
    glutPostRedisplay()
    glutTimerFunc(16, update, 0)   # ~60 fps

def keyboard(key, x, y):
    global paused, angle, speed
    k = key if isinstance(key, str) else key.decode('utf-8', errors='ignore')
    if k in ('\x1b', 'q', 'Q'):
        sys.exit(0)
    elif k == ' ':
        paused = not paused
    elif k == 'r':
        angle = 0.0
    elif k in ('+', '='):
        speed = min(speed + 0.5, 8.0)
    elif k == '-':
        speed = max(speed - 0.5, 0.3)

def reshape(w, h):
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0, WIDTH, 0, HEIGHT)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA)
    glutInitWindowSize(WIDTH, HEIGHT)
    glutInitWindowPosition(100, 50)
    glutCreateWindow(b"4-Stroke Engine Simulation - PyOpenGL")

    glEnable(GL_LINE_SMOOTH)
    glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glDisable(GL_BLEND)

    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(keyboard)
    glutTimerFunc(16, update, 0)

    print("=" * 50)
    print("  4-Stroke Engine Simulation — PyOpenGL")
    print("=" * 50)
    print("  SPACE  → Pause / Resume")
    print("  +/-    → Speed up / Slow down")
    print("  R      → Reset to TDC")
    print("  ESC/Q  → Quit")
    print("=" * 50)
    print("  Strokes: Intake → Compression → Power → Exhaust")
    print("=" * 50)

    glutMainLoop()


main()