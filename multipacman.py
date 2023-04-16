import pygame
import numpy as np
import tcod
import random
from enum import Enum
import re
import sys

theme = random.randint(0, 255)
match(theme%8):
    case 0:
        AssetPath = "Assets/Pacman/"

    case 1:
        AssetPath = "Assets/Mario/"

    case 2:
        AssetPath = "Assets/Zelda/"
            
    case 3:
        AssetPath = "Assets/Kirby/"
        
    case 4:
        AssetPath = "Assets/Pokemon/"
        
    case 5:
        AssetPath = "Assets/Megaman/"
        
    case 6:
        AssetPath = "Assets/Sonic/"
        
    case 7:
        AssetPath = "Assets/Pacman/"


AssetPath = "Assets/Pokemon/"

with open("highscore.txt", "r") as file_highscore:
    current_highscore = int(file_highscore.read())

class Direction(Enum):
    DOWN = -90
    RIGHT = 0
    UP = 90
    LEFT = 180
    NONE = 360

class ScoreType(Enum):
    COOKIE = 100
    POWERUP = 250
    GHOST = 1000


class GhostBehaviour(Enum):
    CHASE = 1
    RANDOM = 2


def translate_screen_to_maze(in_coords, in_size=32):
    return int(in_coords[0] / in_size), int(in_coords[1] / in_size)


def translate_maze_to_screen(in_coords, in_size=32):
    return in_coords[0] * in_size, in_coords[1] * in_size


class GameObject:
    def __init__(self, in_surface, x, y,
                 in_size: int, in_color=(255, 0, 0),
                 is_circle: bool = False):
        self._size = in_size
        self._renderer: GameRenderer = in_surface
        self._surface = in_surface._screen
        self.y = y
        self.x = x
        self._color = in_color
        self._circle = is_circle
        self._shape = pygame.Rect(self.x, self.y, in_size, in_size)

    def draw(self):
        if self._circle:
            pygame.draw.circle(self._surface,
                               self._color,
                               (self.x, self.y),
                               self._size)
        else:
            rect_object = pygame.Rect(self.x, self.y, self._size, self._size)
            pygame.draw.rect(self._surface,
                             self._color,
                             rect_object,
                             border_radius=1)

    def tick(self):
        pass

    def get_shape(self):
        return pygame.Rect(self.x, self.y, self._size, self._size)

    def set_position(self, in_x, in_y):
        self.x = in_x
        self.y = in_y

    def get_position(self):
        return (self.x, self.y)


class Wall(GameObject):
    def __init__(self, in_surface, x, y, in_size: int, in_color=(0, 0, 255)):
        super().__init__(in_surface, x * in_size, y * in_size, in_size, in_color)
        self.image = pygame.image.load(AssetPath + "wall.png")
    
    def draw(self):
        self.image = pygame.transform.scale(self.image, (32, 32))
        self._surface.blit(self.image, self.get_shape())


