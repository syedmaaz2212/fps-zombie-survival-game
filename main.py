from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random, os, math

app = Ursina()

# intro_message = Text(
#     text="Hi, I'm Syed Mohammad Maaz\nCreated this FPS Game\nMission: Kill 100 Zombies",
#     scale=2,
#     origin=(0,0),
#     color=color.cyan,
#     background=True
# )
# def hide_intro():
#     intro_message.enabled = False

# invoke(hide_intro, delay=8) 


end_message = Text('', scale=3, origin=(0,0), color=color.red, enabled=False)
damage_flash = Entity(parent=camera.ui, model='quad', color=color.rgba(255,0,0,100), scale=(2,2), enabled=False)

# === ENVIRONMENT ===
Entity(model='plane', texture='white_cube', scale=(300,1,300), collider='box', texture_scale=(300,300))
Sky()

# === WALLS ===
for i in range(-150, 151, 3):
    Entity(model='cube', color=color.gray, scale=(5, 5, 5), position=(i, 2.5, -150), collider='box')
    Entity(model='cube', color=color.gray, scale=(5, 5, 5), position=(i, 2.5, 150), collider='box')
    Entity(model='cube', color=color.gray, scale=(5, 5, 5), position=(-150, 2.5, i), collider='box')
    Entity(model='cube', color=color.gray, scale=(5, 5, 5), position=(150, 2.5, i), collider='box')

# === BUILDINGS ===
buildings = []
building_positions = [(-50, 0, -50), (60, 0, -60), (-40, 0, 70), (70, 0, 70)]
for pos in building_positions:
    b = Entity(
        model='assets/buildings/Buildings.glb',
        texture='assets/buildings/Textures/brick_modern.jpg',
        scale=.8,
        position=pos,
        collider='mesh'
    )
    buildings.append(b)


# === PLAYER ===
player = FirstPersonController()
player.gravity = 0.5
player.health = 100
player.y = 2

# === HUD ===
gun = Entity(parent=camera.ui, model='quad', texture='assets/first_person_view/M4A1.png', scale=(1.5, 0.7), position=(0.6, -0.6))
muzzle_flash = Entity(parent=camera.ui, model='quad', texture='assets/muzzle_flash.png', scale=0.5, position=(0.20, -0.42), enabled=False)

kill_count = 0
kill_text = Text(text=f"Kills: {kill_count}", position=(-0.85, 0.45), scale=2, color=color.azure)
pos_text = Text(text='', position=(-0.85, 0.4), scale=1.5, color=color.orange)
health_text = Text(text=f"Health: {player.health}", position=(-0.85, 0.35), scale=1.5, color=color.red)

# === PAUSE MENU ===
paused = False
pause_bg = Entity(parent=camera.ui, model='quad', color=color.rgba(0,0,0,150), scale=(1.5, 1), enabled=False)
pause_text = Text("PAUSED", origin=(0, 0), scale=3, color=color.red, enabled=False)
resume_btn = Button(text='Resume', color=color.azure, scale=(0.3, 0.1), y=-0.2, enabled=False)

def resume_game():
    global paused
    paused = False
    mouse.locked = True
    player.enabled = True
    pause_bg.enabled = False
    pause_text.enabled = False
    resume_btn.enabled = False
resume_btn.on_click = resume_game

