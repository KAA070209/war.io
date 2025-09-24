import math
import random
import json
import os
import sys
import hashlib
import mysql.connector
import pygame
from pygame.math import Vector2

# MySQL connection
def get_db_connection():
    """Establishes and returns a MySQL database connection."""
    try:
        return mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='war_game'
        )
    except mysql.connector.Error as e:
        print(f"Database connection failed: {e}. Running without database features.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during database connection: {e}. Running without database features.")
        return None

def create_tables():
    """Creates necessary tables in the database if they don't exist."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_data (
                    user_id INT PRIMARY KEY,
                    coins INT DEFAULT 0,
                    unlocked JSON,
                    upgrades JSON,
                    score INT DEFAULT 0,
                    kills INT DEFAULT 0,
                    weapon VARCHAR(50) DEFAULT 'pistol',
                    ammo JSON,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS leaderboard (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255),
                    score INT,
                    kills INT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    permissions JSON DEFAULT '{}'
                )
            ''')
            conn.commit()
            cursor.close()
            conn.close()
        except mysql.connector.Error as e:
            print(f"Error creating tables: {e}. Running without database features.")
        except Exception as e:
            print(f"An unexpected error occurred during table creation: {e}. Running without database features.")
    else:
        print("No database connection to create tables.")

# --------- Konfigurasi ----------
WIDTH = 1200
HEIGHT = 700

# Add variables to track current window size for responsiveness
current_width = WIDTH
current_height = HEIGHT
FPS = 60

PLAYER_SIZE = 28
PLAYER_SPEED = 350  # Player speed in pixels per second
BULLET_SPEED = 700  # Increased bullet speed for more responsive shooting
ENEMY_SPEED = 100   # Enemy speed in pixels per second, slower than player but faster than before
ENEMY_SPAWN_INTERVAL = 1200  # ms
PARTICLE_COUNT = 16

# Senjata spesifik / constants
SHOTGUN_SPREAD = 0.35
EXPLOSION_RADIUS = 80
EXPLOSION_DAMAGE = 40

MAX_LEADERBOARD = 10

# Warna
WHITE = (245, 245, 245)
BLACK = (10, 10, 10)
RED = (200, 20, 20)
DARK_RED = (120, 0, 0)
GREEN = (60, 180, 75)
YELLOW = (240, 200, 20)
GRAY = (120, 120, 120)
BG = (18, 24, 32)
ORANGE = (255, 140, 0)
PURPLE = (170, 0, 170)
BLUE = (50, 150, 250)
CYAN = (80, 200, 220)
LIGHT_BLUE = (100, 100, 255) # For rain
MAGENTA = (255, 0, 255) # For TeleportingEnemy

pygame.init()
try:
    pygame.mixer.init()
except Exception as e:
    print(f"Audio initialization failed: {e}. Running without sound.")
# Load background music
try:
    pygame.mixer.music.load('bg_music.mp3')
    pygame.mixer.music.set_volume(0.3)
    pygame.mixer.music.play(-1)
except:
    print("Background music not found.")
# Load sound effects
try:
    shoot_sound = pygame.mixer.Sound('shoot.wav')
    enemy_death_sound = pygame.mixer.Sound('enemy_death.wav')
    player_hurt_sound = pygame.mixer.Sound('player_hurt.wav')
    explosion_sound = pygame.mixer.Sound('explosion.wav')
    powerup_sound = pygame.mixer.Sound('powerup.wav')
    dash_sound = pygame.mixer.Sound('dash.wav')
    shield_sound = pygame.mixer.Sound('shield.wav')
except:
    shoot_sound = None
    enemy_death_sound = None
    player_hurt_sound = None
    explosion_sound = None
    powerup_sound = None
    dash_sound = None
    shield_sound = None
    print("Some sound effects not found.")
fullscreen = False
windowed_size = (WIDTH, HEIGHT)
screen = pygame.display.set_mode((current_width, current_height), pygame.RESIZABLE)
pygame.display.set_caption("War.io")
clock = pygame.time.Clock()
create_tables()
# We'll create fonts on demand in draw_text for variable sizes
base_font_name = "consolas"
if base_font_name not in pygame.font.get_fonts():
    base_font_name = pygame.font.get_default_font()

# Add event handler for window resize to update WIDTH and HEIGHT
def handle_window_resize(event):
    """Handles window resize events, updating global dimensions and screen."""
    global current_width, current_height, screen
    current_width, current_height = event.w, event.h
    screen = pygame.display.set_mode((current_width, current_height), pygame.RESIZABLE)

# ---------------- Leaderboard helpers ----------------
def load_leaderboard():
    """Loads leaderboard data from the database."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name, score, kills FROM leaderboard ORDER BY score DESC, kills DESC LIMIT %s", (MAX_LEADERBOARD,))
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return [{"name": row[0], "score": row[1], "kills": row[2]} for row in rows]
        except mysql.connector.Error as e:
            print(f"Database error loading leaderboard: {e}. Using empty leaderboard.")
            return []
        except Exception as e:
            print(f"An unexpected error occurred loading leaderboard: {e}. Using empty leaderboard.")
            return []
    return []


def save_leaderboard(lb):
    """Saves leaderboard data to the database."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("TRUNCATE TABLE leaderboard") # Clear existing leaderboard
            for entry in lb:
                cursor.execute("INSERT INTO leaderboard (name, score, kills) VALUES (%s, %s, %s)", (entry["name"], entry["score"], entry["kills"]))
            conn.commit()
            cursor.close()
            conn.close()
        except mysql.connector.Error as e:
            print(f"Database error saving leaderboard: {e}. Leaderboard not saved.")
        except Exception as e:
            print(f"An unexpected error occurred saving leaderboard: {e}. Leaderboard not saved.")

# ---------------- User management ----------------
def load_users():
    """Loads user credentials from the database."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT username, password FROM users")
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return {row[0]: row[1] for row in rows}
        except mysql.connector.Error as e:
            print(f"Database error loading users: {e}. Running without user accounts.")
            return {}
        except Exception as e:
            print(f"An unexpected error occurred loading users: {e}. Running without user accounts.")
            return {}
    return {}

def add_user_to_db(username, password):
    """Adds a new user to the database."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
            conn.commit()
        except mysql.connector.Error as e:
            print(f"Error adding user '{username}' to DB: {e}")
        except Exception as e:
            print(f"An unexpected error occurred adding user '{username}' to DB: {e}")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

def load_admins():
    """Loads admin credentials from the database."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT username, password, permissions FROM admins")
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return {row[0]: {"password": row[1], "permissions": json.loads(row[2]) if row[2] else {}} for row in rows}
        except mysql.connector.Error as e:
            print(f"Database error loading admins: {e}. Running without admin features.")
            return {}
        except Exception as e:
            print(f"An unexpected error occurred loading admins: {e}. Running without admin features.")
            return {}
    return {}

def add_admin_to_db(username, password, permissions=None):
    """Adds a new admin to the database."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            permissions_json = json.dumps(permissions if permissions else {})
            cursor.execute("INSERT INTO admins (username, password, permissions) VALUES (%s, %s, %s)", (username, password, permissions_json))
            conn.commit()
        except mysql.connector.Error as e:
            print(f"Error adding admin '{username}' to DB: {e}")
        except Exception as e:
            print(f"An unexpected error occurred adding admin '{username}' to DB: {e}")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

def update_admin_permissions(username, permissions):
    """Updates admin permissions in the database."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            permissions_json = json.dumps(permissions)
            cursor.execute("UPDATE admins SET permissions = %s WHERE username = %s", (permissions_json, username))
            conn.commit()
        except mysql.connector.Error as e:
            print(f"Error updating admin '{username}' permissions: {e}")
        except Exception as e:
            print(f"An unexpected error occurred updating admin '{username}' permissions: {e}")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

def delete_user_from_db(username):
    """Deletes a user from the database (admin function)."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # Get user_id before deleting from users table
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            user_id_row = cursor.fetchone()
            if user_id_row:
                user_id = user_id_row[0]
                cursor.execute("DELETE FROM user_data WHERE user_id = %s", (user_id,))
            cursor.execute("DELETE FROM users WHERE username = %s", (username,))
            conn.commit()
            print(f"User '{username}' and associated data deleted successfully.")
        except mysql.connector.Error as e:
            print(f"Error deleting user '{username}' from DB: {e}")
        except Exception as e:
            print(f"An unexpected error occurred deleting user '{username}' from DB: {e}")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

def get_game_statistics():
    """Gets game statistics for admin panel."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM user_data WHERE score > 0")
            active_users = cursor.fetchone()[0]

            cursor.execute("SELECT SUM(score) FROM user_data")
            total_score = cursor.fetchone()[0] or 0

            cursor.execute("SELECT SUM(kills) FROM user_data")
            total_kills = cursor.fetchone()[0] or 0

            cursor.execute("SELECT COUNT(*) FROM leaderboard")
            leaderboard_count = cursor.fetchone()[0]

            cursor.close()
            conn.close()

            return {
                "total_users": total_users,
                "active_users": active_users,
                "total_score": total_score,
                "total_kills": total_kills,
                "leaderboard_count": leaderboard_count
            }
        except mysql.connector.Error as e:
            print(f"Database error getting statistics: {e}")
            return {}
        except Exception as e:
            print(f"An unexpected error occurred getting statistics: {e}")
            return {}
    return {}

admins = load_admins()
current_admin = None

# ---------------- User game data management ----------------
# Default ammo configuration for new users or when data is missing
default_ammo = {
    "pistol": 999999,
    "shotgun": 30,
    "rocket": 8,
    "machinegun": 150,
    "area_damage": 1,
    "sniper": 12,
    "flamethrower": 80,
    "laser": 40,
    "grenade": 10,
    "plasma": 10,
    "sword": 999999,
    "gravity_gun": 20,
    "railgun": 10,
    "minigun": 200,
    "bfg": 5,
    "freeze_ray": 25,
    "poison_gun": 30,
    "lightning_gun": 15,
    "acid_gun": 20,
    "teleport_gun": 8,
    "black_hole_gun": 6,
    "time_bomb": 12,
    "chain_lightning": 18,
    "homing_missile": 10,
    "energy_sword": 999999,
    "flak_cannon": 25,
    "pulse_rifle": 40,
    "gauss_rifle": 15,
    "cryo_blaster": 20,
    "napalm_launcher": 15,
    "sonic_blaster": 30,
    "disintegration_ray": 8
}

def load_user_data(username):
    """Loads user-specific game data from the database."""
    user_data = {
        "coins": 0,
        "unlocked": set(["pistol"]),
        "upgrades": {},
        "score": 0,
        "kills": 0,
        "weapon": "pistol",
        "ammo": default_ammo.copy()
    }
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            user_id_row = cursor.fetchone()
            if user_id_row:
                user_id = user_id_row[0]
                cursor.execute("SELECT coins, unlocked, upgrades, score, kills, weapon, ammo FROM user_data WHERE user_id = %s", (user_id,))
                row = cursor.fetchone()
                if row:
                    coins_db, unlocked_json, upgrades_json, score_db, kills_db, weapon_db, ammo_json = row
                    user_data["coins"] = coins_db
                    user_data["unlocked"] = set(json.loads(unlocked_json)) if unlocked_json else set(["pistol"])
                    user_data["upgrades"] = json.loads(upgrades_json) if upgrades_json else {}
                    user_data["score"] = score_db
                    user_data["kills"] = kills_db
                    user_data["weapon"] = weapon_db
                    user_data["ammo"] = json.loads(ammo_json) if ammo_json else default_ammo.copy()
            cursor.close()
            conn.close()
        except mysql.connector.Error as e:
            print(f"Database error loading user data for {username}: {e}. Using default data.")
        except json.JSONDecodeError as e:
            print(f"JSON decode error loading user data for {username}: {e}. Using default data for affected fields.")
        except Exception as e:
            print(f"An unexpected error occurred loading user data for {username}: {e}. Using default data.")
    return user_data

