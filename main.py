import os
import json
import random
import math

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Line, Triangle, Ellipse, Rectangle, RoundedRectangle, PushMatrix, PopMatrix, InstructionGroup
from kivy.clock import Clock
from kivy.properties import ListProperty
from kivy.core.window import Window
from kivy.core.text import LabelBase
# Simulate mobile screen layout for desktop development
Window.size = (450, 820)

# --- FONT REGISTRATION ---
# Register the Orbitron font globally
font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Orbitron.ttf")
if os.path.exists(font_path):
    LabelBase.register(name='Orbitron', fn_regular=font_path)
else:
    # Fallback to standard sans-serif if not found
    LabelBase.register(name='Orbitron', fn_regular='Roboto')

# --- COLOR PALETTE (Futuristic Neon Space Theme) ---
COLOR_BG = (12/255, 12/255, 16/255, 1.0)         # Deep Space Dark
COLOR_PANEL = (20/255, 20/255, 28/255, 1.0)      # Panel Background
COLOR_TEXT = (240/255, 240/255, 250/255, 1.0)     # Off-white Text
COLOR_NEON_BLUE = (0/255, 217/255, 255/255, 1.0) # UI Buttons/Cyan
COLOR_NEON_GREEN = (0/255, 255/255, 136/255, 1.0)# Win/Laser Success Green
COLOR_NEON_RED = (255/255, 51/255, 102/255, 1.0) # Loss/Laser Fail Red
COLOR_MIRROR = (255/255, 200/255, 0/255, 1.0)     # Mirror Yellow
COLOR_ARROW = (220/255, 220/255, 235/255, 1.0)    # Arrow Default Grey
COLOR_GLOW_WHITE = (1.0, 1.0, 1.0, 1.0)

# --- GAME CONSTANTS ---
GRID_COLS = 6
GRID_ROWS = 10
GRID_MARGIN = 15

# --- SAVE FILE MANAGEMENT ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_FILE = os.path.join(BASE_DIR, "save_data.json")

def load_save_data():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, 'r') as f:
                data = json.load(f)
                return (
                    data.get("high_score", 0),
                    data.get("current_level", 1),
                    data.get("score", 0)
                )
        except Exception as e:
            print(f"Error loading save file: {e}")
    else:
        write_save_data(0, 1, 0)
    return 0, 1, 0

def write_save_data(high_score, current_level, score):
    try:
        with open(SAVE_FILE, 'w') as f:
            json.dump({
                "high_score": high_score,
                "current_level": current_level,
                "score": score
            }, f)
    except Exception as e:
        print(f"Error writing save file: {e}")


# --- PARTICLE SYSTEM ---
class Particle:
    def __init__(self, x, y, dx, dy, color, size=3, life=1.0):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.color = color  # (R, G, B) tuple in 0-255 scale
        self.size = size
        self.life = life  # seconds
        self.max_life = life

    def update(self, dt):
        self.x += self.dx * dt * 60
        self.y += self.dy * dt * 60
        self.life -= dt


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def spawn(self, x, y, color, count=5, speed=2.0):
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            s = random.uniform(0.5, speed)
            dx = math.cos(angle) * s
            dy = math.sin(angle) * s
            life = random.uniform(0.3, 0.8)
            size = random.randint(2, 4)
            self.particles.append(Particle(x, y, dx, dy, color, size, life))

    def update(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]


# --- LEVEL SOLVER / TRAJECTORY SIMULATION ---
def simulate_path(grid, start_col, start_row):
    """
    Simulates the laser path instantly from a given starting arrow.
    Returns:
       success: True if the path triggers ALL arrows in the grid and exits safely.
       laser_steps: List of dicts representing the steps the laser takes
       hit_arrows: Set of arrow positions (col, row) that were triggered.
    """
    if (start_col, start_row) not in grid or grid[(start_col, start_row)]['type'] != 'arrow':
        return False, [], set()

    # Create temporary copy of item state
    temp_grid = {}
    total_arrows = 0
    for pos, item in grid.items():
        if item['type'] == 'arrow':
            temp_grid[pos] = {'type': 'arrow', 'dir': item['dir'], 'active': True}
            total_arrows += 1
        else:
            temp_grid[pos] = {'type': 'mirror', 'mirror_type': item['mirror_type']}

    laser_steps = []
    hit_arrows = set()
    
    current_col, current_row = start_col, start_row
    current_dir = temp_grid[(current_col, current_row)]['dir']
    
    # Trigger start arrow
    temp_grid[(current_col, current_row)]['active'] = False
    hit_arrows.add((current_col, current_row))
    
    steps_count = 0
    max_steps = 150 # Prevent infinite loops in cycle configurations
    
    current_pos = (current_col, current_row)
    segment_start = current_pos
    
    while steps_count < max_steps:
        # Move forward cell by cell
        next_col = current_pos[0] + current_dir[0]
        next_row = current_pos[1] + current_dir[1]
        next_pos = (next_col, next_row)
        
        # Check out of bounds
        if not (0 <= next_col < GRID_COLS and 0 <= next_row < GRID_ROWS):
            # Laser exits screen bounds
            laser_steps.append({
                'start_cell': segment_start,
                'end_cell': next_pos,
                'type': 'exit',
                'dir': current_dir
            })
            break
            
        cell = temp_grid.get(next_pos)
        
        if cell is None:
            # Empty space, continue tracing
            current_pos = next_pos
            steps_count += 1
            continue
            
        if cell['type'] == 'mirror':
            # Add segment leading to the mirror
            laser_steps.append({
                'start_cell': segment_start,
                'end_cell': next_pos,
                'type': 'path',
                'dir': current_dir
            })
            
            # Reflect
            dx, dy = current_dir
            if cell['mirror_type'] == '/':
                current_dir = (-dy, -dx)
            else: # '\'
                current_dir = (dy, dx)
                
            current_pos = next_pos
            segment_start = next_pos
            
        elif cell['type'] == 'arrow':
            # Case 1: Arrow was already triggered, passes through
            if not cell['active']:
                current_pos = next_pos
                steps_count += 1
                continue
                
            # Case 2: Hit arrow from behind
            if current_dir == cell['dir']:
                # Valid trigger!
                laser_steps.append({
                    'start_cell': segment_start,
                    'end_cell': next_pos,
                    'type': 'path',
                    'dir': current_dir
                })
                
                cell['active'] = False
                hit_arrows.add(next_pos)
                
                # Chain trigger: Next laser segment starts here
                current_dir = cell['dir']
                current_pos = next_pos
                segment_start = next_pos
                
            # Case 3: Hit arrow from side or front (crash)
            else:
                laser_steps.append({
                    'start_cell': segment_start,
                    'end_cell': next_pos,
                    'type': 'crash',
                    'dir': current_dir
                })
                break
                
        steps_count += 1
        
    success = (len(hit_arrows) == total_arrows) and (laser_steps and laser_steps[-1]['type'] != 'crash')
    return success, laser_steps, hit_arrows