class GameRenderer:
    def __init__(self, in_width: int, in_height: int):
        pygame.init()
        self._width = in_width
        self._height = in_height
        self._screen = pygame.display.set_mode((in_width, in_height))
        pygame.display.set_caption('Pacman')
        self._clock = pygame.time.Clock()
        self._done = False
        self._won = False
        self._game_objects = []
        self._walls = []
        self._cookies = []
        self._powerups = []
        self._ghosts = []
        self._hero: Hero = None
        self._lives = 3
        self._score = 0
        self._score_cookie_pickup = 100
        self._score_ghost_eaten = 1000
        self._score_powerup_pickup = 250
        self._powerup_active = False
        self._current_mode = GhostBehaviour.RANDOM
        self._mode_switch_event = pygame.USEREVENT + 1 
        self._powerup_end_event = pygame.USEREVENT + 2
        self._pacman_event = pygame.USEREVENT + 3
        self._modes = [
            (7, 20),
            (7, 20),
            (5, 20),
            (5, 999999)
        ]
        self._current_phase = 0

    def tick(self, in_fps: int):
        black = (0, 0, 0)

        self.handle_mode_switch()
        pygame.time.set_timer(self._pacman_event, 200)
        while not self._done:
            for game_object in self._game_objects:
                game_object.tick()
                game_object.draw()

            self.display_text(f"     [Score: {self._score}]  [Lives: {self._lives}]                                 [Current Highscore: {current_highscore}]")
            
            if self._hero is None or self.get_won(): 
                print("Game over")
                if self._hero is None: print("You lost!")
                if self.get_won(): print("YOU WON!")
                if self._score > current_highscore: 
                    print("Congrats! You've set a new high score!")
                    with open("highscore.txt", "w") as overwrite_highscore:
                        overwrite_highscore.write(str(self._score))
                elif self._score > current_highscore: 
                    print("Wow! You got a high score!")
                pygame.quit()
                sys.exit()

            pygame.display.flip()
            self._clock.tick(in_fps)
            self._screen.fill(black)
            self._handle_events()
            
    def handle_mode_switch(self):
        current_phase_timings = self._modes[self._current_phase]
        print(f"Current phase: {str(self._current_phase)}, current_phase_timings: {str(current_phase_timings)}")
        scatter_timing = current_phase_timings[0]
        chase_timing = current_phase_timings[1]

        if self._current_mode == GhostBehaviour.CHASE:
            self._current_phase += 1
            self.set_current_mode(GhostBehaviour.RANDOM)
        else:
            self.set_current_mode(GhostBehaviour.CHASE)

        used_timing = scatter_timing if self._current_mode == GhostBehaviour.RANDOM else chase_timing
        pygame.time.set_timer(self._mode_switch_event, used_timing * 1000)

    def start_powerup_timeout(self):
        pygame.time.set_timer(self._powerup_end_event, 10000)

    def add_game_object(self, obj: GameObject):
        self._game_objects.append(obj)

    def add_cookie(self, obj: GameObject):
        self._game_objects.append(obj)
        self._cookies.append(obj)

    def add_ghost(self, obj: GameObject):
        self._game_objects.append(obj)
        self._ghosts.append(obj)

    def add_powerup(self, obj: GameObject):
        self._game_objects.append(obj)
        self._powerups.append(obj)

    def activate_powerup(self):
        self._powerup_active = True
        self.set_current_mode(GhostBehaviour.RANDOM)
        self.start_powerup_timeout()

    def set_won(self):
        self._won = True

    def get_won(self):
        return self._won

    def add_score(self, in_score: ScoreType):
        self._score += in_score.value

    def get_hero_position(self):
        return self._hero.get_position() if self._hero != None else (0, 0)

    def set_current_mode(self, in_mode: GhostBehaviour):
        self._current_mode = in_mode

    def get_current_mode(self):
        return self._current_mode

    def end_game(self):
        if self._hero in self._game_objects:
            self._game_objects.remove(self._hero)
        self._hero = None

    def kill_pacman(self):
        self._lives -= 1
        self._hero.set_position(32 * 14, 32 *14)
        self._hero.set_direction(Direction.NONE)
        if self._lives == 0: self.end_game()

    def display_text(self, text, in_position=(0, 0), in_size=30):
        font = pygame.font.SysFont('Arial', in_size)
        text_surface = font.render(text, False, (255, 255, 255))
        self._screen.blit(text_surface, in_position)

    def is_powerup_active(self):
        return self._powerup_active

    def add_wall(self, obj: Wall):
        self.add_game_object(obj)
        self._walls.append(obj)

    def get_walls(self):
        return self._walls

    def get_cookies(self):
        return self._cookies

    def get_ghosts(self):
        return self._ghosts

    def get_powerups(self):
        return self._powerups

    def get_game_objects(self):
        return self._game_objects

    def add_hero(self, in_hero):
        self.add_game_object(in_hero)
        self._hero = in_hero

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._done = True

            if event.type == self._mode_switch_event:
                self.handle_mode_switch()

            if event.type == self._powerup_end_event:
                self._powerup_active = False

            if event.type == self._pacman_event:
                if self._hero is None: break
                self._hero.mouth_open = not self._hero.mouth_open

        pressed = pygame.key.get_pressed()
        if self._hero is None: return
        if pressed[pygame.K_m]:
            AssetPath = "Assets/Mario/"
        if pressed[pygame.K_UP] or pressed[pygame.K_w]:
            self._hero.set_direction(Direction.UP)
        elif pressed[pygame.K_LEFT] or pressed[pygame.K_a]:
            self._hero.set_direction(Direction.LEFT)
        elif pressed[pygame.K_DOWN] or pressed[pygame.K_s]:
            self._hero.set_direction(Direction.DOWN)
        elif pressed[pygame.K_RIGHT] or pressed[pygame.K_d]:
            self._hero.set_direction(Direction.RIGHT)