def save_user_data(username, user_data):
    """Saves user-specific game data to the database."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            user_id_row = cursor.fetchone()
            if not user_id_row:
                raise ValueError(f"User {username} not found in database.")
            user_id = user_id_row[0]

            # Ensure 'unlocked' is a list for JSON serialization if it's a set
            unlocked_for_db = list(user_data.get("unlocked", set(["pistol"])))

            cursor.execute("""
                INSERT INTO user_data (user_id, coins, unlocked, upgrades, score, kills, weapon, ammo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                coins = VALUES(coins), unlocked = VALUES(unlocked), upgrades = VALUES(upgrades),
                score = VALUES(score), kills = VALUES(kills), weapon = VALUES(weapon), ammo = VALUES(ammo)
            """, (
                user_id,
                user_data.get("coins", 0),
                json.dumps(unlocked_for_db),
                json.dumps(user_data.get("upgrades", {})),
                user_data.get("score", 0),
                user_data.get("kills", 0),
                user_data.get("weapon", "pistol"),
                json.dumps(user_data.get("ammo", default_ammo.copy()))
            ))
            conn.commit()
            cursor.close()
            conn.close()
        except mysql.connector.Error as e:
            print(f"Database error saving user data for {username}: {e}. Data not saved.")
        except ValueError as e:
            print(f"Error: {e}. Data not saved.")
        except Exception as e:
            print(f"An unexpected error occurred saving user data for {username}: {e}. Data not saved.")
    else:
        print("No database connection to save user data.")

def save_coins(coins_val):
    """Saves the current user's coin count to the database."""
    if current_user:
        user_data = load_user_data(current_user)
        user_data["coins"] = coins_val
        save_user_data(current_user, user_data)

def save_unlocked(unlocked_set):
    """Saves the current user's unlocked weapons to the database."""
    if current_user:
        user_data = load_user_data(current_user)
        user_data["unlocked"] = unlocked_set # Expects a set
        save_user_data(current_user, user_data)

def save_upgrades(upgrades_val):
    """Saves the current user's upgrades to the database."""
    if current_user:
        user_data = load_user_data(current_user)
        user_data["upgrades"] = upgrades_val
        save_user_data(current_user, user_data)

users = load_users()
current_user = None
leaderboard = load_leaderboard()

# ---------------- Weapon prices ----------------
weapon_prices = {
    "shotgun": 50,
    "rocket": 100,
    "machinegun": 150,
    "area_damage": 200,
    "sniper": 250,
    "flamethrower": 300,
    "laser": 350,
    "grenade": 400,
    "plasma": 450,
    "sword": 500,
    "gravity_gun": 550,
    "railgun": 600,
    "minigun": 700,
    "bfg": 800,
    "freeze_ray": 680,
    "poison_gun": 690,
    "lightning_gun": 730,
    "acid_gun": 740,
    "teleport_gun": 760,
    "black_hole_gun": 780,
    "time_bomb": 790,
    "chain_lightning": 810,
    "homing_missile": 820,
    "energy_sword": 830,
    "flak_cannon": 840,
    "pulse_rifle": 860,
    "gauss_rifle": 870,
    "cryo_blaster": 880,
    "napalm_launcher": 890,
    "sonic_blaster": 900,
    "disintegration_ray": 950
}

upgrade_prices = {
    "max_hp": 100,
    "speed": 150,
    "dash_cooldown": 200,
    "shield_regen": 250,
    "damage_mult": 300
}

coins = 0
unlocked = set(["pistol"])
upgrades = {}

# Global weather state
is_raining = False
rain_duration = 0
rain_start_time = 0
rain_drops = []
RAIN_SPEED_DEBUFF = 0.85 # REVISI: Mengurangi penalti kecepatan hujan
# Global daily mission state
daily_mission = {"desc": "Bunuh 50 musuh", "target": 50, "progress": 0, "reward": 100, "completed": False}

def qualifies_for_leaderboard(score, kills):
    """Checks if a score qualifies for the leaderboard."""
    # Use current in-memory leaderboard
    if len(leaderboard) < MAX_LEADERBOARD:
        return True
    lb_sorted = sorted(leaderboard, key=lambda e: (e["score"], e["kills"]), reverse=True)
    worst = lb_sorted[-1]
    return (score, kills) > (worst["score"], kills) # Perbaikan: Bandingkan kills juga

def add_to_leaderboard(name, score, kills):
    """Adds or updates an entry in the leaderboard."""
    global leaderboard
    # Check if name already exists
    for entry in leaderboard:
        if entry["name"] == name:
            if (score, kills) > (entry["score"], entry["kills"]):
                entry["score"] = int(score)
                entry["kills"] = int(kills)
                leaderboard = sorted(leaderboard, key=lambda e: (e["score"], e["kills"]), reverse=True)[:MAX_LEADERBOARD]
                save_leaderboard(leaderboard)
            return
    # If not exists, add if qualifies
    if qualifies_for_leaderboard(score, kills):
        leaderboard.append({"name": name, "score": int(score), "kills": int(kills)})
        leaderboard = sorted(leaderboard, key=lambda e: (e["score"], e["kills"]), reverse=True)[:MAX_LEADERBOARD]
        save_leaderboard(leaderboard)

# ---------------- Utility draw ----------------
def draw_text(surf, text, size, x, y, color=WHITE, center=False):
    """Draws text on a surface."""
    # create font with requested size (fallback to default font)
    f = pygame.font.SysFont(base_font_name, int(size))
    txt = f.render(str(text), True, color)
    rect = txt.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surf.blit(txt, rect)

# ---------------- Game Entities ----------------
class Particle:
    """Represents a visual particle effect."""
    def __init__(self, pos, vel, radius, life, color):
        self.pos = Vector2(pos)
        self.vel = Vector2(vel)
        self.radius = radius
        self.life = life
        self.maxlife = life
        self.color = color

    def update(self, dt):
        self.pos += self.vel * dt
        self.life -= dt
        self.vel.y += 9 * dt * 0.6 # Gravity effect

    def draw(self, surf):
        if self.life <= 0:
            return
        t = max(0, self.life / self.maxlife)
        r = max(0.5, int(self.radius * t))
        alpha = int(255 * t)
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        c = (*self.color, alpha)
        pygame.draw.circle(s, c, (r, r), r)
        surf.blit(s, (self.pos.x - r, self.pos.y - r))


class Bullet:
    """Represents a projectile fired in the game."""
    def __init__(self, pos, dir_vec, owner="player", btype="normal",
                 speed=BULLET_SPEED, radius=5, color=YELLOW, damage=18, lifetime=5000):
        self.pos = Vector2(pos)
        if dir_vec.length_squared() == 0:
            dir_vec = Vector2(1, 0)
        self.dir = dir_vec.normalize()
        self.owner = owner
        self.btype = btype
        self.alive = True
        self.vel = self.dir * speed
        self.radius = radius
        self.color = color
        self.damage = damage
        self.spawn_time = pygame.time.get_ticks()
        self.lifetime = lifetime  # ms
        self.timer = None
        self.exploded = False
        if btype == "grenade":
            self.timer = 800
            self.lifetime = 2000

    def update(self, dt):
        self.pos += self.vel * dt
        if self.timer is not None:
            self.timer -= clock.get_time()
            if self.timer <= 0 and not self.exploded:
                self.exploded = True
                self.alive = False # Mark for removal after explosion
        if pygame.time.get_ticks() - self.spawn_time > self.lifetime:
            self.alive = False
        # Remove bullets that go far off-screen
        if (self.pos.x < -120 or self.pos.x > current_width + 120 or
                self.pos.y < -120 or self.pos.y > current_height + 120):
            self.alive = False

    def draw(self, surf):
        pygame.draw.circle(surf, self.color, (int(self.pos.x), int(self.pos.y)), self.radius)


class Entity:
    """Base class for game entities with position, size, health, and color."""
    def __init__(self, x, y, size, color=WHITE, hp=100):
        self.pos = Vector2(x, y)
        self.size = size
        self.color = color
        self.hp = hp
        self.max_hp = hp

    def draw_health_bar(self, surf, width=40, height=6):
        """Draws a health bar above the entity."""
        bar_rect = pygame.Rect(0, 0, width, height)
        bar_rect.center = (int(self.pos.x), int(self.pos.y - self.size - 10))
        pygame.draw.rect(surf, GRAY, bar_rect)
        hp_w = int(width * max(0, self.hp) / self.max_hp)
        hp_rect = pygame.Rect(bar_rect.left, bar_rect.top, hp_w, height)
        pygame.draw.rect(surf, GREEN, hp_rect)
        pygame.draw.rect(surf, BLACK, bar_rect, 1)


class Player(Entity):
    """Represents the player character."""
    def __init__(self, x=current_width//2, y=current_height//2, initial_upgrades=None):
        super().__init__(x, y, PLAYER_SIZE, color=WHITE, hp=100)
        upgrades_data = initial_upgrades if initial_upgrades is not None else upgrades # Use global upgrades if not provided
        self.max_hp = 100 + (50 if upgrades_data.get("max_hp", 0) else 0)
        self.hp = self.max_hp # Player starts with full HP
        self.speed_bonus = 1.2 if upgrades_data.get("speed", 0) else 1.0
        self.dash_cooldown = 3000 * (0.8 if upgrades_data.get("dash_cooldown", 0) else 1.0)
        self.shield_regen_rate = 0.1 * (1.5 if upgrades_data.get("shield_regen", 0) else 1.0)
        self.damage_mult_base = 1.5 if upgrades_data.get("damage_mult", 0) else 1.0
        self.vel = Vector2(0, 0)
        self.last_shot = 0
        self.score = 0
        self.kills = 0
        self.weapon = "pistol"
        self.level = 1

        self.ammo = default_ammo.copy() # Initialize with default ammo

        self.cooldowns = {
            "pistol": 200,
            "shotgun": 450,
            "rocket": 700,
            "machinegun": 70,
            "area_damage": 5000,
            "sniper": 900,
            "flamethrower": 120,
            "laser": 400,
            "grenade": 800,
            "plasma": 1000,
            "sword": 300,
            "gravity_gun": 600,
            "railgun": 1000,
            "minigun": 60,
            "bfg": 2500,
            "freeze_ray": 500,
            "poison_gun": 150,
            "lightning_gun": 800,
            "acid_gun": 600,
            "teleport_gun": 1000,
            "black_hole_gun": 2000,
            "time_bomb": 1200,
            "chain_lightning": 900,
            "homing_missile": 800,
            "energy_sword": 350,
            "flak_cannon": 400,
            "pulse_rifle": 80,
            "gauss_rifle": 700,
            "cryo_blaster": 500,
            "napalm_launcher": 1000,
            "sonic_blaster": 200,
            "disintegration_ray": 1500
        }

        # Dash & damage boost mechanics
        self.dash_duration = 220  # ms
        self.dash_multiplier = 3.2
        self.last_dash = -99999
        self.dashing = False
        self.dash_timer = 0

        self.damage_mult = 1.0
        self.damage_timer = 0  # ms remaining

        # Shield mechanics
        self.shield_hp = 0
        self.max_shield = 50
        self.shield_color = CYAN

        # Shield skill
        self.shield_skill_duration = 3000  # ms
        self.shield_skill_cooldown = 7000  # ms
        self.last_shield_skill = -99999
        self.shield_skill_active = False
        self.shield_skill_timer = 0

        # Area damage weapon cooldown timer
        self.area_damage_last_used = -99999
        self.area_damage_cooldown = 5000  # ms
        self.area_damage_radius = 100
        self.area_damage_per_tick = 2
        self.area_damage_tick_interval = 500  # ms
        self.area_damage_tick_timer = 0

        # Combo system
        self.combo = 0
        self.last_kill_time = 0
        self.combo_multiplier = 1.0
        self.combo_timer = 3000  # ms

    def apply_upgrades(self, upgrades_data):
        """Applies permanent upgrades to the player's stats."""
        old_max_hp = self.max_hp
        self.max_hp = 100 + (50 if upgrades_data.get("max_hp", 0) else 0)
        # Only heal if max_hp increased, don't set current hp to max if it was lower
        if self.max_hp > old_max_hp:
            self.hp += (self.max_hp - old_max_hp) # Increase current HP by the difference
        if self.hp > self.max_hp: # Cap current HP at new max HP
            self.hp = self.max_hp

        self.speed_bonus = 1.2 if upgrades_data.get("speed", 0) else 1.0
        self.dash_cooldown = 3000 * (0.8 if upgrades_data.get("dash_cooldown", 0) else 1.0)
        self.shield_regen_rate = 0.1 * (1.5 if upgrades_data.get("shield_regen", 0) else 1.0)
        self.damage_mult_base = 1.5 if upgrades_data.get("damage_mult", 0) else 1.0

    def update_combo(self):
        """Updates the player's combo count and multiplier."""
        now = pygame.time.get_ticks()
        if now - self.last_kill_time < self.combo_timer:
            self.combo += 1
            self.combo_multiplier = 1.0 + (self.combo * 0.1)  # Increase multiplier by 0.1 per combo
        else:
            self.combo = 1
            self.combo_multiplier = 1.1
        self.last_kill_time = now

    def can_shoot(self):
        """Checks if the player can currently shoot."""
        now = pygame.time.get_ticks()
        return now - self.last_shot >= self.cooldowns.get(self.weapon, 200)

    def start_dash(self):
        """Initiates a dash maneuver."""
        now = pygame.time.get_ticks()
        if now - self.last_dash >= self.dash_cooldown and not self.dashing:
            self.dashing = True
            self.dash_timer = self.dash_duration
            self.last_dash = now
            if dash_sound: dash_sound.play()
            return True
        return False

    def apply_damage_boost(self, mult=1.6, duration=6000):
        """Applies a temporary damage boost to the player."""
        self.damage_mult = mult
        self.damage_timer = duration
        if powerup_sound: powerup_sound.play()

    def activate_shield_skill(self):
        """Activates the player's shield skill."""
        now = pygame.time.get_ticks()
        if now - self.last_shield_skill >= self.shield_skill_cooldown:
            self.shield_skill_active = True
            self.shield_skill_timer = self.shield_skill_duration
            self.last_shield_skill = now
            self.shield_hp = self.max_shield # Fully restore shield on activation
            self.shield_skill_cooldown = random.randint(6000, 9000) # Randomize next cooldown
            if shield_sound: shield_sound.play()
            return True
        return False

    def update(self, dt, keys, particles=None):
        """Updates the player's state, including movement, timers, and skills."""
        # movement
        mv = Vector2(0, 0)
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            mv.y = -1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            mv.y = 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            mv.x = -1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            mv.x = 1

        if mv.length_squared() > 0:
            mv = mv.normalize()
            speed = PLAYER_SPEED * self.speed_bonus
            if is_raining: # Apply rain speed debuff
                speed *= RAIN_SPEED_DEBUFF
            if self.dashing:
                speed *= self.dash_multiplier
            self.vel = mv * speed
        else:
            self.vel = Vector2(0, 0)

        # During dash, create particles (trail)
        if self.dashing and particles is not None:
            for _ in range(2):
                ang = random.uniform(-math.pi, math.pi)
                sp = random.uniform(0.5, 2.0)
                vel = Vector2(math.cos(ang) * sp, math.sin(ang) * sp)
                particles.append(Particle(self.pos.xy, vel, radius=random.uniform(2, 4), life=0.25, color=(220,220,255)))

        # apply movement
        self.pos += self.vel * dt
        self.pos.x = max(self.size, min(current_width - self.size, self.pos.x))
        self.pos.y = max(self.size, min(current_height - self.size, self.pos.y))

        # update dash timer
        if self.dashing:
            self.dash_timer -= clock.get_time()
            if self.dash_timer <= 0:
                self.dashing = False

        # update damage buff
        if self.damage_timer > 0:
            self.damage_timer -= clock.get_time()
            if self.damage_timer <= 0:
                self.damage_mult = 1.0
                self.damage_timer = 0

        # update shield skill timer
        if self.shield_skill_active:
            self.shield_skill_timer -= clock.get_time()
            if self.shield_skill_timer <= 0:
                self.shield_skill_active = False
                self.shield_hp = 0 # Shield HP depletes when skill ends
                self.shield_skill_timer = 0

        # shield regeneration
        if self.shield_hp < self.max_shield and not self.shield_skill_active: # Only regen if skill is not active
            self.shield_hp += self.shield_regen_rate * dt * 60 # Scale regen with dt
            if self.shield_hp > self.max_shield:
                self.shield_hp = self.max_shield

        # update area damage weapon cooldown timer
        if self.weapon == "area_damage":
            self.area_damage_tick_timer -= clock.get_time()
            if self.area_damage_tick_timer < 0:
                self.area_damage_tick_timer = 0 # Ensure timer doesn't go negative

    def draw(self, surf, mouse_pos=(0,0)):
        """Draws the player on the surface."""
        color = WHITE if not self.dashing else CYAN
        pygame.draw.circle(surf, color, (int(self.pos.x), int(self.pos.y)), self.size)
        if self.shield_hp > 0:
            # Draw shield as an outer circle
            pygame.draw.circle(surf, self.shield_color, (int(self.pos.x), int(self.pos.y)), self.size + 10, 3)
        dirv = Vector2(mouse_pos) - self.pos
        if dirv.length_squared() > 0:
            dirn = dirv.normalize()
            end = self.pos + dirn * (self.size + 12)
            pygame.draw.line(surf, BLACK,
                             (int(self.pos.x), int(self.pos.y)), (int(end.x), int(end.y)), 6)
        self.draw_health_bar(surf)

        # Draw area damage weapon effect radius if active and weapon selected
        if self.weapon == "area_damage":
            now = pygame.time.get_ticks()
            if now - self.area_damage_last_used < self.area_damage_cooldown: # Only draw if recently activated
                color = (255, 0, 0, 50)  # semi-transparent red
                s = pygame.Surface((self.area_damage_radius*2, self.area_damage_radius*2), pygame.SRCALPHA)
                pygame.draw.circle(s, color, (self.area_damage_radius, self.area_damage_radius), self.area_damage_radius, width=3)
                surf.blit(s, (int(self.pos.x - self.area_damage_radius), int(self.pos.y - self.area_damage_radius)))

    def shoot(self, mouse_pos, bullets, particles=None):
        """Fires a bullet based on the current weapon."""
        now = pygame.time.get_ticks()
        if not self.can_shoot():
            return

        if self.ammo.get(self.weapon, 0) <= 0 and self.weapon not in ("pistol", "sword"):
            self.weapon = "pistol" # Switch to pistol if out of ammo

        dirv = Vector2(mouse_pos) - self.pos
        if dirv.length_squared() == 0:
            dirv = Vector2(1, 0)
        dirn = dirv.normalize()
        w = self.weapon

        def mkbullet(pos, d, **kwargs):
            dmg = kwargs.pop("damage", 18)
            dmg = int(dmg * self.damage_mult * self.damage_mult_base)
            b = Bullet(pos, d, damage=dmg, **kwargs)
            bullets.append(b)
            if particles:
                spawn_sparks(particles, pos.x, pos.y, count=2)

        if w == "pistol":
            mkbullet(self.pos + dirn * (self.size + 8), dirn, btype="normal", speed=BULLET_SPEED, radius=5, color=YELLOW, damage=18) # REVISI: Menggunakan BULLET_SPEED global

        elif w == "shotgun":
            if self.ammo["shotgun"] > 0:
                for i in range(-3, 4):
                    angle = math.atan2(dirv.y, dirv.x) + random.uniform(-SHOTGUN_SPREAD, SHOTGUN_SPREAD)
                    d = Vector2(math.cos(angle), math.sin(angle))
                    mkbullet(self.pos + d * (self.size + 8), d, btype="shotgun", speed=BULLET_SPEED * 0.8, radius=4, color=YELLOW, damage=10) # REVISI: Kecepatan relatif terhadap BULLET_SPEED
                self.ammo["shotgun"] -= 1

        elif w == "rocket":
            if self.ammo["rocket"] > 0:
                mkbullet(self.pos + dirn * (self.size + 10), dirn, btype="rocket", speed=BULLET_SPEED * 0.5, radius=10, color=ORANGE, damage=50) # REVISI: Kecepatan relatif terhadap BULLET_SPEED
                self.ammo["rocket"] -= 1

        elif w == "machinegun":
            if self.ammo["machinegun"] > 0:
                mkbullet(self.pos + dirn * (self.size + 8), dirn, btype="mg", speed=BULLET_SPEED * 1.2, radius=3, color=YELLOW, damage=10) # REVISI: Kecepatan relatif terhadap BULLET_SPEED
                self.ammo["machinegun"] -= 1

        elif w == "area_damage":
            now = pygame.time.get_ticks()
            if now - self.area_damage_last_used >= self.area_damage_cooldown:
                self.area_damage_last_used = now
                self.area_damage_tick_timer = self.area_damage_tick_interval
                # Area damage weapon does not shoot bullets, damage applied in game loop
                # Just spawn some particles to indicate activation
                if particles:
                    for _ in range(20):
                        ang = random.uniform(0, math.tau)
                        dist = random.uniform(0, self.area_damage_radius)
                        pos = self.pos + Vector2(math.cos(ang)*dist, math.sin(ang)*dist)
                        vel = Vector2(math.cos(ang)*random.uniform(0.5,1.5), math.sin(ang)*random.uniform(0.5,1.5))
                        particles.append(Particle(pos.xy, vel, radius=4, life=0.5, color=RED))
                self.ammo["area_damage"] -= 1

        elif w == "sniper":
            if self.ammo["sniper"] > 0:
                mkbullet(self.pos + dirn * (self.size + 12), dirn, btype="sniper", speed=BULLET_SPEED * 1.8, radius=6, color=WHITE, damage=90) # REVISI: Kecepatan relatif terhadap BULLET_SPEED
                self.ammo["sniper"] -= 1

        elif w == "flamethrower":
            if self.ammo["flamethrower"] > 0:
                for i in range(3):
                    angle = math.atan2(dirv.y, dirv.x) + random.uniform(-0.25, 0.25)
                    d = Vector2(math.cos(angle), math.sin(angle))
                    mkbullet(self.pos + d * (self.size + 6), d, btype="flame", speed=BULLET_SPEED * 0.6, radius=4, color=ORANGE, damage=8, lifetime=600) # REVISI: Kecepatan relatif terhadap BULLET_SPEED
                self.ammo["flamethrower"] -= 1

        elif w == "laser":
            if self.ammo["laser"] > 0:
                mkbullet(self.pos + dirn * (self.size + 8), dirn, btype="laser", speed=BULLET_SPEED * 2.0, radius=3, color=BLUE, damage=25, lifetime=1200) # REVISI: Kecepatan relatif terhadap BULLET_SPEED
                self.ammo["laser"] -= 1

        elif w == "grenade":
            if self.ammo["grenade"] > 0:
                b = Bullet(self.pos + dirn * (self.size + 10), dirn, btype="grenade", speed=BULLET_SPEED * 0.7, radius=7, color=GREEN, damage=0, lifetime=2000) # REVISI: Kecepatan relatif terhadap BULLET_SPEED
                b.timer = 700
                bullets.append(b)
                if particles:
                    spawn_sparks(particles, b.pos.x, b.pos.y, count=2)
                self.ammo["grenade"] -= 1

        elif w == "plasma":
            if self.ammo["plasma"] > 0:
                mkbullet(self.pos + dirn * (self.size + 12), dirn, btype="plasma", speed=BULLET_SPEED * 0.75, radius=12, color=PURPLE, damage=60) # REVISI: Kecepatan relatif terhadap BULLET_SPEED
                self.ammo["plasma"] -= 1

        elif w == "sword":
            mkbullet(self.pos + dirn * (self.size + 18), dirn, btype="sword", speed=0, radius=28, color=RED, damage=40, lifetime=200)

        elif w == "gravity_gun":
            if self.ammo["gravity_gun"] > 0:
                mkbullet(self.pos + dirn * (self.size + 10), dirn, btype="gravity", speed=BULLET_SPEED * 0.6, radius=10, color=LIGHT_BLUE, damage=0, lifetime=1500) # REVISI: Kecepatan relatif terhadap BULLET_SPEED
                self.ammo["gravity_gun"] -= 1

        elif w == "railgun":
            if self.ammo["railgun"] > 0:
                mkbullet(self.pos + dirn * (self.size + 12), dirn, btype="railgun", speed=BULLET_SPEED * 2.5, radius=8, color=WHITE, damage=120)
                self.ammo["railgun"] -= 1

        elif w == "minigun":
            if self.ammo["minigun"] > 0:
                for i in range(3):
                    angle = math.atan2(dirv.y, dirv.x) + random.uniform(-0.1, 0.1)
                    d = Vector2(math.cos(angle), math.sin(angle))
                    mkbullet(self.pos + d * (self.size + 8), d, btype="minigun", speed=BULLET_SPEED * 1.5, radius=3, color=YELLOW, damage=8)
                self.ammo["minigun"] -= 1

        elif w == "bfg":
            if self.ammo["bfg"] > 0:
                mkbullet(self.pos + dirn * (self.size + 15), dirn, btype="bfg", speed=BULLET_SPEED * 0.8, radius=20, color=PURPLE, damage=200)
                self.ammo["bfg"] -= 1

        elif w == "freeze_ray":
            if self.ammo["freeze_ray"] > 0:
                mkbullet(self.pos + dirn * (self.size + 8), dirn, btype="freeze", speed=BULLET_SPEED * 1.2, radius=4, color=CYAN, damage=20)
                self.ammo["freeze_ray"] -= 1

        elif w == "poison_gun":
            if self.ammo["poison_gun"] > 0:
                mkbullet(self.pos + dirn * (self.size + 8), dirn, btype="poison", speed=BULLET_SPEED, radius=5, color=GREEN, damage=15)
                self.ammo["poison_gun"] -= 1

        elif w == "lightning_gun":
            if self.ammo["lightning_gun"] > 0:
                mkbullet(self.pos + dirn * (self.size + 8), dirn, btype="lightning", speed=BULLET_SPEED * 3, radius=3, color=BLUE, damage=25)
                self.ammo["lightning_gun"] -= 1

        elif w == "acid_gun":
            if self.ammo["acid_gun"] > 0:
                mkbullet(self.pos + dirn * (self.size + 8), dirn, btype="acid", speed=BULLET_SPEED, radius=5, color=YELLOW, damage=30)
                self.ammo["acid_gun"] -= 1

        elif w == "teleport_gun":
            if self.ammo["teleport_gun"] > 0:
                teleport_dist = 200
                new_pos = self.pos + dirn * teleport_dist
                new_pos.x = max(self.size, min(current_width - self.size, new_pos.x))
                new_pos.y = max(self.size, min(current_height - self.size, new_pos.y))
                self.pos = new_pos
                self.ammo["teleport_gun"] -= 1

        elif w == "black_hole_gun":
            if self.ammo["black_hole_gun"] > 0:
                mkbullet(self.pos + dirn * (self.size + 10), dirn, btype="black_hole", speed=0, radius=15, color=BLACK, damage=0, lifetime=3000)
                self.ammo["black_hole_gun"] -= 1

        elif w == "time_bomb":
            if self.ammo["time_bomb"] > 0:
                b = Bullet(self.pos + dirn * (self.size + 10), dirn, btype="time_bomb", speed=BULLET_SPEED * 0.5, radius=8, color=RED, damage=0, lifetime=5000)
                b.timer = 2000
                bullets.append(b)
                if particles:
                    spawn_sparks(particles, b.pos.x, b.pos.y, count=2)
                self.ammo["time_bomb"] -= 1

        elif w == "chain_lightning":
            if self.ammo["chain_lightning"] > 0:
                mkbullet(self.pos + dirn * (self.size + 8), dirn, btype="chain", speed=BULLET_SPEED * 2, radius=3, color=CYAN, damage=20)
                self.ammo["chain_lightning"] -= 1

        elif w == "homing_missile":
            if self.ammo["homing_missile"] > 0:
                mkbullet(self.pos + dirn * (self.size + 10), dirn, btype="homing", speed=BULLET_SPEED * 0.8, radius=8, color=ORANGE, damage=50)
                self.ammo["homing_missile"] -= 1

        elif w == "energy_sword":
            mkbullet(self.pos + dirn * (self.size + 20), dirn, btype="energy_sword", speed=0, radius=30, color=BLUE, damage=50, lifetime=300)

        elif w == "flak_cannon":
            if self.ammo["flak_cannon"] > 0:
                for i in range(5):
                    angle = math.atan2(dirv.y, dirv.x) + random.uniform(-0.3, 0.3)
                    d = Vector2(math.cos(angle), math.sin(angle))
                    mkbullet(self.pos + d * (self.size + 8), d, btype="flak", speed=BULLET_SPEED * 0.9, radius=6, color=ORANGE, damage=15)
                self.ammo["flak_cannon"] -= 1

        elif w == "pulse_rifle":
            if self.ammo["pulse_rifle"] > 0:
                mkbullet(self.pos + dirn * (self.size + 8), dirn, btype="pulse", speed=BULLET_SPEED * 1.8, radius=4, color=PURPLE, damage=18)
                self.ammo["pulse_rifle"] -= 1

        elif w == "gauss_rifle":
            if self.ammo["gauss_rifle"] > 0:
                mkbullet(self.pos + dirn * (self.size + 12), dirn, btype="gauss", speed=BULLET_SPEED * 3, radius=5, color=WHITE, damage=80)
                self.ammo["gauss_rifle"] -= 1

        elif w == "cryo_blaster":
            if self.ammo["cryo_blaster"] > 0:
                mkbullet(self.pos + dirn * (self.size + 8), dirn, btype="cryo", speed=BULLET_SPEED, radius=5, color=CYAN, damage=25)
                self.ammo["cryo_blaster"] -= 1

        elif w == "napalm_launcher":
            if self.ammo["napalm_launcher"] > 0:
                for i in range(8):
                    angle = math.atan2(dirv.y, dirv.x) + random.uniform(-0.5, 0.5)
                    d = Vector2(math.cos(angle), math.sin(angle))
                    mkbullet(self.pos + d * (self.size + 6), d, btype="napalm", speed=BULLET_SPEED * 0.7, radius=4, color=ORANGE, damage=10, lifetime=800)
                self.ammo["napalm_launcher"] -= 1

        elif w == "sonic_blaster":
            if self.ammo["sonic_blaster"] > 0:
                mkbullet(self.pos + dirn * (self.size + 8), dirn, btype="sonic", speed=BULLET_SPEED * 1.5, radius=5, color=LIGHT_BLUE, damage=15)
                self.ammo["sonic_blaster"] -= 1

        elif w == "disintegration_ray":
            if self.ammo["disintegration_ray"] > 0:
                mkbullet(self.pos + dirn * (self.size + 8), dirn, btype="disintegration", speed=BULLET_SPEED * 2, radius=4, color=MAGENTA, damage=150)
                self.ammo["disintegration_ray"] -= 1

        if shoot_sound: shoot_sound.play()
        self.last_shot = now


class Enemy(Entity):
    """Base class for enemy characters."""
    def __init__(self, x, y, hp=30):
        col = random.choice([(220, 60, 60), (180, 30, 30), (200, 80, 50)])
        super().__init__(x, y, 18, color=col, hp=hp)
        self.vel = Vector2(0, 0)

    def update(self, dt, target_pos):
        """Updates the enemy's state, moving towards the target."""
        dirv = Vector2(target_pos) - self.pos
        if dirv.length_squared() > 0:
            speed = ENEMY_SPEED
            if is_raining: # Apply rain speed debuff
                speed *= RAIN_SPEED_DEBUFF
            self.vel = dirv.normalize() * speed
        else:
            self.vel = Vector2(0, 0)
        self.pos += self.vel * dt


class FastEnemy(Enemy):
    """A faster, less durable enemy."""
    def __init__(self, x, y):
        super().__init__(x, y, hp=20)
        self.color = (255, 100, 100)  # Light red
        self.speed = ENEMY_SPEED * 1.8

    def update(self, dt, target_pos):
        dirv = Vector2(target_pos) - self.pos
        if dirv.length_squared() > 0:
            speed = self.speed
            if is_raining: # Apply rain speed debuff
                speed *= RAIN_SPEED_DEBUFF
            self.vel = dirv.normalize() * speed
        else:
            self.vel = Vector2(0, 0)
        self.pos += self.vel * dt


class ArmoredEnemy(Enemy):
    """A slower, more durable enemy."""
    def __init__(self, x, y):
        super().__init__(x, y, hp=60)
        self.color = (100, 100, 100)  # Gray
        self.speed = ENEMY_SPEED * 0.7
        self.size = 22

    def update(self, dt, target_pos):
        dirv = Vector2(target_pos) - self.pos
        if dirv.length_squared() > 0:
            speed = self.speed
            if is_raining: # Apply rain speed debuff
                speed *= RAIN_SPEED_DEBUFF
            self.vel = dirv.normalize() * speed
        else:
            self.vel = Vector2(0, 0)
        self.pos += self.vel * dt


class FlyingEnemy(Enemy):
    """An enemy that moves with a wavy pattern."""
    def __init__(self, x, y):
        super().__init__(x, y, hp=25)
        self.color = (150, 150, 255)  # Light blue
        self.speed = ENEMY_SPEED * 1.2
        self.amplitude = 50
        self.frequency = 0.02
        self.time = 0

    def update(self, dt, target_pos):
        self.time += dt
        dirv = Vector2(target_pos) - self.pos
        if dirv.length_squared() > 0:
            speed = self.speed
            if is_raining: # Apply rain speed debuff
                speed *= RAIN_SPEED_DEBUFF
            self.vel = dirv.normalize() * speed
        else:
            self.vel = Vector2(0, 0)
        # Add wavy movement
        self.vel.y += math.sin(self.time * self.frequency) * self.amplitude * dt
        self.pos += self.vel * dt


class TeleportingEnemy(Enemy):
    """An enemy that periodically teleports near the player."""
    def __init__(self, x, y):
        super().__init__(x, y, hp=30)
        self.color = MAGENTA
        self.speed = ENEMY_SPEED * 1.5
        self.teleport_cd = 2000  # ms
        self.last_teleport = 0

    def update(self, dt, target_pos):
        now = pygame.time.get_ticks()
        if now - self.last_teleport > self.teleport_cd:
            # Teleport to a random position near the player
            angle = random.uniform(0, math.tau)
            dist = random.uniform(100, 300)
            self.pos = Vector2(target_pos) + Vector2(math.cos(angle) * dist, math.sin(angle) * dist)
            self.last_teleport = now
        else:
            # Move towards player
            dirv = Vector2(target_pos) - self.pos
            if dirv.length_squared() > 0:
                speed = self.speed
                if is_raining: # Apply rain speed debuff
                    speed *= RAIN_SPEED_DEBUFF
                self.vel = dirv.normalize() * speed
            else:
                self.vel = Vector2(0, 0)
            self.pos += self.vel * dt


class Boss(Enemy):
    """A powerful boss enemy with multiple phases."""
    def __init__(self, x, y):
        super().__init__(x, y, hp=500)
        self.size = 40
        self.color = PURPLE
        self.shoot_cd = 1200
        self.last_shot = 0
        self.phase = 1 # New: Boss phases
        self.phase_timer = 0 # New: Timer for phase specific actions

    def update(self, dt, target_pos, bullets, player_instance, particles_list, enemies_list):
        """Updates the boss's state, including phase-specific actions."""
        self.phase_timer += clock.get_time() # Use clock.get_time() for ms

        # Phase transition
        if self.hp < self.max_hp / 2 and self.phase == 1: # Transition to Phase 2 at 50% HP
            self.phase = 2
            self.phase_timer = 0 # Reset timer for new phase actions
            print("Boss entered Phase 2!")

        if self.phase == 1:
            super().update(dt, target_pos) # Normal movement
            now = pygame.time.get_ticks()
            if now - self.last_shot > self.shoot_cd:
                dirv = Vector2(target_pos) - self.pos
                if dirv.length_squared() > 0:
                    for a in (-0.12, 0.0, 0.12): # Triple shot
                        ang = math.atan2(dirv.y, dirv.x) + a
                        d = Vector2(math.cos(ang), math.sin(ang))
                        bullets.append(Bullet(self.pos + d * (self.size + 6), d, owner="boss", btype="boss",
                                              speed=BULLET_SPEED * 0.7, radius=8, color=PURPLE, damage=18)) # REVISI: Kecepatan relatif terhadap BULLET_SPEED
                self.last_shot = now
        elif self.phase == 2:
            # Phase 2: Teleport and Area Explosion
            if self.phase_timer >= 2000: # Teleport every 2 seconds
                # Teleport to a random position
                self.pos = Vector2(random.randint(50, current_width - 50), random.randint(50, current_height - 50))

                # Spawn explosion at new position
                spawn_explosion(particles_list, self.pos.x, self.pos.y, count=PARTICLE_COUNT * 5)

                # Damage enemies and player in explosion radius
                for e in list(enemies_list): # Damage other enemies too
                    if e != self and (self.pos - e.pos).length() < EXPLOSION_RADIUS:
                        e.hp -= EXPLOSION_DAMAGE * 1.5 # More damage for boss explosion
                        spawn_blood(particles_list, e.pos.x, e.pos.y, intensity=8)
                        if e.hp <= 0:
                            # No score/drops for boss damaging other enemies
                            try: enemies_list.remove(e)
                            except ValueError: pass

                if (self.pos - player_instance.pos).length() < EXPLOSION_RADIUS:
                    damage = EXPLOSION_DAMAGE * 2 # Player takes more damage
                    if player_instance.shield_hp > 0:
                        if player_instance.shield_hp >= damage:
                            player_instance.shield_hp -= damage
                            damage = 0
                        else:
                            damage -= player_instance.shield_hp
                            player_instance.shield_hp = 0
                    player_instance.hp -= damage
                    spawn_blood(particles_list, player_instance.pos.x, player_instance.pos.y, intensity=12)
                    if player_instance.hp <= 0:
                        # Game over logic will be handled in game_loop
                        pass

                self.phase_timer = 0 # Reset phase timer

# ---------------- Powerups ----------------
class HealthOrb:
    """A power-up that restores player health."""
    def __init__(self, x, y):
        self.pos = Vector2(x, y)
        self.size = 10
        self.color = GREEN
        self.heal_amount = 25

    def draw(self, surf):
        pygame.draw.circle(surf, self.color, (int(self.pos.x), int(self.pos.y)), self.size)


class AmmoBox:
    """A power-up that replenishes player ammo."""
    def __init__(self, x, y):
        self.pos = Vector2(x, y)
        self.size = 12
        self.color = BLUE
        self.fill = {"shotgun": 6, "rocket": 2, "machinegun": 40, "area_damage": 1, "sniper": 4,
                     "flamethrower": 20, "laser": 10, "grenade": 3, "plasma": 2, "gravity_gun": 5, "railgun" : 15 , "minigun" : 20 , "bfg" : 7 , "freeze_ray" : 10, "poison_gun" : 10, "lightning_gun" : 10 , "acid_gun" : 5}

    def draw(self, surf):
        pygame.draw.rect(surf, self.color,
                         (int(self.pos.x - self.size), int(self.pos.y - self.size),
                          self.size * 2, self.size * 2), border_radius=4)


class Powerup:
    """A temporary power-up for dash or damage boost."""
    def __init__(self, x, y, ptype):
        self.pos = Vector2(x, y)
        self.size = 12
        self.ptype = ptype  # 'dash' or 'damage'
        self.color = CYAN if ptype == "dash" else ORANGE

    def draw(self, surf):
        pygame.draw.circle(surf, self.color, (int(self.pos.x), int(self.pos.y)), self.size)
        draw_text(surf, self.ptype[0].upper(), 14, int(self.pos.x - 6), int(self.pos.y - 10), color=BLACK)


class Mine:
    """An environmental hazard that explodes on contact."""
    def __init__(self, x, y):
        self.pos = Vector2(x, y)
        self.size = 15
        self.color = DARK_RED
        self.damage = 20

    def draw(self, surf):
        pygame.draw.circle(surf, self.color, (int(self.pos.x), int(self.pos.y)), self.size)


# ---------------- Helpers: particles, explosion ------------
def spawn_blood(particles, x, y, intensity=PARTICLE_COUNT):
    """Spawns blood particles at a given position."""
    for _ in range(intensity):
        ang = random.uniform(0, math.tau)
        speed = random.uniform(2, 8)
        vel = Vector2(math.cos(ang) * speed, math.sin(ang) * speed)
        radius = random.uniform(2, 5)
        life = random.uniform(0.4, 1.0)
        color = RED if random.random() > 0.3 else DARK_RED
        particles.append(Particle((x, y), vel, radius, life, color))


def spawn_explosion(particles, x, y, count=PARTICLE_COUNT * 3):
    """Spawns explosion particles and plays explosion sound."""
    if explosion_sound:
        explosion_sound.play()
    for _ in range(count):
        ang = random.uniform(0, math.tau)
        speed = random.uniform(3, 12)
        vel = Vector2(math.cos(ang) * speed, math.sin(ang) * speed)
        radius = random.uniform(3, 8)
        life = random.uniform(0.6, 1.4)
        color = ORANGE if random.random() > 0.4 else YELLOW
        particles.append(Particle((x, y), vel, radius, life, color))


def spawn_sparks(particles, x, y, count=8):
    """Spawns spark particles at a given position."""
    for _ in range(count):
        ang = random.uniform(0, math.tau)
        speed = random.uniform(1, 5)
        vel = Vector2(math.cos(ang) * speed, math.sin(ang) * speed)
        radius = random.uniform(1, 3)
        life = random.uniform(0.2, 0.6)
        color = WHITE
        particles.append(Particle((x, y), vel, radius, life, color))

# ---------------- Spawn enemy helper ----------------
def spawn_enemy(enemies, level):
    """Spawns a random enemy type at a random edge of the screen."""
    edge = random.choice(["top", "bottom", "left", "right"])
    if edge == "top":
        x = random.randint(20, current_width - 20)
        y = -30
    elif edge == "bottom":
        x = random.randint(20, current_width - 20)
        y = current_height + 30
    elif edge == "left":
        x = -30
        y = random.randint(20, current_height - 20)
    else: # right
        x = current_width + 30
        y = random.randint(20, current_height - 20)

    # Randomly choose enemy type
    enemy_types = [Enemy, FastEnemy, ArmoredEnemy, FlyingEnemy, TeleportingEnemy]
    weights = [0.4, 0.2, 0.15, 0.15, 0.1]  # Normal more common, teleporting less
    enemy_class = random.choices(enemy_types, weights=weights, k=1)[0]

    if enemy_class == Enemy:
        hp = random.randint(18 + level * 2, 30 + level * 3)
        enemies.append(Enemy(x, y, hp=hp))
    elif enemy_class == FastEnemy:
        enemies.append(FastEnemy(x, y))
    elif enemy_class == ArmoredEnemy:
        enemies.append(ArmoredEnemy(x, y))
    elif enemy_class == FlyingEnemy:
        enemies.append(FlyingEnemy(x, y))
    elif enemy_class == TeleportingEnemy:
        enemies.append(TeleportingEnemy(x, y))

# ---------------- Weather System ----------------
def start_rain():
    """Initiates the rain weather effect."""
    global is_raining, rain_duration, rain_start_time, rain_drops
    is_raining = True
    rain_duration = random.randint(10000, 25000) # Rain for 10-25 seconds
    rain_start_time = pygame.time.get_ticks()
    rain_drops = []
    for _ in range(200): # More rain drops
        x = random.randint(0, current_width)
        y = random.randint(0, current_height)
        speed = random.uniform(4, 8)
        rain_drops.append([x, y, speed])

def stop_rain():
    """Stops the rain weather effect."""
    global is_raining, rain_drops
    is_raining = False
    rain_drops = []

def update_rain():
    """Updates the position of rain drops."""
    global rain_drops
    if is_raining:
        for drop in rain_drops:
            drop[1] += drop[2] * (clock.get_time() / 16.6667) # Adjust speed with dt
            if drop[1] > current_height:
                drop[0] = random.randint(0, current_width)
                drop[1] = random.randint(-20, 0)

def draw_rain(surf):
    """Draws rain drops on the surface."""
    if is_raining:
        for drop in rain_drops:
            pygame.draw.line(surf, LIGHT_BLUE, (int(drop[0]), int(drop[1])), (int(drop[0]), int(drop[1] + 10)), 1)

# ---------------- Daily Mission System ----------------
def reset_daily_mission():
    """Resets the daily mission to a new random mission."""
    global daily_mission
    mission_types = [
        {"desc": "Bunuh {target} musuh", "target": random.randint(30, 70), "reward": random.randint(50, 150)},
        {"desc": "Capai score {target}", "target": random.randint(500, 1500), "reward": random.randint(70, 200)},
        {"desc": "Bunuh {target} musuh dengan {weapon}", "target": random.randint(10, 30), "reward": random.randint(80, 250), "weapon": random.choice(["shotgun", "machinegun", "sniper"])}
    ]
    daily_mission = random.choice(mission_types)
    daily_mission["progress"] = 0
    daily_mission["completed"] = False

def update_daily_mission(player_instance, enemy_killed_weapon=None):
    """Updates the progress of the daily mission."""
    global coins, daily_mission
    if daily_mission["completed"]:
        return

    if "Bunuh" in daily_mission["desc"]:
        if "dengan" in daily_mission["desc"]: # Specific weapon kill mission
            if enemy_killed_weapon == daily_mission.get("weapon"):
                daily_mission["progress"] += 1
        else: # General kill mission
            daily_mission["progress"] += 1
    elif "Capai score" in daily_mission["desc"]:
        daily_mission["progress"] = player_instance.score # Update progress with current score

    if daily_mission["progress"] >= daily_mission["target"]:
        coins += daily_mission["reward"]
        daily_mission["completed"] = True
        print(f"Misi Harian Selesai! Kamu mendapatkan {daily_mission['reward']} koin.")
        # Save coins immediately
        save_coins(coins)


# ---------------- Quiz Data ----------------
quiz_questions = [
    {
        "question": "Apa rumus dasar untuk menghitung luas segitiga?",
        "options": ["A. (alas x tinggi) / 2", "B. alas x tinggi", "C. sisi x sisi", "D. π x r²"],
        "answer": "A"
    },
    {
        "question": "Siapa penemu teori relativitas?",
        "options": ["A. Isaac Newton", "B. Albert Einstein", "C. Nikola Tesla", "D. Thomas Edison"],
        "answer": "B"
    },
    {
        "question": "Apa nama proses fotosintesis?",
        "options": ["A. Pembentukan glukosa dari CO2 dan H2O", "B. Pembentukan oksigen dari CO2", "C. Pembentukan karbohidrat dari air", "D. Pembentukan energi dari matahari"],
        "answer": "A"
    },
    {
        "question": "Berapa jumlah proton dalam atom karbon-12?",
        "options": ["A. 6", "B. 12", "C. 18", "D. 24"],
        "answer": "A"
    },
    {
        "question": "Apa nama ibu kota Indonesia?",
        "options": ["A. Jakarta", "B. Surabaya", "C. Bandung", "D. Medan"],
        "answer": "A"
    },
    {
        "question": "Apa rumus kimia untuk air?",
        "options": ["A. H2O", "B. CO2", "C. O2", "D. H2O2"],
        "answer": "A"
    },
    {
        "question": "Siapa presiden pertama Indonesia?",
        "options": ["A. Soekarno", "B. Soeharto", "C. BJ Habibie", "D. Abdurrahman Wahid"],
        "answer": "A"
    },
    {
        "question": "Apa nama planet terdekat dengan Matahari?",
        "options": ["A. Venus", "B. Bumi", "C. Merkurius", "D. Mars"],
        "answer": "C"
    },
    {
        "question": "Berapa nilai dari π (pi) hingga 2 desimal?",
        "options": ["A. 3.14", "B. 3.16", "C. 3.12", "D. 3.18"],
        "answer": "A"
    },
    {
        "question": "Apa nama reaksi nuklir yang terjadi di dalam Matahari?",
        "options": ["A. Fusi", "B. Fisi", "C. Pembelahan", "D. Penggabungan"],
        "answer": "A"
    },
    {
        "question": "Apa hasil dari 2 + 2 x 3?",
        "options": ["A. 8", "B. 12", "C. 6", "D. 10"],
        "answer": "A"
    },
    {
        "question": "Siapa penulis novel 'Pride and Prejudice'?",
        "options": ["A. Jane Austen", "B. Charlotte Bronte", "C. Emily Bronte", "D. Louisa May Alcott"],
        "answer": "A"
    },
    {
        "question": "Apa nama sungai terpanjang di dunia?",
        "options": ["A. Amazon", "B. Nil", "C. Yangtze", "D. Mississippi"],
        "answer": "B"
    },
    {
        "question": "Berapa jumlah tulang dalam tubuh manusia dewasa?",
        "options": ["A. 206", "B. 208", "C. 210", "D. 212"],
        "answer": "A"
    },
    {
        "question": "Apa nama unsur kimia dengan simbol 'Fe'?",
        "options": ["A. Flourin", "B. Ferrum", "C. Fosfor", "D. Besi"],
        "answer": "D"
    },
    {
        "question": "Siapa pelukis terkenal dari lukisan 'Mona Lisa'?",
        "options": ["A. Vincent van Gogh", "B. Pablo Picasso", "C. Leonardo da Vinci", "D. Michelangelo"],
        "answer": "C"
    },
    {
        "question": "Apa nama benua terkecil di dunia?",
        "options": ["A. Afrika", "B. Australia", "C. Eropa", "D. Antartika"],
        "answer": "B"
    },
    {
        "question": "Berapa jumlah sisi pada sebuah kubus?",
        "options": ["A. 4", "B. 6", "C. 8", "D. 12"],
        "answer": "B"
    },
    {
        "question": "Apa nama proses perubahan wujud padat menjadi gas?",
        "options": ["A. Kondensasi", "B. Sublimasi", "C. Evaporasi", "D. Fusi"],
        "answer": "B"
    },
    {
        "question": "Siapa penemu bola lampu?",
        "options": ["A. Thomas Edison", "B. Nikola Tesla", "C. Alexander Graham Bell", "D. Benjamin Franklin"],
        "answer": "A"
    },
    {
        "question": "Apa nama ibu kota Jepang?",
        "options": ["A. Tokyo", "B. Kyoto", "C. Osaka", "D. Hiroshima"],
        "answer": "A"
    },
    {
        "question": "Berapa jumlah planet di tata surya kita?",
        "options": ["A. 7", "B. 8", "C. 9", "D. 10"],
        "answer": "B"
    },
    {
        "question": "Apa rumus kimia untuk garam dapur?",
        "options": ["A. NaCl", "B. HCl", "C. NaOH", "D. KCl"],
        "answer": "A"
    },
    {
        "question": "Siapa penulis 'Harry Potter' series?",
        "options": ["A. J.K. Rowling", "B. Stephen King", "C. Roald Dahl", "D. C.S. Lewis"],
        "answer": "A"
    },
    {
        "question": "Apa nama gunung tertinggi di dunia?",
        "options": ["A. K2", "B. Kangchenjunga", "C. Everest", "D. Lhotse"],
        "answer": "C"
    },
    {
        "question": "Berapa jumlah kromosom dalam sel manusia?",
        "options": ["A. 22", "B. 23", "C. 46", "D. 48"],
        "answer": "C"
    },
    {
        "question": "Apa nama proses pembelahan sel?",
        "options": ["A. Meiosis", "B. Mitosis", "C. Fotosintesis", "D. Respirasi"],
        "answer": "B"
    },
    {
        "question": "Siapa presiden Amerika Serikat pertama?",
        "options": ["A. Abraham Lincoln", "B. George Washington", "C. Thomas Jefferson", "D. John Adams"],
        "answer": "B"
    },
    {
        "question": "Apa nama samudra terbesar di dunia?",
        "options": ["A. Atlantik", "B. Pasifik", "C. Hindia", "D. Arktik"],
        "answer": "B"
    },
    {
        "question": "Berapa sudut dalam segitiga sama sisi?",
        "options": ["A. 90 derajat", "B. 60 derajat", "C. 45 derajat", "D. 30 derajat"],
        "answer": "B"
    },
    {
        "question": "Apa nama zat yang dihasilkan oleh tumbuhan hijau?",
        "options": ["A. Karbon dioksida", "B. Oksigen", "C. Nitrogen", "D. Hidrogen"],
        "answer": "B"
    },
    {
        "question": "Siapa penemu telepon?",
        "options": ["A. Alexander Graham Bell", "B. Guglielmo Marconi", "C. Samuel Morse", "D. Heinrich Hertz"],
        "answer": "A"
    },
    {
        "question": "Apa nama ibu kota Prancis?",
        "options": ["A. Paris", "B. London", "C. Berlin", "D. Rome"],
        "answer": "A"
    },
    {
        "question": "Berapa jumlah unsur dalam tabel periodik?",
        "options": ["A. 100", "B. 118", "C. 120", "D. 150"],
        "answer": "B"
    },
    {
        "question": "Apa rumus kimia untuk glukosa?",
        "options": ["A. C6H12O6", "B. C12H22O11", "C. CH4", "D. CO2"],
        "answer": "A"
    },
    {
        "question": "Siapa penulis 'The Great Gatsby'?",
        "options": ["A. F. Scott Fitzgerald", "B. Ernest Hemingway", "C. William Faulkner", "D. John Steinbeck"],
        "answer": "A"
    },
    {
        "question": "Apa nama benua terbesar di dunia?",
        "options": ["A. Asia", "B. Afrika", "C. Amerika Utara", "D. Amerika Selatan"],
        "answer": "A"
    },
    {
        "question": "Berapa jumlah gigi susu pada anak-anak?",
        "options": ["A. 20", "B. 28", "C. 32", "D. 16"],
        "answer": "A"
    },
    {
        "question": "Apa nama proses penguapan air?",
        "options": ["A. Kondensasi", "B. Evaporasi", "C. Presipitasi", "D. Transpirasi"],
        "answer": "B"
    },
    {
        "question": "Siapa penemu komputer modern?",
        "options": ["A. Charles Babbage", "B. Alan Turing", "C. Ada Lovelace", "D. John von Neumann"],
        "answer": "B"
    },
    {
        "question": "Apa nama ibu kota Australia?",
        "options": ["A. Sydney", "B. Melbourne", "C. Canberra", "D. Brisbane"],
        "answer": "C"
    },
    {
        "question": "Berapa jumlah bulan dalam setahun?",
        "options": ["A. 10", "B. 11", "C. 12", "D. 13"],
        "answer": "C"
    },
    {
        "question": "Apa rumus kimia untuk asam sulfat?",
        "options": ["A. HCl", "B. H2SO4", "C. HNO3", "D. H3PO4"],
        "answer": "B"
    },
    {
        "question": "Siapa penulis '1984'?",
        "options": ["A. George Orwell", "B. Aldous Huxley", "C. Ray Bradbury", "D. Philip K. Dick"],
        "answer": "A"
    },
    {
        "question": "Apa nama gunung berapi terbesar di dunia?",
        "options": ["A. Vesuvius", "B. Krakatau", "C. Mauna Loa", "D. Fuji"],
        "answer": "C"
    },
    {
        "question": "Berapa jumlah jari pada satu tangan manusia?",
        "options": ["A. 4", "B. 5", "C. 6", "D. 10"],
        "answer": "B"
    }
]

# ---------------- User login screen ----------------
def login_screen():
    """Handles user login and registration."""
    global current_user, current_admin, coins, unlocked, upgrades
    username = ""
    password = ""
    step = "username"  # "username" or "password"
    mode = "login"  # or "register"
    message = ""
    while True:
        screen.fill(BG)
        draw_text(screen, "Login / Register", 48, current_width // 2, 100, color=WHITE, center=True)
        if step == "username":
            draw_text(screen, f"Username: {username}", 24, current_width // 2, 200, color=WHITE, center=True)
        else:
            draw_text(screen, f"Username: {username}", 24, current_width // 2, 200, color=WHITE, center=True)
            draw_text(screen, f"Password: {'*' * len(password)}", 24, current_width // 2, 250, color=WHITE, center=True)
        draw_text(screen, message, 20, current_width // 2, 300, color=RED, center=True)

        mx, my = pygame.mouse.get_pos()
        click = False
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit() # Exit the game completely
            if ev.type == pygame.VIDEORESIZE:
                handle_window_resize(ev)
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if step == "password":
                        step = "username"
                        password = ""
                        message = ""
                    else:
                        return None # Go back to main menu
                elif ev.key == pygame.K_RETURN:
                    if step == "username":
                        if username.strip():
                            step = "password"
                        else:
                            message = "Enter username"
                    else: # step == "password"
                        if mode == "login":
                            # Check if it's an admin first
                            if username in admins and admins[username]["password"] == password:
                                current_admin = username
                                current_user = None  # Clear current user when admin logs in
                                return "admin" # Return admin state
                            elif username in users and users[username] == password:
                                current_user = username
                                current_admin = None  # Clear current admin when user logs in
                                # Load user data on login
                                user_data = load_user_data(current_user)
                                coins = user_data.get("coins", 0)
                                unlocked = set(user_data.get("unlocked", ["pistol"]))
                                upgrades = user_data.get("upgrades", {})
                                return "user" # Return user state
                            else:
                                message = "Invalid username or password"
                        elif mode == "register":
                            if username and password:
                                if username in users or username in admins:
                                    message = "Username already exists"
                                else:
                                    users[username] = password # Add to in-memory users
                                    add_user_to_db(username, password) # Add to database
                                    current_user = username
                                    current_admin = None  # Clear current admin when user logs in
                                    # Initialize user data on registration
                                    user_data = {
                                        "coins": 0,
                                        "unlocked": set(["pistol"]),
                                        "upgrades": {},
                                        "score": 0,
                                        "kills": 0,
                                        "weapon": "pistol",
                                        "ammo": default_ammo.copy()
                                    }
                                    save_user_data(current_user, user_data) # Save initial user data to DB
                                    coins = 0
                                    unlocked = set(["pistol"])
                                    upgrades = {}
                                    return "user" # Return user state
                            else:
                                message = "Enter username and password"
                elif ev.key == pygame.K_BACKSPACE:
                    if step == "username":
                        username = username[:-1]
                    elif step == "password":
                        password = password[:-1]
                else:
                    if ev.unicode.isprintable():
                        if step == "username":
                            username += ev.unicode
                        elif step == "password":
                            password += ev.unicode
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                click = True

        # Buttons
        login_btn = pygame.Rect(current_width // 2 - 100, 350, 200, 50)
        register_btn = pygame.Rect(current_width // 2 - 100, 420, 200, 50)
        back_to_menu_btn = pygame.Rect(10, 10, 100, 40)

        # Dynamic buttons based on step and mode
        continue_btn = pygame.Rect(current_width // 2 - 100, 490, 200, 50) if step == "username" else None
        submit_btn = pygame.Rect(current_width // 2 - 100, 490, 200, 50) if step == "password" and mode in ("login", "register") else None

        button_list = []
        if step == "username":
            button_list.append((login_btn, "Login"))
            button_list.append((register_btn, "Register"))
            if username.strip():
                button_list.append((continue_btn, "Continue"))
        else: # step == "password"
            button_list.append((submit_btn, "Submit"))

        button_list.append((back_to_menu_btn, "Back to Menu"))


        action = draw_buttons(button_list, mx, my, click)

        if action == "Login":
            mode = "login"
            step = "username"
            username = ""
            password = ""
            message = ""
        elif action == "Register":
            mode = "register"
            step = "username"
            username = ""
            password = ""
            message = ""
        elif action == "Back to Menu":
            return None
        elif action == "Continue" and step == "username":
            if username.strip():
                step = "password"
            else:
                message = "Enter username"
        elif action == "Submit" and step == "password":
            if mode == "login":
                # Check if it's an admin first
                if username in admins and admins[username]["password"] == password:
                    current_admin = username
                    current_user = None  # Clear current user when admin logs in
                    return "admin" # Return admin state
                elif username in users and users[username] == password:
                    current_user = username
                    current_admin = None  # Clear current admin when user logs in
                    user_data = load_user_data(current_user)
                    coins = user_data.get("coins", 0)
                    unlocked = set(user_data.get("unlocked", ["pistol"]))
                    upgrades = user_data.get("upgrades", {})
                    return "user" # Return user state
                else:
                    message = "Invalid username or password"
            elif mode == "register":
                if username and password:
                    if username in users or username in admins:
                        message = "Username already exists"
                    else:
                        users[username] = password
                        add_user_to_db(username, password)
                        current_user = username
                        current_admin = None  # Clear current admin when user logs in
                        user_data = {
                            "coins": 0,
                            "unlocked": set(["pistol"]),
                            "upgrades": {},
                            "score": 0,
                            "kills": 0,
                            "weapon": "pistol",
                            "ammo": default_ammo.copy()
                        }
                        save_user_data(current_user, user_data)
                        coins = 0
                        unlocked = set(["pistol"])
                        upgrades = {}
                        return "user" # Return user state
                else:
                    message = "Enter username and password"

        pygame.display.flip()
        clock.tick(FPS)

# ---------------- Menu & Leaderboard screens ----------------
def draw_buttons(buttons, mx, my, click):
    """Draws a list of buttons and returns the label of the clicked one."""
    for rect, label in buttons:
        color = (80, 80, 80)
        if rect.collidepoint((mx, my)):
            color = (120, 120, 120)
            if click:
                return label
        pygame.draw.rect(screen, color, rect, border_radius=8)
        draw_text(screen, label, 24, rect.centerx, rect.centery, color=WHITE, center=True)
    return None

    
def main_menu():
    """Displays the main menu and handles user interactions."""
    global current_user, current_admin, coins, unlocked, upgrades, daily_mission
    if not current_user and not current_admin:
        coins = 0
        unlocked = set(["pistol"])
        upgrades = {}
    elif current_user:
        # Ensure global coins, unlocked, upgrades are updated from DB on menu entry
        user_data = load_user_data(current_user)
        coins = user_data.get("coins", 0)
        unlocked = set(user_data.get("unlocked", ["pistol"]))
        upgrades = user_data.get("upgrades", {})
    
    # Reset daily mission when entering main menu (for simplicity, new mission each game session)
    reset_daily_mission()

    while True:
        screen.fill(BG)
        # Title positioned higher for better balance
        draw_text(screen, "War.io", 48, current_width // 2, current_height // 2 - int(current_height * 0.23), color=WHITE, center=True)
        # Instructions with better spacing
       
        # Move buttons below the War.io description for neatness
        button_w, button_h = int(current_width * 0.18), int(current_height * 0.07)
        button_spacing = int(current_height * 0.09)
        start_y = current_height // 2 - int(current_height * 0.05)

        # Show small leaderboard preview on the right
        draw_text(screen, "Top Scores:", 18, current_width - int(current_width * 0.18), int(current_height * 0.07), color=WHITE)
        for i, entry in enumerate(leaderboard[:5]):
            draw_text(screen, f"{i+1}. {entry['name']}  S:{entry['score']}  K:{entry['kills']}", 16, current_width - int(current_width * 0.18), int(current_height * 0.11) + i*int(current_height * 0.035), color=GRAY)
        # Show coins
        draw_text(screen, f"Coins: {coins}", 20, int(current_width * 0.008), current_height - int(current_height * 0.07), color=YELLOW)

        # Show Daily Mission
        if current_user:
            if "weapon" in daily_mission:
                mission_text = daily_mission["desc"].format(target=daily_mission["target"], weapon=daily_mission["weapon"])
            else:
                mission_text = daily_mission["desc"].format(target=daily_mission["target"])
            progress_text = f"Progress: {daily_mission['progress']}/{daily_mission['target']}"
            reward_text = f"Reward: {daily_mission['reward']} coins"
            status_text = "Completed!" if daily_mission["completed"] else "In Progress"

            draw_text(screen, "Daily Mission:", 16, current_width - 200, current_height - 100, color=WHITE)
            draw_text(screen, mission_text, 14, current_width - 200, current_height - 80, color=GRAY)
            draw_text(screen, progress_text, 14, current_width - 200, current_height - 64, color=GRAY)
            draw_text(screen, reward_text, 14, current_width - 200, current_height - 48, color=YELLOW)
            draw_text(screen, status_text, 14, current_width - 200, current_height - 32, color=GREEN if daily_mission["completed"] else YELLOW)


        mx, my = pygame.mouse.get_pos()
        click = False
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                # Save user data on quit if logged in
                if current_user:
                    user_data = {
                        "coins": coins,
                        "unlocked": unlocked,
                        "upgrades": upgrades
                    }
                    save_user_data(current_user, user_data)
                pygame.quit()
                return "quit"
            if ev.type == pygame.VIDEORESIZE:
                handle_window_resize(ev)
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                click = True
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    # Save user data on quit if logged in
                    if current_user:
                        user_data = {
                            "coins": coins,
                            "unlocked": unlocked,
                            "upgrades": upgrades
                        }
                        save_user_data(current_user, user_data)
                    pygame.display.flip()
                    pygame.quit()
                    return "quit"

        if current_user:
            draw_text(screen, f"Logged in as: {current_user}", 20, current_width // 2, current_height // 2 - int(current_height * 0.15), color=GREEN, center=True)
            button_labels = ["Start Game", "Quiz", "Shop", "Leaderboard", "Logout", "Quit"]
            buttons = []
            for i, label in enumerate(button_labels):
                y = start_y + i * button_spacing
                buttons.append((pygame.Rect(current_width // 2 - button_w // 2, y, button_w, button_h), label))
            choice = draw_buttons(buttons, mx, my, click)
            if choice == "Logout":
                # Save user data on logout
                if current_user:
                    user_data = {
                        "coins": coins,
                        "unlocked": unlocked,
                        "upgrades": upgrades
                    }
                    save_user_data(current_user, user_data)
                current_user = None
                # Reset global coins, unlocked, upgrades on logout
                coins = 0
                unlocked = set(["pistol"])
                upgrades = {}
                continue
        elif current_admin: # Admin is logged in
            draw_text(screen, f"Logged in as: {current_admin} (Admin)", 20, current_width // 2, current_height // 2 - int(current_height * 0.15), color=MAGENTA, center=True)
            button_labels = ["Admin Panel", "Logout", "Quit"]
            buttons = []
            for i, label in enumerate(button_labels):
                y = start_y + i * button_spacing
                buttons.append((pygame.Rect(current_width // 2 - button_w // 2, y, button_w, button_h), label))
            choice = draw_buttons(buttons, mx, my, click)
            if choice == "Admin Panel":
                return "admin_panel"
            elif choice == "Logout":
                current_admin = None
                continue
            elif choice == "Quit":
                pygame.quit()
                return "quit"
        else: # No one is logged in
            # Draw login button at top left
            login_btn = pygame.Rect(10, 10, 100, 40)
            pygame.draw.rect(screen, (80,80,80), login_btn, border_radius=8)
            draw_text(screen, "Login", 24, login_btn.centerx, login_btn.centery, color=WHITE, center=True)
            if click and login_btn.collidepoint(mx, my):
                login_result = login_screen()
                if login_result == "user":
                    # After user login, reload global user data
                    if current_user:
                        user_data = load_user_data(current_user)
                        coins = user_data.get("coins", 0)
                        unlocked = set(user_data.get("unlocked", ["pistol"]))
                        upgrades = user_data.get("upgrades", {})
                elif login_result == "admin":
                    # Admin logged in, current_admin is set
                    pass
                continue
            button_labels = ["Start Game", "Quiz", "Shop", "Leaderboard", "Quit"]
            buttons = []
            for i, label in enumerate(button_labels):
                y = start_y + i * button_spacing
                buttons.append((pygame.Rect((current_width - button_w) // 2, y, button_w, button_h), label))
            choice = draw_buttons(buttons, mx, my, click)

        pygame.display.flip()
        clock.tick(FPS)
        if choice == "Start Game":
            return "game"
        if choice == "Leaderboard":
            leaderboard_screen()
        if choice == "Quiz":
            run_quiz()
        if choice == "Shop":
            shop_screen()
        if choice == "Quit":
            # Save user data on quit if logged in
            if current_user:
                user_data = {
                    "coins": coins,
                    "unlocked": unlocked,
                    "upgrades": upgrades
                }
                save_user_data(current_user, user_data)
            pygame.quit()
            return "quit"


def leaderboard_screen():
    """Displays the game leaderboard."""
    global leaderboard # Ensure we use the global leaderboard
    leaderboard = load_leaderboard() # Reload leaderboard to get latest scores
    while True:
        screen.fill(BG)
        draw_text(screen, "Leaderboard", 48, current_width // 2, int(current_height * 0.11), color=WHITE, center=True)
        y = int(current_height * 0.23)
        if leaderboard:
            for i, e in enumerate(leaderboard):
                draw_text(screen, f"{i+1}. {e['name']}", 28, current_width // 2 - int(current_width * 0.12), y, color=WHITE)
                draw_text(screen, f"S:{e['score']}  K:{e['kills']}", 22, current_width // 2 + int(current_width * 0.09), y + int(current_height * 0.01), color=GRAY)
                y += int(current_height * 0.035)
        else:
            draw_text(screen, "No scores yet. Play to add your name!", 20, current_width // 2, current_height // 2, color=GRAY, center=True)

        mx, my = pygame.mouse.get_pos()
        click = False
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.VIDEORESIZE:
                handle_window_resize(ev)
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                click = True

        back_btn = pygame.Rect(current_width // 2 - int(current_width * 0.15), current_height - int(current_height * 0.16), int(current_width * 0.3), int(current_height * 0.07))
        res = draw_buttons([(back_btn, "Back")], mx, my, click)
        pygame.display.flip()
        clock.tick(FPS)
        if res == "Back":
            return

# ---------------- Shop Screen ----------------
# Load weapon images (tetap sama seperti sebelumnya)
weapon_images = {}
weapon_image_paths = {
    "pistol": "assets/images/pistol.png",
    "shotgun": "assets/images/shotgun.png",
    "rocket": "assets/images/rocket.png",
    "machinegun": "assets/images/machinegun.png",
    "area_damage": "assets/images/area_damage.png",
    "sniper": "assets/images/sniper.png",
    "flamethrower": "assets/images/flamethrower.png",
    "laser": "assets/images/laser.png",
    "grenade": "assets/images/grenade.png",
    "plasma": "assets/images/plasma.png",
    "sword": "assets/images/sword.png",
    "gravity_gun": "assets/images/gravity_gun.png",
    "railgun": "assets/images/railgun.png",
    "minigun": "assets/images/minigun.png",
    "bfg": "assets/images/bfg.png",
    "freeze_ray": "assets/images/freeze_ray.png",
    "poison_gun": "assets/images/poison_gun.png",
    "lightning_gun": "assets/images/lightning_gun.png",
    "acid_gun": "assets/images/acid_gun.png",
    "teleport_gun": "assets/images/teleport_gun.png",
    "black_hole_gun": "assets/images/black_hole_gun.png",
    "time_bomb": "assets/images/time_bomb.png",
    "chain_lightning": "assets/images/chain_lightning.png",
    "homing_missile": "assets/images/homing_missile.png",
    "energy_sword": "assets/images/energy_sword.png",
    "flak_cannon": "assets/images/flak_cannon.png",
    "pulse_rifle": "assets/images/pulse_rifle.png",
    "gauss_rifle": "assets/images/gauss_rifle.png",
    "cryo_blaster": "assets/images/cryo_blaster.png",
    "napalm_launcher": "assets/images/napalm_launcher.png",
    "sonic_blaster": "assets/images/sonic_blaster.png",
    "disintegration_ray": "assets/images/disintegration_ray.png"
}

for weapon_name, path in weapon_image_paths.items():
    try:
        full_path = os.path.join(os.path.dirname(__file__), path)
        img = pygame.image.load(full_path).convert_alpha()
        img = pygame.transform.scale(img, (40, 40))  # Ukuran tetap untuk konsistensi
        weapon_images[weapon_name] = img
    except pygame.error:
        print(f"Warning: Could not load image for {weapon_name} from {path}. Using fallback.")
        weapon_images[weapon_name] = None

def shop_screen():
    """Displays the in-game shop for weapons and upgrades."""
    global coins, unlocked, upgrades

    scroll_offset = 0
    item_height = int(current_height * 0.07)
    item_gap = 8  # Jarak antar button/item (spacing vertikal)

    def draw_weapon_list_and_buttons():
        """Draws the list of weapons with image on left and text on right, with spacing."""
        draw_text(screen, "Weapons", 32, current_width // 4, int(current_height * 0.18), color=WHITE, center=True)
        y_start = int(current_height * 0.25)
        x_start = current_width // 4 - int(current_width * 0.16)
        buttons = []
        all_weapons = [
            "shotgun", "rocket", "machinegun", "area_damage", "sniper",
            "flamethrower", "laser", "grenade", "plasma", "sword", "gravity_gun",
            "railgun", "minigun", "bfg", "freeze_ray", "poison_gun", "lightning_gun",
            "acid_gun", "teleport_gun", "black_hole_gun", "time_bomb", "chain_lightning",
            "homing_missile", "energy_sword", "flak_cannon", "pulse_rifle", "gauss_rifle",
            "cryo_blaster", "napalm_launcher", "sonic_blaster", "disintegration_ray"
        ]
        visible_height = current_height - y_start - int(current_height * 0.2)
        # Hitung total height dengan spacing
        total_height = len(all_weapons) * item_height + max(0, (len(all_weapons) - 1)) * item_gap
        max_scroll = max(0, total_height - visible_height)
        nonlocal scroll_offset
        scroll_offset = max(0, min(scroll_offset, max_scroll))

        y = y_start - scroll_offset
        for i, w in enumerate(all_weapons):
            if y + item_height > y_start and y < current_height:
                price = weapon_prices.get(w, 0)
                owned = w in unlocked
                color = GREEN if owned else (GRAY if coins >= price else RED)
                status = "Owned" if owned else f"Buy ({price} coins)"
                weapon_name = w.replace('_', ' ').title()
                text = f"{weapon_name}: {status}"
                
                rect = pygame.Rect(x_start, y, int(current_width * 0.32), item_height)
                pygame.draw.rect(screen, (60, 60, 60), rect, border_radius=6)
                
                # Gambar di kiri (center vertically)
                img_x = rect.left + 25  # Center gambar di 25px dari left rect
                if weapon_images.get(w):
                    img = weapon_images[w]
                    img_rect = img.get_rect(center=(img_x, rect.centery))
                    screen.blit(img, img_rect)
                    
                    # Teks di kanan gambar (top-left alignment, dengan padding 10px setelah gambar)
                    text_x = rect.left + 50 + 10  # Setelah gambar (40px + padding 10px)
                    text_y = rect.centery - 10  # Adjust y agar centered vertically
                    # Render teks manual untuk presisi
                    f = pygame.font.SysFont(base_font_name, 20)
                    txt_surf = f.render(text, True, color)
                    screen.blit(txt_surf, (text_x, text_y))
                else:
                    # Jika no image, center teks di rect
                    draw_text(screen, text, 20, rect.centerx, rect.centery, color=color, center=True)
                
                buttons.append((rect, w))
            # Increment y dengan spacing
            y += item_height + item_gap
        return buttons, max_scroll

    def draw_upgrade_list_and_buttons():
        """Draws the list of upgrades (no images, text centered), with spacing."""
        draw_text(screen, "Upgrades", 32, 3 * current_width // 4, int(current_height * 0.18), color=WHITE, center=True)
        y = int(current_height * 0.25)
        x_start = 3 * current_width // 4 - int(current_width * 0.16)
        buttons = []
        for i, u in enumerate(upgrade_prices.keys()):
            price = upgrade_prices[u]
            owned = upgrades.get(u, 0) > 0
            color = GREEN if owned else (GRAY if coins >= price else RED)
            status = "Owned" if owned else f"Buy ({price} coins)"
            text = f"{u.replace('_', ' ').title()}: {status}"
            rect = pygame.Rect(x_start, y, int(current_width * 0.32), item_height)
            pygame.draw.rect(screen, (60, 60, 60), rect, border_radius=6)
            draw_text(screen, text, 20, rect.centerx, rect.centery, color=color, center=True)
            buttons.append((rect, u))
            # Increment y dengan spacing
            y += item_height + item_gap
        return buttons

    while True:
        screen.fill(BG)
        draw_text(screen, "Shop", 48, current_width // 2, int(current_height * 0.11), color=WHITE, center=True)
        draw_text(screen, f"Coins: {coins}", 24, current_width // 2, int(current_height * 0.15), color=YELLOW, center=True)

        weapon_buttons, max_scroll = draw_weapon_list_and_buttons()
        upgrade_buttons = draw_upgrade_list_and_buttons()

        mx, my = pygame.mouse.get_pos()
        click = False
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.VIDEORESIZE:
                handle_window_resize(ev)
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                click = True
            if ev.type == pygame.MOUSEWHEEL:
                scroll_offset -= ev.y * (item_height + item_gap)  # Scroll by item height + gap untuk smooth
                scroll_offset = max(0, min(scroll_offset, max_scroll))

        action = None
        if click:
            for rect, item_name in weapon_buttons:
                if rect.collidepoint(mx, my):
                    action = ("weapon", item_name)
                    break
            if not action:
                for rect, item_name in upgrade_buttons:
                    if rect.collidepoint(mx, my):
                        action = ("upgrade", item_name)
                        break

        if action:
            item_type, item_name = action
            if item_type == "weapon":
                if item_name not in unlocked:
                    price = weapon_prices.get(item_name, 0)
                    if coins >= price:
                        coins -= price
                        unlocked.add(item_name)
                        save_coins(coins)
                        save_unlocked(unlocked)
                        print(f"Unlocked {item_name.replace('_', ' ').title()} for {price} coins.")
                    else:
                        print("Not enough coins!")
                else:
                    print(f"{item_name.replace('_', ' ').title()} already unlocked.")
            elif item_type == "upgrade":
                if upgrades.get(item_name, 0) == 0:
                    price = upgrade_prices.get(item_name, 0)
                    if coins >= price:
                        coins -= price
                        upgrades[item_name] = 1
                        save_coins(coins)
                        save_upgrades(upgrades)
                        print(f"Bought {item_name.replace('_', ' ').title()} upgrade for {price} coins.")
                    else:
                        print("Not enough coins!")
                else:
                    print(f"{item_name.replace('_', ' ').title()} already owned.")

        back_btn = pygame.Rect(current_width // 2 - int(current_width * 0.15), current_height - int(current_height * 0.16), int(current_width * 0.3), int(current_height * 0.07))
        res = draw_buttons([(back_btn, "Back")], mx, my, click)
        pygame.display.flip()
        clock.tick(FPS)
        if res == "Back":
            return


# ---------------- Quiz Screen ----------------
def run_quiz():
    """Runs an in-game quiz for the player."""
    global coins # Ensure global coins is updated
    if not current_user:
        screen.fill(BG)
        draw_text(screen, "Please log in to take the quiz.", 28, current_width // 2, current_height // 2, color=RED, center=True)
        pygame.display.flip()
        pygame.time.wait(1500)
        return

    # Simple quiz flow: 10 questions from pool of 40, next with Enter, track score
    # Randomize questions each time quiz is run
    questions = random.sample(quiz_questions, 10)
    idx = 0
    score = 0
    selected = None
    in_feedback = False
    feedback_timer = 0
    correct_rect = None
    selected_rect = None
    selected_letter = None
    correct = False

    while True:
        screen.fill(BG)
        q = questions[idx]
        draw_text(screen, f"Quiz ({idx+1}/10)", 28, current_width // 2, int(current_height * 0.11), color=WHITE, center=True)
        draw_text(screen, q['question'], 22, current_width // 2, int(current_height * 0.16), color=WHITE, center=True)

        # draw options
        oy = int(current_height * 0.25)
        option_rects = []
        for i, opt in enumerate(q['options']):
            r = pygame.Rect(current_width // 2 - int(current_width * 0.25), oy + i*int(current_height * 0.08), int(current_width * 0.5), int(current_height * 0.06))
            option_rects.append((r, opt))
            pygame.draw.rect(screen, (60,60,60), r, border_radius=6)
            draw_text(screen, opt, 20, r.centerx, r.centery, color=WHITE, center=True)

        draw_text(screen, "Click an option then press ENTER to confirm.", 16, current_width // 2, current_height - int(current_height * 0.07), color=GRAY, center=True)
        draw_text(screen, "ESC to quit quiz.", 16, current_width // 2, current_height - int(current_height * 0.04), color=GRAY, center=True)

        mx, my = pygame.mouse.get_pos()
        click = False
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.VIDEORESIZE:
                handle_window_resize(ev)
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and not in_feedback:
                click = True
                for i, (r, opt) in enumerate(option_rects):
                    if r.collidepoint(mx, my):
                        selected = opt[0]  # letter A/B/C/D
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return
                if ev.key == pygame.K_RETURN and selected is not None and not in_feedback:
                    # check answer
                    selected_letter = selected
                    correct = selected.upper() == q['answer']
                    if correct:
                        score += 1
                    in_feedback = True
                    feedback_timer = 1000  # ms
                    selected = None
                    # find rects
                    for r, opt in option_rects:
                        if opt[0].upper() == q['answer']:
                            correct_rect = r
                        if opt[0].upper() == selected_letter.upper():
                            selected_rect = r

        # draw selection highlight
        if selected is not None and not in_feedback:
            for r, opt in option_rects:
                if opt[0].upper() == selected.upper():
                    pygame.draw.rect(screen, (100,100,140), r, border_radius=6)
                    draw_text(screen, opt, 20, r.centerx, r.centery, color=WHITE, center=True)

        # feedback animation
        if in_feedback:
            # highlight correct
            if correct_rect:
                highlight_surf = pygame.Surface((correct_rect.width, correct_rect.height), pygame.SRCALPHA)
                highlight_surf.fill((*GREEN, 128))
                screen.blit(highlight_surf, correct_rect.topleft)
            # if incorrect, highlight selected with red
            if not correct and selected_rect:
                highlight_surf = pygame.Surface((selected_rect.width, selected_rect.height), pygame.SRCALPHA)
                highlight_surf.fill((*RED, 128))
                screen.blit(highlight_surf, selected_rect.topleft)
            feedback_timer -= clock.get_time()
            if feedback_timer <= 0:
                in_feedback = False
                correct_rect = None
                selected_rect = None
                selected_letter = None
                idx += 1
                if idx >= len(questions):
                    # show result briefly and return
                    earned_coins = score * 10
                    coins += earned_coins
                    save_coins(coins) # Save updated coins to DB
                    end_message = f"Quiz selesai! Score: {score}/{len(questions)} Coins: +{earned_coins}"
                    screen.fill(BG)
                    draw_text(screen, end_message, 28, current_width // 2, current_height // 2, color=WHITE, center=True)
                    pygame.display.flip()
                    pygame.time.wait(1500)
                    return

        pygame.display.flip()
        clock.tick(FPS)

# ---------------- Admin Panel Screen ----------------
def admin_panel_screen():
    """Displays the admin panel and handles admin actions."""
    global current_admin, users # Need access to users for management
    message = ""
    input_box_active = False
    input_box_text = ""
    input_box_rect = pygame.Rect(current_width // 2 - 150, 400, 300, 40)
    action_mode = None # "delete_user", "add_admin"

    while True:
        screen.fill(BG)
        draw_text(screen, "Admin Panel", 48, current_width // 2, 100, color=WHITE, center=True)
        draw_text(screen, f"Welcome, {current_admin}!", 28, current_width // 2, 150, color=MAGENTA, center=True)
        draw_text(screen, message, 20, current_width // 2, 200, color=RED, center=True)

        mx, my = pygame.mouse.get_pos()
        click = False
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.VIDEORESIZE:
                handle_window_resize(ev)
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                click = True
                if input_box_rect.collidepoint(ev.pos):
                    input_box_active = True
                else:
                    input_box_active = False
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if input_box_active:
                        input_box_active = False
                        input_box_text = ""
                        action_mode = None
                        message = ""
                    else:
                        return "menu" # Kembali ke menu utama
                if input_box_active:
                    if ev.key == pygame.K_RETURN:
                        if action_mode == "delete_user":
                            if input_box_text in users:
                                delete_user_from_db(input_box_text)
                                users.pop(input_box_text) # Update in-memory users
                                message = f"User '{input_box_text}' deleted."
                            else:
                                message = f"User '{input_box_text}' not found."
                        elif action_mode == "add_admin":
                            # For simplicity, adding admin with default password "adminpass" and empty permissions
                            # In a real app, you'd prompt for password and permissions
                            if input_box_text and input_box_text not in admins:
                                add_admin_to_db(input_box_text, "adminpass", {})
                                admins[input_box_text] = {"password": "adminpass", "permissions": {}} # Update in-memory admins
                                message = f"Admin '{input_box_text}' added with default password 'adminpass'."
                            else:
                                message = f"Admin '{input_box_text}' already exists or invalid name."
                        input_box_text = ""
                        input_box_active = False
                        action_mode = None
                    elif ev.key == pygame.K_BACKSPACE:
                        input_box_text = input_box_text[:-1]
                    else:
                        if ev.unicode.isprintable():
                            input_box_text += ev.unicode

        button_w, button_h = 250, 60
        button_spacing = 80
        start_y = 250

        buttons = [
            (pygame.Rect(current_width // 2 - button_w // 2, start_y, button_w, button_h), "View Game Stats"),
            (pygame.Rect(current_width // 2 - button_w // 2, start_y + button_spacing, button_w, button_h), "Delete User"),
            (pygame.Rect(current_width // 2 - button_w // 2, start_y + 2 * button_spacing, button_w, button_h), "Add Admin"),
            (pygame.Rect(current_width // 2 - button_w // 2, start_y + 3 * button_spacing, button_w, button_h), "Back to Menu")
        ]

        action = draw_buttons(buttons, mx, my, click)

        if action == "View Game Stats":
            stats = get_game_statistics()
            message = f"Total Users: {stats.get('total_users', 0)}, Active Users: {stats.get('active_users', 0)}, Total Score: {stats.get('total_score', 0)}, Total Kills: {stats.get('total_kills', 0)}, Leaderboard Entries: {stats.get('leaderboard_count', 0)}"
        elif action == "Delete User":
            action_mode = "delete_user"
            input_box_active = True
            message = "Enter username to delete:"
        elif action == "Add Admin":
            action_mode = "add_admin"
            input_box_active = True
            message = "Enter new admin username:"
        elif action == "Back to Menu":
            return "menu"

        if input_box_active:
            pygame.draw.rect(screen, WHITE, input_box_rect, 2)
            draw_text(screen, input_box_text, 24, input_box_rect.x + 5, input_box_rect.y + 5, color=WHITE)

        pygame.display.flip()
        clock.tick(FPS)

# ---------------- Main Game Loop ----------------
def game_loop():
    """Main game loop where the action happens."""
    global coins, unlocked, upgrades, is_raining, rain_duration, rain_start_time, rain_drops, daily_mission
    
    # Load user data if logged in, otherwise use defaults
    if current_user:
        user_data = load_user_data(current_user)
        initial_score = user_data.get("score", 0)
        initial_kills = user_data.get("kills", 0)
        initial_weapon = user_data.get("weapon", "pistol")
        initial_ammo = user_data.get("ammo", default_ammo.copy())
        unlocked = set(user_data.get("unlocked", ["pistol"]))
        upgrades = user_data.get("upgrades", {})
        coins = user_data.get("coins", 0)
    else:
        initial_score = 0
        initial_kills = 0
        initial_weapon = "pistol"
        initial_ammo = default_ammo.copy()
        unlocked = set(["pistol"])
        upgrades = {}
        coins = 0

    player = Player(current_width // 2, current_height // 2, initial_upgrades=upgrades)
    player.score = initial_score
    player.kills = initial_kills
    player.weapon = initial_weapon
    player.ammo = initial_ammo
    player.apply_upgrades(upgrades) # Apply upgrades to player instance

    bullets, enemies, particles, orbs, ammoboxes, powerups, mines = [], [], [], [], [], [], []
    game_over = False
    win = False
    entering_name = False
    name_buf = ""
    can_submit = False
    coins_added = False

    SPAWN_EVENT = pygame.USEREVENT + 1
    pygame.time.set_timer(SPAWN_EVENT, ENEMY_SPAWN_INTERVAL)

    MINE_SPAWN_EVENT = pygame.USEREVENT + 2
    pygame.time.set_timer(MINE_SPAWN_EVENT, 5000)  # Spawn mine every 5 seconds

    COMBO_RESET_EVENT = pygame.USEREVENT + 3
    pygame.time.set_timer(COMBO_RESET_EVENT, 3000)  # Reset combo every 3 seconds if no kill

    WEATHER_EVENT = pygame.USEREVENT + 4 # New event for weather changes
    pygame.time.set_timer(WEATHER_EVENT, random.randint(15000, 30000)) # Weather changes every 15-30 seconds

    mouse_pos = (0, 0)
    running = True

    weapon_list = ["pistol", "shotgun", "rocket", "machinegun", "area_damage", "sniper", "flamethrower", "laser", "grenade", "plasma", "sword", "gravity_gun", "railgun", "minigun", "bfg", "freeze_ray", "poison_gun", "lightning_gun", "acid_gun", "teleport_gun", "black_hole_gun", "time_bomb", "chain_lightning", "homing_missile", "energy_sword", "flak_cannon", "pulse_rifle", "gauss_rifle", "cryo_blaster", "napalm_launcher", "sonic_blaster", "disintegration_ray"]
    mouse_held = False

    # Reset weather and mission for new game
    stop_rain()
    reset_daily_mission()

    while running:
        dt = clock.tick(FPS) / 1000.0 # dt in seconds for consistent physics
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            elif event.type == pygame.VIDEORESIZE:
                handle_window_resize(event)
            elif event.type == SPAWN_EVENT and not game_over:
                if player.kills >= player.level * 10:
                    player.level += 1
                    if player.level % 5 == 0:
                        enemies.append(Boss(random.randint(100, current_width - 100), -60))
                else:
                    spawn_enemy(enemies, player.level)

            elif event.type == MINE_SPAWN_EVENT and not game_over:
                # Spawn mine at random position
                x = random.randint(50, current_width - 50)
                y = random.randint(50, current_height - 50)
                mines.append(Mine(x, y))
            
            elif event.type == COMBO_RESET_EVENT and not game_over:
                # Reset combo if no kill within the timer
                now = pygame.time.get_ticks()
                if now - player.last_kill_time >= player.combo_timer:
                    player.combo = 0
                    player.combo_multiplier = 1.0
            
            elif event.type == WEATHER_EVENT and not game_over: # Handle weather changes
                if is_raining:
                    stop_rain()
                    pygame.time.set_timer(WEATHER_EVENT, random.randint(15000, 30000)) # Next weather event after clear
                else:
                    start_rain()
                    pygame.time.set_timer(WEATHER_EVENT, rain_duration) # Next weather event after rain duration

            elif event.type == pygame.MOUSEMOTION:
                mouse_pos = event.pos
            elif event.type == pygame.MOUSEBUTTONDOWN and not game_over:
                if event.button == 1:
                    mouse_held = True
                    player.shoot(mouse_pos, bullets, particles)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    mouse_held = False
            elif event.type == pygame.MOUSEWHEEL and not game_over:
                if event.y > 0: # Scroll up
                    current_idx = weapon_list.index(player.weapon)
                    for i in range(1, len(weapon_list) + 1):
                        next_idx = (current_idx + i) % len(weapon_list)
                        if weapon_list[next_idx] in unlocked:
                            player.weapon = weapon_list[next_idx]
                            break
                elif event.y < 0: # Scroll down
                    current_idx = weapon_list.index(player.weapon)
                    for i in range(1, len(weapon_list) + 1):
                        prev_idx = (current_idx - i + len(weapon_list)) % len(weapon_list) # Ensure positive index
                        if weapon_list[prev_idx] in unlocked:
                            player.weapon = weapon_list[prev_idx]
                            break
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # if entering name, cancel entry, else go to menu
                    if entering_name:
                        entering_name = False
                    else:
                        return "menu"
                if event.key == pygame.K_r and game_over:
                    return "restart"

                if not game_over:
                    if event.key == pygame.K_SPACE:
                        player.shoot(mouse_pos, bullets, particles)
                    if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                        started = player.start_dash()
                        if started:
                            for _ in range(6):
                                ang = random.uniform(0, math.tau)
                                speed = random.uniform(1, 4)
                                particles.append(Particle(player.pos.xy, Vector2(math.cos(ang)*speed, math.sin(ang)*speed),
                                                          radius=random.uniform(2,4), life=0.3, color=CYAN))
                    if event.key == pygame.K_q:
                        player.activate_shield_skill()
                    # weapon switching
                    if event.key == pygame.K_1 and "pistol" in unlocked: player.weapon = "pistol"
                    if event.key == pygame.K_2 and "shotgun" in unlocked: player.weapon = "shotgun"
                    if event.key == pygame.K_3 and "rocket" in unlocked: player.weapon = "rocket"
                    if event.key == pygame.K_4 and "machinegun" in unlocked: player.weapon = "machinegun"
                    if event.key == pygame.K_5 and "area_damage" in unlocked: player.weapon = "area_damage"
                    if event.key == pygame.K_6 and "sniper" in unlocked: player.weapon = "sniper"
                    if event.key == pygame.K_7 and "flamethrower" in unlocked: player.weapon = "flamethrower"
                    if event.key == pygame.K_8 and "laser" in unlocked: player.weapon = "laser"
                    if event.key == pygame.K_9 and "grenade" in unlocked: player.weapon = "grenade"
                    if event.key == pygame.K_0 and "sword" in unlocked: player.weapon = "sword"
                    if event.key == pygame.K_MINUS and "gravity_gun" in unlocked: player.weapon = "gravity_gun" # Key for gravity gun

                else:
                    # when game_over: allow name entry if qualifies
                    if entering_name:
                        if event.key == pygame.K_RETURN:
                            # submit name
                            if name_buf.strip() == "":
                                add_to_leaderboard("Player", player.score, player.kills)
                            else:
                                add_to_leaderboard(name_buf[:12], player.score, player.kills)
                            entering_name = False
                            can_submit = False
                        elif event.key == pygame.K_BACKSPACE:
                            name_buf = name_buf[:-1]
                        else:
                            if len(name_buf) < 12:
                                if event.unicode.isprintable():
                                    name_buf += event.unicode

        keys = pygame.key.get_pressed()
        if not game_over:
            player.update(dt, keys, particles)

            if mouse_held:
                player.shoot(mouse_pos, bullets, particles)
            if keys[pygame.K_SPACE]:
                player.shoot(mouse_pos, bullets, particles)

            for b in bullets:
                b.update(dt)

            for e in enemies:
                if isinstance(e, Boss):
                    e.update(dt, player.pos, bullets, player, particles, enemies) # Pass player and particles for boss phase 2
                else:
                    e.update(dt, player.pos)
            
            # Gravity Gun effect: pull enemies towards gravity bullets
            for b in list(bullets):
                if b.btype == "gravity" and b.alive:
                    for e in list(enemies):
                        dist = (e.pos - b.pos).length()
                        if dist < 150: # Radius of gravity pull
                            direction = (b.pos - e.pos).normalize()
                            e.pos += direction * 2 * dt # Pull enemies towards the bullet

            # grenade explosions
            grenades_to_explode = [b for b in bullets if b.btype == "grenade" and b.exploded]
            for g in grenades_to_explode:
                spawn_explosion(particles, g.pos.x, g.pos.y)
                for ee in list(enemies):
                    if (g.pos - ee.pos).length() < EXPLOSION_RADIUS:
                        ee.hp -= 60
                        spawn_blood(particles, ee.pos.x, ee.pos.y, intensity=8)
                        if ee.hp <= 0:
                            player.score += int(10 * player.combo_multiplier) # Apply combo bonus
                            player.kills += 1
                            player.update_combo() # Update combo on kill
                            update_daily_mission(player, enemy_killed_weapon=player.weapon) # Update daily mission
                            if random.random() < 0.25 or isinstance(ee, Boss):
                                orbs.append(HealthOrb(ee.pos.x, ee.pos.y))
                            if random.random() < 0.25 or isinstance(ee, Boss):
                                ammoboxes.append(AmmoBox(ee.pos.x, ee.pos.y))

                            if random.random() < 0.12:
                                ptype = random.choice(["dash", "damage"])
                                powerups.append(Powerup(ee.pos.x, ee.pos.y, ptype))
                            try: enemies.remove(ee)
                            except ValueError: pass
                try: bullets.remove(g)
                except ValueError: pass

            # bullets -> enemies collisions
            for b in list(bullets):
                if not b.alive:
                    continue
                if b.owner == "player":
                    for e in list(enemies):
                        if (b.pos - e.pos).length() < (b.radius + e.size):
                            if b.btype == "rocket":
                                spawn_explosion(particles, b.pos.x, b.pos.y)
                                for ee in list(enemies):
                                    if (b.pos - ee.pos).length() < EXPLOSION_RADIUS:
                                        ee.hp -= EXPLOSION_DAMAGE
                                        spawn_blood(particles, ee.pos.x, ee.pos.y, intensity=PARTICLE_COUNT//2)
                                        if ee.hp <= 0:
                                            player.score += int(15 * player.combo_multiplier) # Apply combo bonus
                                            player.kills += 1
                                            player.update_combo() # Update combo on kill
                                            update_daily_mission(player, enemy_killed_weapon=player.weapon) # Update daily mission
                                            if random.random() < 0.25 or isinstance(ee, Boss): orbs.append(HealthOrb(ee.pos.x, ee.pos.y))
                                            if random.random() < 0.25 or isinstance(ee, Boss): ammoboxes.append(AmmoBox(ee.pos.x, ee.pos.y))
                                            if random.random() < 0.12:
                                                ptype = random.choice(["dash", "damage"])
                                                powerups.append(Powerup(ee.pos.x, ee.pos.y, ptype))
                                            try: enemies.remove(ee)
                                            except ValueError: pass
                                b.alive = False
                                break
                            elif b.btype == "plasma":
                                spawn_explosion(particles, b.pos.x, b.pos.y, count=PARTICLE_COUNT*4)
                                for ee in list(enemies):
                                    if (b.pos - ee.pos).length() < EXPLOSION_RADIUS * 0.7:
                                        ee.hp -= b.damage
                                        spawn_blood(particles, ee.pos.x, ee.pos.y, intensity=6)
                                        if ee.hp <= 0:
                                            player.score += int(15 * player.combo_multiplier) # Apply combo bonus
                                            player.kills += 1
                                            player.update_combo() # Update combo on kill
                                            update_daily_mission(player, enemy_killed_weapon=player.weapon) # Update daily mission
                                            if random.random() < 0.25 or isinstance(ee, Boss): orbs.append(HealthOrb(ee.pos.x, ee.pos.y))
                                            if random.random() < 0.25 or isinstance(ee, Boss): ammoboxes.append(AmmoBox(ee.pos.x, ee.pos.y))
                                            if random.random() < 0.12:
                                                ptype = random.choice(["dash", "damage"])
                                                powerups.append(Powerup(ee.pos.x, ee.pos.y, ptype))
                                            try: enemies.remove(ee)
                                            except ValueError: pass
                                b.alive = False
                                break
                            elif b.btype == "laser":
                                e.hp -= b.damage
                                spawn_blood(particles, b.pos.x, b.pos.y, intensity=4)
                                spawn_sparks(particles, b.pos.x, b.pos.y, count=4)
                                if e.hp <= 0:
                                    player.score += int(10 * player.combo_multiplier) # Apply combo bonus
                                    player.kills += 1
                                    player.update_combo() # Update combo on kill
                                    update_daily_mission(player, enemy_killed_weapon=player.weapon) # Update daily mission
                                    if random.random() < 0.25 or isinstance(e, Boss): orbs.append(HealthOrb(e.pos.x, e.pos.y))
                                    if random.random() < 0.25 or isinstance(e, Boss): ammoboxes.append(AmmoBox(e.pos.x, e.pos.y))
                                    if random.random() < 0.12:
                                        ptype = random.choice(["dash", "damage"])
                                        powerups.append(Powerup(e.pos.x, e.pos.y, ptype))
                                    try: enemies.remove(e)
                                    except ValueError: pass
                                # laser continues
                            elif b.btype == "gravity": # Gravity gun does no direct damage
                                # Handled by pulling enemies
                                pass
                            else:
                                dmg = b.damage
                                e.hp -= dmg
                                spawn_blood(particles, b.pos.x, b.pos.y, intensity=6)
                                spawn_sparks(particles, b.pos.x, b.pos.y, count=4)
                                if b.btype not in ("laser",):
                                    b.alive = False
                                if e.hp <= 0:
                                    player.score += int(10 * player.combo_multiplier) # Apply combo bonus
                                    player.kills += 1
                                    player.update_combo() # Update combo on kill
                                    update_daily_mission(player, enemy_killed_weapon=player.weapon) # Update daily mission
                                    if random.random() < 0.25 or isinstance(e, Boss): orbs.append(HealthOrb(e.pos.x, e.pos.y))
                                    if random.random() < 0.25 or isinstance(e, Boss): ammoboxes.append(AmmoBox(e.pos.x, e.pos.y))
                                    if random.random() < 0.12:
                                        ptype = random.choice(["dash", "damage"])
                                        powerups.append(Powerup(e.pos.x, e.pos.y, ptype))
                                    try: enemies.remove(e)
                                    except ValueError: pass
                                break

            bullets = [b for b in bullets if b.alive]

            # enemy contact with player
            damage = 0  # default, tidak kena hit

            for e in list(enemies):
                if (e.pos - player.pos).length() < (e.size + player.size - 6):
                    push = (player.pos - e.pos)
                    if push.length_squared() == 0:
                        push = Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
                    push = push.normalize() * 8
                    player.pos += push
                    damage = 12
                    e.pos -= push * 0.3   # <- pindahkan ini ke dalam blok tabrakan

            if damage > 0:
                if player_hurt_sound: player_hurt_sound.play()
                if player.shield_skill_active: # Shield skill makes player immune
                    # No damage taken, but shield HP might still be affected if it was a temporary shield
                    # For shield skill, we assume full immunity
                    pass
                elif player.shield_hp > 0:
                    if player.shield_hp >= damage:
                        player.shield_hp -= damage
                        damage = 0
                    else:
                        damage -= player.shield_hp
                        player.shield_hp = 0
                player.hp -= damage
                spawn_blood(particles, player.pos.x, player.pos.y, intensity=8)
                if player.hp <= 0:
                    game_over = True


            # boss bullets hit player
            for b in list(bullets):
                if b.owner == "boss" and b.alive:
                    if (b.pos - player.pos).length() < (b.radius + player.size):
                        damage = b.damage
                        if player_hurt_sound: player_hurt_sound.play()
                        if player.shield_skill_active: # Shield skill makes player immune
                            pass
                        elif player.shield_hp > 0:
                            if player.shield_hp >= damage:
                                player.shield_hp -= damage
                                damage = 0
                            else:
                                damage -= player.shield_hp
                                player.shield_hp = 0
                        player.hp -= damage
                        b.alive = False
                        spawn_blood(particles, player.pos.x, player.pos.y, intensity=12)
                        if player.hp <= 0:
                            game_over = True
            
            # Mine collisions
            for mine in list(mines):
                if (mine.pos - player.pos).length() < (mine.size + player.size):
                    damage = mine.damage
                    if player_hurt_sound: player_hurt_sound.play()
                    if player.shield_skill_active: # Shield skill makes player immune
                        pass
                    elif player.shield_hp > 0:
                        if player.shield_hp >= damage:
                            player.shield_hp -= damage
                            damage = 0
                        else:
                            damage -= player.shield_hp
                            player.shield_hp = 0
                    player.hp -= damage
                    spawn_explosion(particles, mine.pos.x, mine.pos.y)
                    mines.remove(mine)
                    if player.hp <= 0:
                        game_over = True
                else: # Mines can also damage enemies
                    for e in list(enemies):
                        if (mine.pos - e.pos).length() < (mine.size + e.size):
                            e.hp -= mine.damage
                            spawn_explosion(particles, mine.pos.x, mine.pos.y)
                            mines.remove(mine)
                            if e.hp <= 0:
                                if enemy_death_sound: enemy_death_sound.play()
                                player.score += int(10 * player.combo_multiplier) # Apply combo bonus
                                player.kills += 1
                                player.update_combo() # Update combo on kill
                                update_daily_mission(player, enemy_killed_weapon="mine") # Update daily mission
                                if random.random() < 0.25 or isinstance(e, Boss): orbs.append(HealthOrb(e.pos.x, e.pos.y))
                                if random.random() < 0.25 or isinstance(e, Boss): ammoboxes.append(AmmoBox(e.pos.x, e.pos.y))
                                if random.random() < 0.12:
                                    ptype = random.choice(["dash", "damage"])
                                    powerups.append(Powerup(e.pos.x, e.pos.y, ptype))
                                try: enemies.remove(e)
                                except ValueError: pass
                            break # Only one enemy can trigger a mine explosion

            # pickups
            for orb in list(orbs):
                if (orb.pos - player.pos).length() < (orb.size + player.size):
                    player.hp = min(player.max_hp, player.hp + orb.heal_amount)
                    if powerup_sound: powerup_sound.play()
                    orbs.remove(orb)

            for box in list(ammoboxes):
                if (box.pos - player.pos).length() < (box.size + player.size):
                    for k, v in box.fill.items():
                        if k in player.ammo:
                            player.ammo[k] += v
                    if powerup_sound: powerup_sound.play()
                    ammoboxes.remove(box)

            for pu in list(powerups):
                if (pu.pos - player.pos).length() < (pu.size + player.size):
                    if pu.ptype == "dash":
                        player.last_dash = -99999
                        for _ in range(10):
                            ang = random.uniform(0, math.tau)
                            particles.append(Particle(player.pos.xy, Vector2(math.cos(ang)*random.uniform(1,4), math.sin(ang)*random.uniform(1,4)), radius=3, life=0.5, color=CYAN))
                    elif pu.ptype == "damage":
                        player.apply_damage_boost(mult=1.6, duration=8000)
                        for _ in range(10):
                            ang = random.uniform(0, math.tau)
                            particles.append(Particle(player.pos.xy, Vector2(math.cos(ang)*random.uniform(1,4), math.sin(ang)*random.uniform(1,4)), radius=3, life=0.5, color=ORANGE))
                    try: powerups.remove(pu)
                    except ValueError: pass

        # particle update
        for p in particles:
            p.update(dt)
        particles = [p for p in particles if p.life > 0.01]

        # Area damage weapon effect: damage enemies inside radius slowly with cooldown
        if player.weapon == "area_damage":
            now = pygame.time.get_ticks()
            if now - player.area_damage_last_used < player.area_damage_cooldown:
                player.area_damage_tick_timer -= clock.get_time()
                if player.area_damage_tick_timer <= 0:
                    player.area_damage_tick_timer = player.area_damage_tick_interval
                    for e in enemies:
                        dist = (e.pos - player.pos).length()
                        if dist <= player.area_damage_radius:
                            e.hp -= player.area_damage_per_tick
                            spawn_blood(particles, e.pos.x, e.pos.y, intensity=4)
                            if e.hp <= 0:
                                if enemy_death_sound: enemy_death_sound.play()
                                player.score += int(10 * player.combo_multiplier) # Apply combo bonus
                                player.kills += 1
                                player.update_combo() # Update combo on kill
                                update_daily_mission(player, enemy_killed_weapon=player.weapon) # Update daily mission
                                if random.random() < 0.25 or isinstance(e, Boss): orbs.append(HealthOrb(e.pos.x, e.pos.y))
                                if random.random() < 0.25 or isinstance(e, Boss): ammoboxes.append(AmmoBox(e.pos.x, e.pos.y))
                                if random.random() < 0.12:
                                    ptype = random.choice(["dash", "damage"])
                                    powerups.append(Powerup(e.pos.x, e.pos.y, ptype))
                                try: enemies.remove(e)
                                except ValueError: pass

        # Update rain effects
        if is_raining:
            update_rain()
            if pygame.time.get_ticks() - rain_start_time > rain_duration:
                stop_rain()
                pygame.time.set_timer(WEATHER_EVENT, random.randint(15000, 30000)) # Schedule next weather event

        # occasionally spawn fallback enemy
        if len(enemies) < 1 and random.random() < 0.02:
            spawn_enemy(enemies, player.level)

        if player.kills >= 200: # Example win condition
            win = True
            game_over = True

        if game_over and not coins_added:
            coins += player.kills * 10
            save_coins(coins)
            coins_added = True
            # Save updated score and kills to database if logged in
            if current_user:
                user_data = load_user_data(current_user)
                user_data["score"] = player.score
                user_data["kills"] = player.kills
                user_data["weapon"] = player.weapon
                user_data["ammo"] = player.ammo
                save_user_data(current_user, user_data)
            # Auto add to leaderboard if qualifies and logged in
            can_submit = qualifies_for_leaderboard(player.score, player.kills)
            if can_submit and current_user:
                add_to_leaderboard(current_user, player.score, player.kills)
                can_submit = False # No need to prompt for name if auto-submitted
            elif can_submit and not current_user: # If not logged in but qualifies, allow name entry
                entering_name = True


        # --- Drawing ---
        screen.fill(BG)
        for gx in range(0, current_width, 60):
            pygame.draw.line(screen, (17, 22, 28), (gx, 0), (gx, current_height))
        for gy in range(0, current_height, 60):
            pygame.draw.line(screen, (17, 22, 28), (0, gy), (current_width, gy))

        for p in particles:
            p.draw(screen)
        for b in bullets:
            b.draw(screen)
        for e in enemies:
            pygame.draw.circle(screen, e.color, (int(e.pos.x), int(e.pos.y)), e.size)
            e.draw_health_bar(screen)
        for orb in orbs:
            orb.draw(screen)
        for box in ammoboxes:
            box.draw(screen)
        for pu in powerups:
            pu.draw(screen)
        for mine in mines: # Draw mines
            mine.draw(screen)

        player.draw(screen, mouse_pos)

        # Draw rain on top of everything else
        draw_rain(screen)

        # HUD
        draw_text(screen, f"HP: {int(player.hp)}", 20, 10, 10)
        draw_text(screen, f"Score: {player.score}", 20, 10, 34)
        draw_text(screen, f"Kills: {player.kills}", 20, 10, 58)
        draw_text(screen, f"Weapon: {player.weapon.replace('_', ' ').title()}", 20, 10, 82) # Formatted weapon name
        ammo_text = "∞" if player.weapon in ("pistol", "sword") else str(int(player.ammo.get(player.weapon, 0)))
        draw_text(screen, f"Ammo: {ammo_text}", 20, 10, 106)
        draw_text(screen, f"Level: {player.level}", 20, 10, 130)
        draw_text(screen, f"Combo: x{player.combo_multiplier:.1f} ({player.combo})", 20, 10, 154, color=YELLOW)


        # dash and damage HUD
        dash_ready = (pygame.time.get_ticks() - player.last_dash) >= player.dash_cooldown
        dash_cd_left = max(0, int((player.dash_cooldown - (pygame.time.get_ticks() - player.last_dash))/1000))
        draw_text(screen, f"Dash: {'Ready' if dash_ready else f'{dash_cd_left}s'}", 16, 10, 178, color=CYAN)
        if player.damage_timer > 0:
            draw_text(screen, f"DMG x{player.damage_mult:.1f} ({int(player.damage_timer/1000)}s)", 16, 10, 198, color=ORANGE)

        # shield skill HUD
        if player.shield_skill_active:
            draw_text(screen, f"Shield Skill: {int(player.shield_skill_timer/1000)}s", 16, 10, 218, color=CYAN)
        else:
            shield_ready = (pygame.time.get_ticks() - player.last_shield_skill) >= player.shield_skill_cooldown
            shield_cd_left = max(0, int((player.shield_skill_cooldown - (pygame.time.get_ticks() - player.last_shield_skill))/1000))
            draw_text(screen, f"Shield Skill: {'Ready' if shield_ready else f'{shield_cd_left}s'}", 16, 10, 218, color=CYAN)

        # area damage weapon cooldown HUD
        if player.weapon == "area_damage":
            now = pygame.time.get_ticks()
            area_ready = (now - player.area_damage_last_used) >= player.area_damage_cooldown
            area_cd_left = max(0, int((player.area_damage_cooldown - (now - player.area_damage_last_used))/1000))
            draw_text(screen, f"Area Damage: {'Ready' if area_ready else f'{area_cd_left}s'}", 16, 10, 238, color=RED)
        
        # Weather HUD
        if is_raining:
            draw_text(screen, "Weather: Rain (Speed -15%)", 16, current_width - 200, 10, color=LIGHT_BLUE) # REVISI: Teks debuff
        else:
            draw_text(screen, "Weather: Clear", 16, current_width - 200, 10, color=WHITE)

        # Daily Mission HUD
        if current_user:
            if "weapon" in daily_mission:
                mission_text = daily_mission["desc"].format(target=daily_mission["target"], weapon=daily_mission["weapon"])
            else:
                mission_text = daily_mission["desc"].format(target=daily_mission["target"])
            progress_text = f"Progress: {daily_mission['progress']}/{daily_mission['target']}"
            reward_text = f"Reward: {daily_mission['reward']} coins"
            status_text = "Completed!" if daily_mission["completed"] else "In Progress"

            draw_text(screen, "Daily Mission:", 16, current_width - 200, current_height - 100, color=WHITE)
            draw_text(screen, mission_text, 14, current_width - 200, current_height - 80, color=GRAY)
            draw_text(screen, progress_text, 14, current_width - 200, current_height - 64, color=GRAY)
            draw_text(screen, reward_text, 14, current_width - 200, current_height - 48, color=YELLOW)
            draw_text(screen, status_text, 14, current_width - 200, current_height - 32, color=GREEN if daily_mission["completed"] else YELLOW)


        draw_text(screen, "Switch: 1..0 (0=10th) or Scroll  •  SHIFT = Dash  •  Q = Shield Skill  •  R = Restart (on Game Over)  •  ESC = Menu", 16, 10, current_height - 28, color=GRAY)

        if game_over:
            if win:
                draw_text(screen, "YOU WIN!", 48, current_width // 2, current_height // 2 - 80, color=GREEN, center=True)
            else:
                draw_text(screen, "GAME OVER", 48, current_width // 2, current_height // 2 - 80, color=RED, center=True)

            draw_text(screen, f"Score: {player.score}", 28, current_width // 2, current_height // 2 - 20, color=WHITE, center=True)
            draw_text(screen, f"Kills: {player.kills}", 22, current_width // 2, current_height // 2 + 18, color=WHITE, center=True)

            # check leaderboard qualification
            can_submit = qualifies_for_leaderboard(player.score, player.kills)
            if can_submit and not entering_name:
                draw_text(screen, "New High Score! Press ENTER to submit name, or R to restart.", 18, current_width // 2, current_height // 2 + 64, color=GRAY, center=True)
            elif can_submit and entering_name:
                draw_text(screen, "Enter name (max 12 chars). Press ENTER to submit:", 18, current_width // 2, current_height // 2 + 96, color=GRAY, center=True)
                draw_text(screen, name_buf + ("|" if (pygame.time.get_ticks()//400)%2==0 else ""), 24, current_width // 2, current_height // 2 + 96, color=WHITE, center=True)
            else:
                draw_text(screen, "Press R to restart • ESC to menu • ENTER to submit score (if eligible)", 18, current_width // 2, current_height // 2 + 64, color=GRAY, center=True)

        pygame.display.flip()

    return "menu"

# ---------------- Main Program ----------------
state = "menu"
while True:
    if state == "menu":
        state = main_menu()
    elif state == "game":
        state = game_loop()
    elif state == "admin_panel": # New state for admin panel
        state = admin_panel_screen()
    elif state == "restart":
        state = "game"
    elif state == "quit":
        break
    else:
        state = "menu"

pygame.quit()