# --- PROCEDURAL LEVEL GENERATOR ---
def generate_solvable_level(level_idx):
    """
    Generates a guaranteed solvable grid layout for a given level by tracing BACKWARD
    from a randomized exit path. Validates the solve path AFTER decoy placement.
    """
    num_arrows = min(4 + (level_idx - 1) // 2, 10)
    num_mirrors = min(1 + (level_idx - 1) // 3, 6)
    
    for attempt in range(2000):
        grid = {}
        visited = set()
        
        border_cells = []
        for c in range(GRID_COLS):
            border_cells.append((c, 0, (0, -1)))  # exits UP
            border_cells.append((c, GRID_ROWS - 1, (0, 1)))  # exits DOWN
        for r in range(1, GRID_ROWS - 1):
            border_cells.append((0, r, (-1, 0)))  # exits LEFT
            border_cells.append((GRID_COLS - 1, r, (1, 0)))  # exits RIGHT
            
        ex_col, ex_row, exit_dir = random.choice(border_cells)
        
        grid[(ex_col, ex_row)] = {'type': 'arrow', 'dir': exit_dir, 'is_start': False}
        visited.add((ex_col, ex_row))
        
        current_pos = (ex_col, ex_row)
        current_dir = exit_dir
        arrows_placed = 1
        mirrors_placed = 0
        path_cells = [current_pos]
        success = True
        
        while arrows_placed < num_arrows:
            step_length = random.randint(1, 3)
            segment_ok = True
            temp_visited = []
            
            pos = current_pos
            for _ in range(step_length):
                pos = (pos[0] - current_dir[0], pos[1] - current_dir[1])
                if not (0 <= pos[0] < GRID_COLS and 0 <= pos[1] < GRID_ROWS):
                    segment_ok = False
                    break
                if pos in visited:
                    segment_ok = False
                    break
                temp_visited.append(pos)
                
            if not segment_ok:
                success = False
                break
                
            for p in temp_visited:
                visited.add(p)
                path_cells.append(p)
            current_pos = pos
            
            if mirrors_placed < num_mirrors and random.random() < 0.5:
                new_dir = random.choice([
                    (current_dir[1], current_dir[0]), 
                    (-current_dir[1], -current_dir[0])
                ])
                
                if new_dir == (-current_dir[1], -current_dir[0]):
                    m_type = '/'
                else:
                    m_type = '\\'
                    
                grid[current_pos] = {'type': 'mirror', 'mirror_type': m_type}
                current_dir = new_dir
                mirrors_placed += 1
                
                step_length = random.randint(1, 2)
                segment_ok = True
                temp_visited = []
                pos = current_pos
                for _ in range(step_length):
                    pos = (pos[0] - current_dir[0], pos[1] - current_dir[1])
                    if not (0 <= pos[0] < GRID_COLS and 0 <= pos[1] < GRID_ROWS):
                        segment_ok = False
                        break
                    if pos in visited:
                        segment_ok = False
                        break
                    temp_visited.append(pos)
                    
                if not segment_ok:
                    success = False
                    break
                    
                for p in temp_visited:
                    visited.add(p)
                    path_cells.append(p)
                current_pos = pos
                
            grid[current_pos] = {'type': 'arrow', 'dir': current_dir, 'is_start': False}
            arrows_placed += 1
            
        if success and arrows_placed == num_arrows:
            start_pos = current_pos
            grid[start_pos]['is_start'] = True
            
            num_decoys = min(level_idx // 2, 4)
            empty_cells = []
            for gc in range(GRID_COLS):
                for gr in range(GRID_ROWS):
                    if (gc, gr) not in visited:
                        empty_cells.append((gc, gr))
                        
            random.shuffle(empty_cells)
            temp_grid = grid.copy()
            
            decoy_count = 0
            while decoy_count < num_decoys and empty_cells:
                cell = empty_cells.pop()
                if random.random() < 0.5:
                    decoy_dir = random.choice([(0, -1), (0, 1), (-1, 0), (1, 0)])
                    temp_grid[cell] = {'type': 'arrow', 'dir': decoy_dir, 'is_start': False}
                else:
                    decoy_m = random.choice(['/', '\\'])
                    temp_grid[cell] = {'type': 'mirror', 'mirror_type': decoy_m}
                decoy_count += 1
            
            sol_status, _, _ = simulate_path(temp_grid, start_pos[0], start_pos[1])
            if not sol_status:
                continue
                
            decoy_solves = False
            for pos, item in temp_grid.items():
                if item['type'] == 'arrow' and pos != start_pos:
                    ds, _, _ = simulate_path(temp_grid, pos[0], pos[1])
                    if ds:
                        decoy_solves = True
                        break
                        
            if not decoy_solves:
                return temp_grid, start_pos
                    
    return get_fallback_grid()

def get_fallback_grid():
    grid = {
        (1, 2): {'type': 'arrow', 'dir': (1, 0), 'is_start': True},
        (3, 2): {'type': 'mirror', 'mirror_type': '\\'},
        (3, 5): {'type': 'arrow', 'dir': (0, 1), 'is_start': False},
        (3, 7): {'type': 'mirror', 'mirror_type': '/'},
        (1, 7): {'type': 'arrow', 'dir': (-1, 0), 'is_start': False},
    }
    return grid, (1, 2)


# --- MAIN GAME CONTROLLER ---
class Game:
    def __init__(self):
        self.high_score, self.level, self.score = load_save_data()
        self.state = 'MENU'
        
        self.grid = {}
        self.start_arrow_pos = None
        self.active_arrows = {}
        self.mirrors = []
        
        self.laser_segments = []
        self.active_step_idx = 0
        self.active_step_list = []
        
        self.active_seg_start_cell = None
        self.active_seg_end_cell = None
        self.active_seg_progress = 0.0
        self.active_seg_dir = (0, 0)
        self.active_seg_type = ''
        self.laser_success = False
        
        self.pulse_timer = 0
        self.particles = ParticleSystem()
        self.field_widget = None

    def start_new_level(self):
        grid_data, start_pos = generate_solvable_level(self.level)
        self.start_arrow_pos = start_pos
        self.grid = grid_data
        
        self.active_arrows = {}
        self.mirrors = []
        for pos, item in grid_data.items():
            col, row = pos
            if item['type'] == 'arrow':
                self.active_arrows[pos] = {
                    'col': col,
                    'row': row,
                    'dir': item['dir'],
                    'is_start': (pos == start_pos),
                    'active': True
                }
            elif item['type'] == 'mirror':
                self.mirrors.append({
                    'col': col,
                    'row': row,
                    'mirror_type': item['mirror_type']
                })
                
        self.laser_segments = []
        self.particles.particles = []
        self.state = 'PLAYING'
        
        # Trigger layout update and visual stats updates
        app = App.get_running_app()
        if app and app.root and 'game' in app.root.screen_names:
            app.root.get_screen('game').update_stats()

    def retry_level(self):
        for arrow in self.active_arrows.values():
            arrow['active'] = True
        self.laser_segments = []
        self.particles.particles = []
        self.state = 'PLAYING'

    def handle_grid_click(self, col, row):
        arr_pos = (col, row)
        print(f"[DEBUG] handle_grid_click: clicked cell={arr_pos}, active_arrows={list(self.active_arrows.keys())}")
        if arr_pos in self.active_arrows:
            print(f"[DEBUG] handle_grid_click: arrow active={self.active_arrows[arr_pos]['active']}")
        if arr_pos in self.active_arrows and self.active_arrows[arr_pos]['active']:
            success, steps, hit_arrows = simulate_path(self.grid, arr_pos[0], arr_pos[1])
            self.laser_success = success
            self.active_step_list = steps
            self.active_step_idx = 0
            print(f"[DEBUG] handle_grid_click: simulate path success={success}, steps={len(steps)}")
            
            if steps:
                self.state = 'ANIMATING_LASER'
                self.setup_laser_step(0)
            else:
                self.trigger_gameover(False)

    def setup_laser_step(self, idx):
        if idx >= len(self.active_step_list):
            self.trigger_gameover(self.laser_success)
            return

        step = self.active_step_list[idx]
        self.active_seg_start_cell = step['start_cell']
        self.active_seg_end_cell = step['end_cell']
        self.active_seg_type = step['type']
        self.active_seg_dir = step['dir']
        self.active_seg_progress = 0.0
        self.active_step_idx = idx

        start_cell = step['start_cell']
        if start_cell in self.active_arrows:
            self.active_arrows[start_cell]['active'] = False
            if self.field_widget:
                cx, cy, _ = self.field_widget.get_cell_center(start_cell[0], start_cell[1])
                self.particles.spawn(cx, cy, (0, 217, 255), 12, 3.5)

    def trigger_gameover(self, is_win):
        self.state = 'GAMEOVER'
        if is_win:
            self.score += 5
            self.level += 1
            if self.score > self.high_score:
                self.high_score = self.score
        else:
            self.score = 0
            
        write_save_data(self.high_score, self.level, self.score)
        
        # Display gameover overlay panel
        app = App.get_running_app()
        if app and app.root and 'game' in app.root.screen_names:
            app.root.get_screen('game').show_gameover_overlay(is_win)

    def update(self, dt):
        dt = min(dt, 0.1) # Bound dt to prevent skips
        self.pulse_timer += dt
        
        if self.state == 'ANIMATING_LASER':
            anim_speed = 6.0 
            self.active_seg_progress += dt * anim_speed
            
            if self.field_widget:
                cx1, cy1, cs = self.field_widget.get_cell_center(self.active_seg_start_cell[0], self.active_seg_start_cell[1])
                if self.active_seg_type == 'exit':
                    cx2, cy2 = self.field_widget.get_exit_pixels(self.active_seg_end_cell, self.active_seg_dir, cs)
                else:
                    cx2, cy2, _ = self.field_widget.get_cell_center(self.active_seg_end_cell[0], self.active_seg_end_cell[1])
                    
                progress = min(self.active_seg_progress, 1.0)
                tip_x = cx1 + (cx2 - cx1) * progress
                tip_y = cy1 + (cy2 - cy1) * progress
                
                # Spawn glowing tip trail particles
                color = (0, 255, 136) if self.laser_success else (255, 51, 102)
                self.particles.spawn(tip_x, tip_y, color, 1, 0.8)
            
            if self.active_seg_progress >= 1.0:
                self.laser_segments.append((
                    self.active_seg_start_cell,
                    self.active_seg_end_cell,
                    self.active_seg_type,
                    self.active_seg_dir
                ))
                
                step = self.active_step_list[self.active_step_idx]
                if self.field_widget:
                    cx2, cy2, cs = self.field_widget.get_cell_center(step['end_cell'][0], step['end_cell'][1])
                    if step['type'] == 'path':
                        end_cell = step['end_cell']
                        if end_cell in self.grid and self.grid[end_cell]['type'] == 'mirror':
                            self.particles.spawn(cx2, cy2, (255, 200, 0), 8, 2.5)
                    elif step['type'] == 'crash':
                        self.particles.spawn(cx2, cy2, (255, 51, 102), 25, 4.5)
                
                self.setup_laser_step(self.active_step_idx + 1)
                
        self.particles.update(dt)


# --- CUSTOM WIDGETS ---

class NeonButton(Button):
    border_color = ListProperty([0, 217/255, 255/255, 1.0])
    bg_color = ListProperty([0, 217/255, 255/255, 0.15])
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = [0, 0, 0, 0] # transparent normal background
        self.font_name = 'Orbitron'
        self.bold = True
        self.bind(pos=self.update_canvas, size=self.update_canvas, state=self.update_canvas)
        
    def update_canvas(self, *args):
        if self.width < 22 or self.height < 22:
            return
        self.canvas.before.clear()
        with self.canvas.before:
            # Semi-transparent background
            alpha = 0.35 if self.state == 'down' else 0.15
            Color(self.bg_color[0], self.bg_color[1], self.bg_color[2], alpha)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[10])
            
            # Glowing border outline
            border_width = 3 if self.state == 'down' else 1.8
            Color(*self.border_color)
            Line(rounded_rect=(self.pos[0], self.pos[1], self.size[0], self.size[1], 10), width=border_width)


class HeaderPanel(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.padding = [20, 15, 20, 15]
        self.bg_canvas = InstructionGroup()
        self.canvas.before.add(self.bg_canvas)
        self.bind(pos=self.draw_bg, size=self.draw_bg)
        self.build_ui()
        
    def draw_bg(self, *args):
        if self.width <= 0 or self.height <= 0:
            return
        self.bg_canvas.clear()
        self.bg_canvas.add(Color(*COLOR_PANEL))
        self.bg_canvas.add(Rectangle(pos=self.pos, size=self.size))
    
        # Glowing bottom divider line
        self.bg_canvas.add(Color(0, 217/255, 255/255, 0.4))
        self.bg_canvas.add(Line(points=[self.x, self.y, self.x + self.width, self.y], width=1.5))
            
    def build_ui(self):
        # Stats layout
        left_side = BoxLayout(orientation='vertical', spacing=2, size_hint_x=0.75)
        
        self.lbl_level = Label(text="LEVEL 1", font_size=20, font_name='Orbitron', bold=True, color=COLOR_NEON_BLUE, halign='left', valign='middle')
        self.lbl_level.bind(size=self.lbl_level.setter('text_size'))
        
        self.lbl_score = Label(text="SCORE: 0", font_size=18, font_name='Orbitron', bold=True, color=COLOR_TEXT, halign='left', valign='middle')
        self.lbl_score.bind(size=self.lbl_score.setter('text_size'))
        
        self.lbl_hi = Label(text="HI: 0", font_size=13, font_name='Orbitron', color=COLOR_MIRROR, halign='left', valign='middle')
        self.lbl_hi.bind(size=self.lbl_hi.setter('text_size'))
        
        left_side.add_widget(self.lbl_level)
        left_side.add_widget(self.lbl_score)
        left_side.add_widget(self.lbl_hi)
        self.add_widget(left_side)
        
        # Home navigation button
        right_side = BoxLayout(size_hint_x=0.25, pos_hint={'center_y': 0.5})
        right_side.add_widget(Widget()) # acts as spacer to push home button to the right
        btn_home = NeonButton(text="X", border_color=COLOR_NEON_RED, bg_color=COLOR_NEON_RED, size_hint=(None, None), size=(44, 44))
        btn_home.bind(on_release=self.go_home)
        right_side.add_widget(btn_home)
        self.add_widget(right_side)
        
    def go_home(self, instance):
        app = App.get_running_app()
        app.game.state = 'MENU'
        app.root.current = 'menu'


class GameField(Widget):
    def __init__(self, game, **kwargs):
        super().__init__(**kwargs)
        self.game = game
        self.game.field_widget = self
        
    def get_cell_center(self, col, row):
        # Coordinates mapping taking Kivy y-axis (bottom-up) into account
        cx = self.grid_x + col * self.cell_size + self.cell_size / 2
        cy = self.grid_y + (GRID_ROWS - 1 - row) * self.cell_size + self.cell_size / 2
        return cx, cy, self.cell_size

    def get_exit_pixels(self, end_cell, direction, cell_size):
        col, row = end_cell
        prev_col = col - direction[0]
        prev_row = row - direction[1]
        cx, cy, _ = self.get_cell_center(prev_col, prev_row)
        
        grid_left = self.grid_x
        grid_right = self.grid_x + self.actual_grid_w
        grid_bottom = self.grid_y
        grid_top = self.grid_y + self.actual_grid_h
        
        # row increases down in logic (which corresponds to decreasing Kivy y)
        if direction == (1, 0): # RIGHT
            return grid_right, cy
        elif direction == (-1, 0): # LEFT
            return grid_left, cy
        elif direction == (0, 1): # DOWN
            return cx, grid_bottom
        else: # UP
            return cx, grid_top

    def layout_grid(self):
        w, h = self.size
        # Center grid horizontally with GRID_MARGIN left/right, no vertical margin constraints
        self.cell_size = min((w - 2 * GRID_MARGIN) / GRID_COLS, h / GRID_ROWS)
        self.actual_grid_w = self.cell_size * GRID_COLS
        self.actual_grid_h = self.cell_size * GRID_ROWS
        
        # Center horizontally and vertically within GameField
        self.grid_x = self.x + GRID_MARGIN + (w - 2 * GRID_MARGIN - self.actual_grid_w) / 2
        self.grid_y = self.y + (h - self.actual_grid_h) / 2

    def on_touch_down(self, touch):
        print(f"[DEBUG] touch_down: pos={touch.pos}, self.pos={self.pos}, self.size={self.size}, state={self.game.state}")
        if not self.collide_point(*touch.pos):
            print(f"[DEBUG] touch_down: collide_point failed")
            return False
            
        if self.game.state != 'PLAYING':
            print(f"[DEBUG] touch_down: state is not PLAYING")
            return False
            
        self.layout_grid()
        tx, ty = touch.pos
        print(f"[DEBUG] touch_down: grid bounds: x=[{self.grid_x}, {self.grid_x + self.actual_grid_w}], y=[{self.grid_y}, {self.grid_y + self.actual_grid_h}]")
        
        if self.grid_x <= tx < self.grid_x + self.actual_grid_w and self.grid_y <= ty < self.grid_y + self.actual_grid_h:
            col = int((tx - self.grid_x) / self.cell_size)
            row = GRID_ROWS - 1 - int((ty - self.grid_y) / self.cell_size)
            
            col = max(0, min(col, GRID_COLS - 1))
            row = max(0, min(row, GRID_ROWS - 1))
            print(f"[DEBUG] touch_down: clicked grid cell col={col}, row={row}")
            
            self.game.handle_grid_click(col, row)
            return True
        else:
            print(f"[DEBUG] touch_down: clicked outside grid area")
        return False

    def draw_canvas(self):
        self.layout_grid()
        if self.cell_size <= 0 or self.width <= 0 or self.height <= 0:
            return
        self.canvas.clear()
        
        with self.canvas:
            # Space Background
            Color(*COLOR_BG)
            Rectangle(pos=self.pos, size=self.size)
            
            # --- DRAW ACTIVE ARROWS ---
            for pos, arrow in self.game.active_arrows.items():
                if not arrow['active']:
                    continue
                cx, cy, cs = self.get_cell_center(arrow['col'], arrow['row'])
                
                # Math angle rotation based on direction
                # Invert logic dy since Kivy y increases upwards
                kivy_dy = -arrow['dir'][1]
                angle = math.atan2(kivy_dy, arrow['dir'][0])
                
                size = cs * 0.45
                points = [
                    (-size / 2, -size / 3),
                    (size / 2, 0),
                    (-size / 2, size / 3),
                    (-size / 3, 0)
                ]
                
                cos_a = math.cos(angle)
                sin_a = math.sin(angle)
                rotated_points = []
                for px, py in points:
                    rx = px * cos_a - py * sin_a
                    ry = px * sin_a + py * cos_a
                    rotated_points.append(cx + rx)
                    rotated_points.append(cy + ry)
                
                # Glowing backing Arrow
                Color(0.86, 0.86, 0.92, 0.25)
                Line(points=rotated_points, close=True, width=3)
                
                # Foreground Arrow line
                Color(1, 1, 1, 1)
                Line(points=rotated_points, close=True, width=1.3)
                
                # Arrow center node
                Color(0.86, 0.86, 0.92, 1)
                Ellipse(pos=(cx - 3, cy - 3), size=(6, 6))

            # --- DRAW MIRRORS ---
            for mirror in self.game.mirrors:
                cx, cy, cs = self.get_cell_center(mirror['col'], mirror['row'])
                length = cs * 0.57
                half = length / 2
                
                if mirror['mirror_type'] == '/':
                    start_x, start_y = cx - half, cy - half
                    end_x, end_y = cx + half, cy + half
                else: # '\'
                    start_x, start_y = cx - half, cy + half
                    end_x, end_y = cx + half, cy - half
                
                # Mirror Glow
                Color(1.0, 0.78, 0.0, 0.3)
                Line(points=[start_x, start_y, end_x, end_y], width=6)
                
                # Mirror main body
                Color(1.0, 0.78, 0.0, 1.0)
                Line(points=[start_x, start_y, end_x, end_y], width=2.5)
                
                # Mirror Caps
                Color(1, 1, 1, 1)
                Ellipse(pos=(start_x - 3, start_y - 3), size=(6, 6))
                Ellipse(pos=(end_x - 3, end_y - 3), size=(6, 6))

            # --- DRAW COMPLETED LASER PATHS ---
            laser_color = COLOR_NEON_GREEN if self.game.laser_success else COLOR_NEON_RED
            for start_cell, end_cell, seg_type, seg_dir in self.game.laser_segments:
                cx1, cy1, cs = self.get_cell_center(start_cell[0], start_cell[1])
                if seg_type == 'exit':
                    cx2, cy2 = self.get_exit_pixels(end_cell, seg_dir, cs)
                else:
                    cx2, cy2, _ = self.get_cell_center(end_cell[0], end_cell[1])
                
                self.draw_glow_line(cx1, cy1, cx2, cy2, laser_color)

            # --- DRAW ANIMATING LASER ---
            if self.game.state == 'ANIMATING_LASER' and self.game.active_seg_start_cell:
                cx1, cy1, cs = self.get_cell_center(self.game.active_seg_start_cell[0], self.game.active_seg_start_cell[1])
                if self.game.active_seg_type == 'exit':
                    cx2, cy2 = self.get_exit_pixels(self.game.active_seg_end_cell, self.game.active_seg_dir, cs)
                else:
                    cx2, cy2, _ = self.get_cell_center(self.game.active_seg_end_cell[0], self.game.active_seg_end_cell[1])
                
                progress = min(self.game.active_seg_progress, 1.0)
                tip_x = cx1 + (cx2 - cx1) * progress
                tip_y = cy1 + (cy2 - cy1) * progress
                
                self.draw_glow_line(cx1, cy1, tip_x, tip_y, laser_color)

            # --- DRAW PARTICLES ---
            for p in self.game.particles.particles:
                alpha = p.life / p.max_life
                if alpha > 0:
                    Color(p.color[0]/255, p.color[1]/255, p.color[2]/255, alpha)
                    Ellipse(pos=(p.x - p.size, p.y - p.size), size=(p.size * 2, p.size * 2))

    def draw_glow_line(self, x1, y1, x2, y2, color):
        # Outer soft glow layer
        Color(color[0], color[1], color[2], 0.12)
        Line(points=[x1, y1, x2, y2], width=8)
        
        # Inner soft glow layer
        Color(color[0], color[1], color[2], 0.38)
        Line(points=[x1, y1, x2, y2], width=4)
        
        # Core sharp white tracer line
        Color(1, 1, 1, 1)
        Line(points=[x1, y1, x2, y2], width=1.3)


class GameOverOverlay(RelativeLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.opacity = 0
        self.disabled = True
        self.bg_canvas = InstructionGroup()
        self.canvas.before.add(self.bg_canvas)
        
        # Central modal panel
        self.panel = RelativeLayout(size_hint=(None, None), size=(320, 360))
        self.panel_bg_canvas = InstructionGroup()
        self.panel.canvas.before.add(self.panel_bg_canvas)
        self.add_widget(self.panel)
        self.panel.bind(size=self.draw_panel_bg)
        self.bind(size=self.draw_overlay_bg)
        
        # Layout inside panel
        content = BoxLayout(orientation='vertical', padding=25, spacing=15, size_hint=(1, 1))
        
        self.lbl_title = Label(text="SUCCESS!", font_size=28, font_name='Orbitron', bold=True, halign='center', size_hint_y=0.22)
        self.lbl_desc = Label(text="", font_size=15, font_name='Orbitron', halign='center', color=COLOR_TEXT, size_hint_y=0.4)
        
        buttons = BoxLayout(orientation='vertical', spacing=12, size_hint_y=0.38)
        self.btn_action = NeonButton(text="", size_hint=(1, None), height=45)
        self.btn_action.bind(on_release=self.on_action)
        
        btn_menu = NeonButton(text="MAIN MENU", border_color=COLOR_NEON_RED, bg_color=COLOR_NEON_RED, size_hint=(1, None), height=45)
        btn_menu.bind(on_release=self.on_menu)
        
        buttons.add_widget(self.btn_action)
        buttons.add_widget(btn_menu)
        
        content.add_widget(self.lbl_title)
        content.add_widget(self.lbl_desc)
        content.add_widget(buttons)
        
        self.panel.add_widget(content)

    def draw_overlay_bg(self, *args):
        if self.width <= 0 or self.height <= 0:
            return
        self.bg_canvas.clear()
        self.bg_canvas.add(Color(8/255, 8/255, 12/255, 0.75))
        self.bg_canvas.add(Rectangle(pos=(0, 0), size=self.size))
            
    def draw_panel_bg(self, *args):
        if self.opacity == 0:
            self.panel.x = (self.width - self.panel.width) / 2
            self.panel.y = self.height

    def show(self, is_win):
        self.is_win = is_win
    
    # Re-center overlay layout elements
        self.panel.x = (self.width - self.panel.width) / 2
        self.panel.y = self.height
    
        if is_win:
            self.lbl_title.text = "SUCCESS!"
            self.lbl_title.color = COLOR_NEON_GREEN
            self.lbl_desc.text = "All nodes cleared successfully!\n+5 points earned."
        
            self.panel_bg_canvas.clear()
            self.panel_bg_canvas.add(Color(*COLOR_PANEL))
            self.panel_bg_canvas.add(RoundedRectangle(pos=(0, 0), size=self.panel.size, radius=[15]))
            self.panel_bg_canvas.add(Color(*COLOR_NEON_GREEN))
            self.panel_bg_canvas.add(Line(rounded_rect=(0, 0, self.panel.width, self.panel.height, 15), width=3))
        
            self.btn_action.text = "NEXT LEVEL"
            self.btn_action.border_color = COLOR_NEON_GREEN
            self.btn_action.bg_color = COLOR_NEON_GREEN
        else:
            self.lbl_title.text = "LEVEL FAILED"
            self.lbl_title.color = COLOR_NEON_RED
            self.lbl_desc.text = "Laser crashed or went offscreen\nbefore triggering all arrows.\n\nScore streak reset to 0."
        
            self.panel_bg_canvas.clear()
            self.panel_bg_canvas.add(Color(*COLOR_PANEL))
            self.panel_bg_canvas.add(RoundedRectangle(pos=(0, 0), size=self.panel.size, radius=[15]))
            self.panel_bg_canvas.add(Color(*COLOR_NEON_RED))
            self.panel_bg_canvas.add(Line(rounded_rect=(0, 0, self.panel.width, self.panel.height, 15), width=3))
        
            self.btn_action.text = "RETRY"
            self.btn_action.border_color = COLOR_NEON_BLUE
            self.btn_action.bg_color = COLOR_NEON_BLUE
        
        self.opacity = 1
        self.disabled = False
    
    # Dropdown slide animation with bounce
        from kivy.animation import Animation
        target_y = (self.height - self.panel.height) / 2
        anim = Animation(y=target_y, t='out_bounce', duration=0.8)
        anim.start(self.panel)

    def hide(self):
        self.opacity = 0
        self.disabled = True

    def on_action(self, instance):
        self.hide()
        app = App.get_running_app()
        if self.is_win:
            app.game.start_new_level()
        else:
            app.game.retry_level()

    def on_menu(self, instance):
        self.hide()
        app = App.get_running_app()
        app.game.state = 'MENU'
        app.root.current = 'menu'


# --- SCREENS ---

class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bg_canvas = InstructionGroup()
        self.canvas.before.add(self.bg_canvas)
        self.bind(size=self.draw_bg, pos=self.draw_bg)
        self.build_ui()
        
    def on_pre_enter(self):
        # Refresh scores upon returning to main menu
        app = App.get_running_app()
        self.lbl_score.text = f"SCORE: {app.game.score}"
        self.lbl_level.text = f"LEVEL: {app.game.level}"
        self.lbl_hi.text = f"HIGH SCORE: {app.game.high_score}"

    def draw_bg(self, *args):
        if self.width <= 0 or self.height <= 0:
            return
        self.bg_canvas.clear()
        
        # Background Dark Space
        self.bg_canvas.add(Color(*COLOR_BG))
        self.bg_canvas.add(Rectangle(pos=(0, 0), size=self.size))
    
        # Glowing large space orbits (accents)
        w, h = self.size
        cx1, cy1 = w * 0.25, h * 0.66
        r1, max_r1 = 10, 100
        for r in range(max_r1, r1, -4):
            a = 0.08 * (1.0 - (r - r1) / (max_r1 - r1))
            self.bg_canvas.add(Color(0, 0.31, 0.59, a))
            self.bg_canvas.add(Ellipse(pos=(cx1 - r, cy1 - r), size=(r * 2, r * 2)))
        
        cx2, cy2 = w * 0.75, h * 0.33
        r2, max_r2 = 10, 120
        for r in range(max_r2, r2, -4):
            a = 0.08 * (1.0 - (r - r2) / (max_r2 - r2))
            self.bg_canvas.add(Color(0.59, 0, 0.31, a))
            self.bg_canvas.add(Ellipse(pos=(cx2 - r, cy2 - r), size=(r * 2, r * 2)))
        
        # Neon cyan divider line
        y_line = h * 0.65
        self.bg_canvas.add(Color(0, 217/255, 255/255, 0.1))
        self.bg_canvas.add(Line(points=[80, y_line, w - 80, y_line], width=6))
        self.bg_canvas.add(Color(0, 217/255, 255/255, 0.45))
        self.bg_canvas.add(Line(points=[80, y_line, w - 80, y_line], width=3))
        self.bg_canvas.add(Color(1, 1, 1, 1))
        self.bg_canvas.add(Line(points=[80, y_line, w - 80, y_line], width=1))

    def build_ui(self):
        layout = RelativeLayout()
        
        # Left stats panel
        stats_layout = BoxLayout(orientation='vertical', size_hint=(None, None), size=(300, 100), pos_hint={'x': 0.06, 'top': 0.95}, spacing=4)
        self.lbl_score = Label(text="SCORE: 0", font_size=18, font_name='Orbitron', bold=True, color=COLOR_TEXT, halign='left', valign='middle')
        self.lbl_score.bind(size=self.lbl_score.setter('text_size'))
        self.lbl_level = Label(text="LEVEL: 1", font_size=18, font_name='Orbitron', bold=True, color=COLOR_NEON_BLUE, halign='left', valign='middle')
        self.lbl_level.bind(size=self.lbl_level.setter('text_size'))
        self.lbl_hi = Label(text="HIGH SCORE: 0", font_size=18, font_name='Orbitron', bold=True, color=COLOR_MIRROR, halign='left', valign='middle')
        self.lbl_hi.bind(size=self.lbl_hi.setter('text_size'))
        
        stats_layout.add_widget(self.lbl_score)
        stats_layout.add_widget(self.lbl_level)
        stats_layout.add_widget(self.lbl_hi)
        layout.add_widget(stats_layout)
        
        # Glow title shadow layout
        title_box = RelativeLayout(size_hint=(1, 0.2), pos_hint={'x': 0, 'top': 0.81})
        shadow_offset = 2
        for ox, oy in [(-shadow_offset, 0), (shadow_offset, 0), (0, -shadow_offset), (0, shadow_offset)]:
            g_lbl = Label(text="LASER TRIGGER", font_size=42, font_name='Orbitron', bold=True, color=COLOR_NEON_BLUE, pos_hint={'center_x': 0.5 + ox/450.0, 'center_y': 0.5 + oy/820.0})
            title_box.add_widget(g_lbl)
            
        t_lbl = Label(text="LASER TRIGGER", font_size=42, font_name='Orbitron', bold=True, color=COLOR_GLOW_WHITE, pos_hint={'center_x': 0.5, 'center_y': 0.5})
        title_box.add_widget(t_lbl)
        layout.add_widget(title_box)
        
        # Subtitle description
        sub_lbl = Label(text="Chain Reaction Puzzle Game", font_size=16, font_name='Orbitron', color=COLOR_NEON_BLUE, pos_hint={'center_x': 0.5, 'top': 0.62}, size_hint=(1, 0.05))
        layout.add_widget(sub_lbl)
        
        # Control Buttons
        btn_layout = BoxLayout(orientation='vertical', size_hint=(None, None), size=(260, 140), pos_hint={'center_x': 0.5, 'y': 0.22}, spacing=20)
        btn_start = NeonButton(text="START GAME", border_color=COLOR_NEON_BLUE, bg_color=COLOR_NEON_BLUE, size_hint=(1, None), height=52)
        btn_start.bind(on_release=self.start_game)
        
        btn_exit = NeonButton(text="EXIT", border_color=COLOR_NEON_RED, bg_color=COLOR_NEON_RED, size_hint=(1, None), height=52)
        btn_exit.bind(on_release=self.exit_game)
        
        btn_layout.add_widget(btn_start)
        btn_layout.add_widget(btn_exit)
        layout.add_widget(btn_layout)
        
        self.add_widget(layout)
        
    def start_game(self, instance):
        app = App.get_running_app()
        app.game.start_new_level()
        self.manager.current = 'game'
        
    def exit_game(self, instance):
        App.get_running_app().stop()


class GameScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
        
    def build_ui(self):
        # Layout container for Header and GameField
        layout = BoxLayout(orientation='vertical')
        
        # Header (top 120dp panel)
        self.header = HeaderPanel(size_hint=(1, None), height=120)
        layout.add_widget(self.header)
        
        # GameField (takes remaining vertical space)
        app = App.get_running_app()
        self.field = GameField(game=app.game, size_hint=(1, 1))
        layout.add_widget(self.field)
        
        # Add layout directly to Screen
        self.add_widget(layout)
        
        # Modal Overlay on very top directly on Screen
        self.overlay = GameOverOverlay(size_hint=(1, 1))
        self.add_widget(self.overlay)
        
    def on_enter(self):
        # Start tick updates when entering the screen
        self.field.layout_grid()
        self.overlay.hide()
        self.update_stats()
        Clock.schedule_interval(self.tick_update, 1/60.0)
        
    def on_leave(self):
        # Stop tick updates
        Clock.unschedule(self.tick_update)

    def tick_update(self, dt):
        app = App.get_running_app()
        app.game.update(dt)
        self.field.draw_canvas()
        
    def update_stats(self):
        app = App.get_running_app()
        self.header.lbl_level.text = f"LEVEL {app.game.level}"
        self.header.lbl_score.text = f"SCORE: {app.game.score}"
        self.header.lbl_hi.text = f"HI: {app.game.high_score}"

    def show_gameover_overlay(self, is_win):
        self.overlay.show(is_win)
        self.update_stats()


# --- KIVY APP ---

class LaserTriggerApp(App):
    def build(self):
        self.game = Game()
        
        # Setup Screen Manager
        sm = ScreenManager()
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(GameScreen(name='game'))
        
        return sm


if __name__ == "__main__":
    LaserTriggerApp().run()