class MovableObject(GameObject):
    def __init__(self, in_surface, x, y, in_size: int, in_color=(255, 255, 0), is_circle: bool = False):
        super().__init__(in_surface, x, y, in_size, in_color, is_circle)
        self.current_direction = Direction.NONE
        self.direction_buffer = Direction.NONE
        self.last_working_direction = Direction.NONE
        self.location_queue = []
        self.next_target = None
        self.image = pygame.image.load(AssetPath + 'ghost.png')

    def get_next_location(self):
        return None if len(self.location_queue) == 0 else self.location_queue.pop(0)

    def set_direction(self, in_direction):
        self.current_direction = in_direction
        self.direction_buffer = in_direction

    def collides_with_wall(self, in_position):
        collision_rect = pygame.Rect(in_position[0], in_position[1], self._size, self._size)
        collides = False
        walls = self._renderer.get_walls()
        for wall in walls:
            collides = collision_rect.colliderect(wall.get_shape())
            if collides: break
        return collides

    def check_collision_in_direction(self, in_direction: Direction):
        desired_position = (0, 0)
        if in_direction == Direction.NONE: return False, desired_position
        if in_direction == Direction.UP:
            desired_position = (self.x, self.y - 2)
        elif in_direction == Direction.DOWN:
            desired_position = (self.x, self.y + 2)
        elif in_direction == Direction.LEFT:
            desired_position = (self.x - 2, self.y)
        elif in_direction == Direction.RIGHT:
            desired_position = (self.x + 2, self.y)

        return self.collides_with_wall(desired_position), desired_position

    def auto_move(self, in_direction: Direction):
        pass

    def tick(self):
        self.reached_target()
        self.auto_move(self.current_direction)

    def reached_target(self):
        pass
    
    def draw(self):
        self.image = pygame.transform.scale(self.image, (32, 32))
        self._surface.blit(self.image, self.get_shape())


class Hero(MovableObject):
    def __init__(self, in_surface, x, y, in_size: int):
        super().__init__(in_surface, x, y, in_size, (255, 255, 0), False)
        self.last_non_colliding_position = (0, 0)
        self.open = pygame.image.load(AssetPath + "pacman_open.png")
        self.closed = pygame.image.load(AssetPath + "pacman_closed.png")
        self.image = self.open
        self.mouth_open = True


    def tick(self):
        if self.x < 0:
            self.x = self._renderer._width

        if self.x > self._renderer._width:
            self.x = 0
        
        if self.y < 0:
            self.y = self._renderer._height

        if self.y > self._renderer._height:
            self.y = 0

        self.last_non_colliding_position = self.get_position()

        if self.check_collision_in_direction(self.direction_buffer)[0]:
            self.auto_move(self.current_direction)
        else:
            self.auto_move(self.direction_buffer)
            self.current_direction = self.direction_buffer

        if self.collides_with_wall((self.x, self.y)):
            self.set_position(self.last_non_colliding_position[0], self.last_non_colliding_position[1])

        self.handle_cookie_pickup()
        self.handle_ghosts()

    def auto_move(self, in_direction: Direction):
        collision_result = self.check_collision_in_direction(in_direction)

        desired_position_collides = collision_result[0]
        if not desired_position_collides:
            self.last_working_direction = self.current_direction
            desired_position = collision_result[1]
            self.set_position(desired_position[0], desired_position[1])
        else:
            self.current_direction = self.last_working_direction

    def handle_cookie_pickup(self):
        collision_rect = pygame.Rect(self.x, self.y, self._size, self._size)
        cookies = self._renderer.get_cookies()
        powerups = self._renderer.get_powerups()
        game_objects = self._renderer.get_game_objects()
        cookie_to_remove = None
        for cookie in cookies:
            collides = collision_rect.colliderect(cookie.get_shape())
            if collides and cookie in game_objects:
                game_objects.remove(cookie)
                self._renderer.add_score(ScoreType.COOKIE)
                cookie_to_remove = cookie

        if cookie_to_remove is not None:
            cookies.remove(cookie_to_remove)

        if len(self._renderer.get_cookies()) == 0:
            self._renderer.set_won()

        for powerup in powerups:
            collides = collision_rect.colliderect(powerup.get_shape())
            if collides and powerup in game_objects:
                if not self._renderer.is_powerup_active():
                    game_objects.remove(powerup)
                    self._renderer.add_score(ScoreType.POWERUP)
                    self._renderer.activate_powerup()

    def handle_ghosts(self):
        collision_rect = pygame.Rect(self.x, self.y, self._size, self._size)
        ghosts = self._renderer.get_ghosts()
        game_objects = self._renderer.get_game_objects()
        for ghost in ghosts:
            collides = collision_rect.colliderect(ghost.get_shape())
            if collides and ghost in game_objects:
                if self._renderer.is_powerup_active():
                    game_objects.remove(ghost)
                    self._renderer.add_score(ScoreType.GHOST)
                else:
                    if not self._renderer.get_won():
                        self._renderer.kill_pacman()

    def draw(self):
        half_size = self._size / 2
        self.image = self.open if self.mouth_open else self.closed
        self.image = pygame.transform.rotate(self.image, self.current_direction.value)
        super(Hero, self).draw()