# === ENEMY CLASS ===
class Enemy(Entity):
    def __init__(self, position):
        super().__init__(
            model='assets/Old Man Police Zombie.obj',
            texture='assets/Old_Man_Police_Zombie_packed0_diffuse.png',
            position=position,
            scale=0.015,
            collider='box'
        )
        self.health = 1
        self.alive = True
        self.health_bar = Entity(model='quad', color=color.red, scale=(0.6, 0.05), parent=self, y=2.2, z=-0.01)
        self.attack_cooldown = 0

    def get_hit(self, damage=1):
        if not self.alive: return
        self.health -= damage
        self.health_bar.scale_x = max(0.01, self.health / 3 * 0.6)
        self.color = color.red
        invoke(setattr, self, 'color', color.white, delay=0.15)
        if self.health <= 0:
            self.die()

    def die(self):
        global kill_count
        self.alive = False
        kill_count += 1
        kill_text.text = f"Kills: {kill_count}"
        self.rotation_x = 90
        self.collider = None
        self.health_bar.enabled = False

         # Win condition
        if kill_count == 100:
            player.enabled = False
            mouse.locked = False
            end_message.text = "YOU WIN!"
            end_message.color = color.green
            end_message.enabled = True
            # Play win music
            if os.path.exists('assets/batman.mp3'):
                Audio('assets/batman.mp3', loop=False, autoplay=True)

    def move_ai(self):
        if not self.alive: return

        direction = (player.position - self.position).normalized()
        next_pos = self.position + direction * time.dt * 2.5

        # Check collision with buildings
        for b in buildings:
            if distance(b.position, next_pos) < 3:
                return

        # Move toward player
        self.look_at(player.position)
        self.position = next_pos
        self.y += math.sin(time.time() * 10) * 0.01
        self.rotation_y += math.sin(time.time() * 10) * 0.5

        # Attack logic
        if distance(player.position, self.position) < 2 and self.attack_cooldown <= 0:
            player.health -= 10
            damage_flash.enabled = True
            invoke(setattr, damage_flash, 'enabled', False, delay=0.2)
            health_text.text = f"Health: {player.health}"
            self.attack_cooldown = 1.5

            if player.health <= 0:
                player.enabled = False
                mouse.locked = False
                end_message.text = "YOU DIED"
                end_message.color = color.red
                end_message.enabled = True
        else:
            self.attack_cooldown -= time.dt



# === SPAWN ENEMIES ===
enemies = []
for _ in range(100):
    while True:
        x = random.randint(-140, 140)
        z = random.randint(-140, 140)
        if abs(x - player.x) > 10 and abs(z - player.z) > 10:  # Avoid spawning on player
            break
    enemies.append(Enemy(position=Vec3(x, 0, z)))

# === SHOOTING ===
shooting = False
cooldown = 0.15
time_since_last_shot = cooldown

def shoot():
    global time_since_last_shot
    if paused or time_since_last_shot < cooldown: return
    time_since_last_shot = 0

    muzzle_flash.enabled = True
    invoke(setattr, muzzle_flash, 'enabled', False, delay=0.05)

    if os.path.exists('assets/m4.mp3'):
        Audio('assets/m4.mp3', loop=False, autoplay=True)

    bullet = Entity(
        model='sphere',
        color=color.white,
        scale=0.1,
        position=camera.world_position + camera.forward * 1.5,
        collider='box'
    )
    bullet.direction = camera.forward
    bullet.speed = 100

    def update_bullet():
        bullet.position += bullet.direction * bullet.speed * time.dt
        if bullet.y < -10:
            destroy(bullet)
            return
        for enemy in enemies:
            if enemy.alive and bullet.intersects(enemy).hit:
                enemy.get_hit(damage=1)
                destroy(bullet)
                return

    bullet.update = update_bullet

# === PAUSE TOGGLE ===
def toggle_pause():
    global paused
    paused = not paused
    mouse.locked = not paused
    player.enabled = not paused
    pause_bg.enabled = paused
    pause_text.enabled = paused
    resume_btn.enabled = paused

# === INPUT ===
def input(key):
    global shooting
    if key == 'escape': toggle_pause()
    elif key == 'left mouse down': shooting = True
    elif key == 'left mouse up': shooting = False

# === MAIN UPDATE ===
def update():
    global time_since_last_shot
    if paused: return
    time_since_last_shot += time.dt
    if shooting: shoot()
    for enemy in enemies:
        enemy.move_ai()
    pos_text.text = f"Pos: {round(player.x,1)}, {round(player.y,1)}, {round(player.z,1)}"
    health_text.text = f"Health: {player.health}%"



app.run()