class Ghost(MovableObject):
    def __init__(self, in_surface, x, y, in_size: int, in_game_controller, sprite_path=AssetPath+"ghost_fright.png"):
        super().__init__(in_surface, x, y, in_size)
        self.game_controller = in_game_controller
        self.sprite_normal = pygame.image.load(sprite_path)
        self.sprite_fright = pygame.image.load(AssetPath + "ghost_fright.png")

    def reached_target(self):
        if (self.x, self.y) == self.next_target:
            self.next_target = self.get_next_location()
        self.current_direction = self.calculate_direction_to_next_target()

    def set_new_path(self, in_path):
        for item in in_path:
            self.location_queue.append(item)
        self.next_target = self.get_next_location()

    def calculate_direction_to_next_target(self) -> Direction:
        if self.next_target is None:
            if self._renderer.get_current_mode() == GhostBehaviour.CHASE and not self._renderer.is_powerup_active():
                self.request_path_to_player(self)
            else:
                self.game_controller.request_new_random_path(self)
            return Direction.NONE

        diff_x = self.next_target[0] - self.x
        diff_y = self.next_target[1] - self.y
        if diff_x == 0:
            return Direction.DOWN if diff_y > 0 else Direction.UP
        if diff_y == 0:
            return Direction.LEFT if diff_x < 0 else Direction.RIGHT

        if self._renderer.get_current_mode() == GhostBehaviour.CHASE and not self._renderer.is_powerup_active():
            self.request_path_to_player(self)
        else:
            self.game_controller.request_new_random_path(self)
        return Direction.NONE

    def request_path_to_player(self, in_ghost):
        player_position = translate_screen_to_maze(in_ghost._renderer.get_hero_position())
        current_maze_coord = translate_screen_to_maze(in_ghost.get_position())
        path = self.game_controller.p.get_path(current_maze_coord[1], current_maze_coord[0], player_position[1],
                                               player_position[0])

        new_path = [translate_maze_to_screen(item) for item in path]
        in_ghost.set_new_path(new_path)

    def auto_move(self, in_direction: Direction):
        if in_direction == Direction.UP:
            self.set_position(self.x, self.y - 2)
        elif in_direction == Direction.DOWN:
            self.set_position(self.x, self.y + 2)
        elif in_direction == Direction.LEFT:
            self.set_position(self.x - 2, self.y)
        elif in_direction == Direction.RIGHT:
            self.set_position(self.x + 2, self.y)

    def draw(self):
        self.image = self.sprite_fright if self._renderer.is_powerup_active() else self.sprite_normal
        super(Ghost, self).draw()

class Cookie(GameObject):
    def __init__(self, in_surface, x, y):
        super().__init__(in_surface, x, y, 4, (255, 255, 0), True)

class Powerup(GameObject):
    def __init__(self, in_surface, x, y):
        super().__init__(in_surface, x, y, 8, (0, 255, 0), True)

class Pathfinder:
    def __init__(self, in_arr):
        cost = np.array(in_arr, dtype=np.bool_).tolist()
        self.pf = tcod.path.AStar(cost=cost, diagonal=0)

    def get_path(self, from_x, from_y, to_x, to_y) -> object:
        res = self.pf.get_path(from_x, from_y, to_x, to_y)
        return [(sub[1], sub[0]) for sub in res]


class PacmanGame:
    def __init__(self):
        self.ascii_maze1 = [
            "XXXXXXXXXXXXXX XXXXXXXXXXXXXX",
            "X            X X            X",
            "X XXXX XXXXX X X XXXXX XXXX X",
            "X XXXX XXXXX X X XXXXX XXXX X",
            "X XXXX XXXXX X X XXXXX XXXX X",
            " G            O            G ",
            "X XXXX XX XXXXXXXXX XX XXXX X",
            "X XXXX XX XXXXXXXXX XX XXXX X",
            "X      XX    XXX    XX      X",
            "XXX XXXXXXXX XXX XXXXXXXX XXX",
            "XXX XXXXXXXX XXX XXXXXXXX XXX",
            "X      XX           XX      X",
            "X XXXX XX XXXXXXXXX XX XXXX X",
            "X XXXX XX XXXXXXXXX XX XXXX X",
            "X O                       O X",
            "XXX XX XX XXXX XXXX XX XX XXX",
            "XXX XX XX XXXX XXXX XX XX XXX",
            "XXX    XX     p     XX    XXX",
            "XXXXXX XX XXXXXXXXX XX XXXXXX",
            "XXXXXX XX XXXXXXXXX XX XXXXXX",
            "X                           X",
            "X XXXX XXXXX XXX XXXXX XXXX X",
            "X XXXX XXXXX XXX XXXXX XXXX X",
            "X   XX        O        XX   X",
            "XXX XX XX XXXX XXXX XX XX XXX",
            "XXX XX XX XXXX XXXX XX XX XXX",
            "       XX    X X    XX       ",
            "XXX XXXXXXXX X X XXXXXXXX XXX",
            "XXX XXXXXXXX X X XXXXXXXX XXX",
            "XXX G        X X       G  XXX",
            "XXXXXXXXXXXXXX XXXXXXXXXXXXXX",
        ]

        self.numpy_maze = []
        self.cookie_spaces = []
        self.powerup_spaces = []
        self.reachable_spaces = []
        self.ghost_spawns = []
        self.ghost_colors = [
            AssetPath + "ghost.png",
            AssetPath + "ghost_pink.png",
            AssetPath + "ghost_orange.png",
            AssetPath + "ghost_blue.png"
        ]
        self.size = (0, 0)
        self.convert_maze_to_numpy()
        self.p = Pathfinder(self.numpy_maze)

    def request_new_random_path(self, in_ghost: Ghost):
        random_space = random.choice(self.reachable_spaces)
        current_maze_coord = translate_screen_to_maze(in_ghost.get_position())

        path = self.p.get_path(current_maze_coord[1], current_maze_coord[0], random_space[1],
                               random_space[0])
        test_path = [translate_maze_to_screen(item) for item in path]
        in_ghost.set_new_path(test_path)

    def convert_maze_to_numpy(self):
        for x, row in enumerate(self.ascii_maze1):
            self.size = (len(row), x + 1)
            binary_row = []
            for y, column in enumerate(row):
                if column == "G":
                    self.ghost_spawns.append((y, x))

                if column == "X":
                    binary_row.append(0)
                else:
                    binary_row.append(1)
                    self.cookie_spaces.append((y, x))
                    self.reachable_spaces.append((y, x))
                    if column == "O":
                        self.powerup_spaces.append((y, x))

            self.numpy_maze.append(binary_row)


if __name__ == "__main__":
    unified_size = 32
    pacman_game = PacmanGame()
    size = pacman_game.size
    game_renderer = GameRenderer(size[0] * unified_size, size[1] * unified_size)

    for y, row in enumerate(pacman_game.numpy_maze):
        for x, column in enumerate(row):
            if column == 0:
                game_renderer.add_wall(Wall(game_renderer, x, y, unified_size))

    for cookie_space in pacman_game.cookie_spaces:
        translated = translate_maze_to_screen(cookie_space)
        cookie = Cookie(game_renderer, translated[0] + unified_size / 2, translated[1] + unified_size / 2)
        game_renderer.add_cookie(cookie)

    for powerup_space in pacman_game.powerup_spaces:
        translated = translate_maze_to_screen(powerup_space)
        powerup = Powerup(game_renderer, translated[0] + unified_size / 2, translated[1] + unified_size / 2)
        game_renderer.add_powerup(powerup)

    for i, ghost_spawn in enumerate(pacman_game.ghost_spawns):
        translated = translate_maze_to_screen(ghost_spawn)
        ghost = Ghost(game_renderer, translated[0], translated[1], unified_size, pacman_game,
                      pacman_game.ghost_colors[i % 4])
        game_renderer.add_ghost(ghost)

    pacman = Hero(game_renderer, unified_size, unified_size, unified_size)
    game_renderer.add_hero(pacman)
    game_renderer.set_current_mode(GhostBehaviour.CHASE)
    game_renderer.tick(120)
    