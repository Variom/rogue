import truc
import pygame
import sys
import random
import time
import os
import math
import collections


def loadscale(image, width, height):
    good_path = os.path.join("Images", image)
    img = pygame.image.load(good_path)
    return pygame.transform.scale(img, (width, height))


class Coord:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __repr__(self):
        return '<' + str(self.x) + ',' + str(self.y) + '>'

    def __add__(self, other):
        return Coord(self.x + other.x, self.y + other.y)

    def __hash__(self):
        return hash((self.x, self.y))


class Room:
    def __init__(self, c1, c2):
        self.c1 = c1
        self.c2 = c2

    def __repr__(self):
        return "[" + str(self.c1) + ", " + str(self.c2) + "]"

    def __contains__(self, other):
        if isinstance(other, Coord):
            return other.x >= self.c1.x and other.x <= self.c2.x and other.y >= self.c1.y and other.y <= self.c2.y

    def center(self):
        middle_x = (self.c1.x + self.c2.x) // 2
        middle_y = (self.c1.y + self.c2.y) // 2
        return Coord(middle_x, middle_y)

    def intersect(self, other):
        c3 = Coord(self.c2.x, self.c1.y)
        c4 = Coord(self.c1.x, self.c2.y)
        if self.c1 in other or self.c2 in other or c3 in other or c4 in other or other.c1 in self:
            return True
        return False


class Map:
    ground = '.'
    empty = ' '
    timer = time.time()

    def __init__(self, nb_rooms_possible, size_possible, nb_equipment_possible, nb_creature_possible):

        global dpi, offset

        self.is_playing = False

        # Map generation
        self._size_possible = size_possible
        self._size = random.choice(self._size_possible)
        self._mat = []
        self._elem = {}
        self._rooms = []
        self._roomsToReach = []
        self.nb_rooms_possible = nb_rooms_possible
        self.nb_rooms = random.choice(self.nb_rooms_possible)
        for i in range(self._size):
            self._mat.append([Map.empty] * self._size)
        self.generateRooms(self.nb_rooms)
        self.reachAllRooms()
        self.border()

        dpi = height/self._size
        offset = (width/2) - (self._size*dpi)/2

        # Group
        self.player_group = pygame.sprite.GroupSingle()
        self.all_creatures = pygame.sprite.Group()
        self.all_equipments = pygame.sprite.Group()
        self.stairs_group = pygame.sprite.GroupSingle()
        self.ground_group = pygame.sprite.Group()
        self.wall_group = pygame.sprite.Group()
        self.ground_prox_group = pygame.sprite.Group()
        self.wall_prox_group = pygame.sprite.Group()
        self.interface_group = pygame.sprite.Group()
        self.health_bar_group = pygame.sprite.Group()

        # Player
        self.player = Player((offset + dpi * self._rooms[0].center(
        ).x, dpi * self._rooms[0].center().y), 40/self._size, 1000, 1000, 0.2, 0, 10, 10, 10, False)
        self.player_group.add(self.player)
        self.sound = Sound()

        # Map display
        self.draw()

        # Creature
        self.nb_creature_possible = nb_creature
        self.nb_creature = random.choice(self.nb_creature_possible)
        for i in range(self.nb_creature):
            self.spawn_random_creature(self.random_coord_creature())

        # Equipment
        self.nb_equipment_possible = nb_equipment
        self.nb_equipment = random.choice(self.nb_equipment_possible)
        for f in range(self.nb_equipment):
            self.spawn_random_equipment(self.random_coord_equipment())

        # Health bar
        self.health_bar()

        # Interface
        self.new_interface()

    def new_stairs(self):
        self.stairs_group.empty()
        stairs = Stairs(self.random_coord_creature())
        self.stairs_group.add(stairs)
        self.stairs_group.draw(screen)

    def check_down(self, k, i):
        if i+1 < self._size:
            if self.get(Coord(k, i+1)) == self.ground:
                return False
        return True

    def border(self):
        for i in range(len(self._mat)):
            for k in range(len(self._mat[i])):
                if i == 0 or i == len(self._mat)-1:
                    self.put(Coord(k, i), self.empty)
                if k == 0 or k == len(self._mat[i])-1:
                    self.put(Coord(k, i), self.empty)

    def addRoom(self, room):
        self._roomsToReach.append(room)
        for y in range(room.c1.y, room.c2.y + 1):
            for x in range(room.c1.x, room.c2.x + 1):
                self._mat[y][x] = Map.ground

    def findRoom(self, coord):
        for r in self._roomsToReach:
            if coord in r:
                return r
        return None

    def intersectNone(self, room):
        for r in self._roomsToReach:
            if room.intersect(r):
                return False
        return True

    def put(self, c, o):
        self._mat[c.y][c.x] = o
        self._elem[o] = c

    def get(self, c):
        return self._mat[c.y][c.x]

    def dig(self, coord):
        self.put(coord, self.ground)
        r = self.findRoom(coord)
        if r:
            self._roomsToReach.remove(r)
            self._rooms.append(r)

    def corridor(self, start, end):
        for i in range(start.y, end.y - 1 if start.y > end.y else end.y + 1, -1 if start.y > end.y else 1):
            self.dig(Coord(start.x, i))
        for i in range(start.x, end.x - 1 if start.x > end.x else end.x + 1, -1 if start.x > end.x else 1):
            self.dig(Coord(i, end.y))

    def reach(self):
        roomA = random.choice(self._rooms)
        roomB = random.choice(self._roomsToReach)
        self.corridor(roomA.center(), roomB.center())

    def reachAllRooms(self):
        self._rooms.append(self._roomsToReach.pop(0))
        while len(self._roomsToReach) > 0:
            self.reach()

    def randRoom(self):
        c1 = Coord(random.randint(0, len(self) - 3),
                   random.randint(0, len(self) - 3))
        c2 = Coord(min(c1.x + random.randint(3, 8), len(self) - 1),
                   min(c1.y + random.randint(3, 8), len(self) - 1))
        return Room(c1, c2)

    def generateRooms(self, n):
        # Si sur 100 essais, l'ordinateur n'arrive pas à placer une salle, il arrête d'essayer
        for i in range(n):
            validate = 0
            while validate < 100:
                r = self.randRoom()
                validate += 1
                if self.intersectNone(r):
                    self.addRoom(r)
                    validate = 100

    def __len__(self):
        return len(self._mat)

    def __contains__(self, item):
        if isinstance(item, Coord):
            return 0 <= item.x < len(self) and 0 <= item.y < len(self)
        return item in self._elem

    def __repr__(self):
        s = ""
        for i in self._mat:
            for j in i:
                s += str(j)
            s += '\n'
        return s

    def checkCoord(self, c):
        if not isinstance(c, Coord):
            raise TypeError('Not a Coord')
        if not c in self:
            raise IndexError('Out of map coord')

    def rm(self, c):
        self.checkCoord(c)
        del self._elem[self._mat[c.y][c.x]]
        self._mat[c.y][c.x] = Map.ground

    def draw(self):
        for i in range(len(self._mat)):
            for k in range(len(self._mat[i])):
                if self.get(Coord(k, i)) == self.ground:
                    ground = Ground((offset + dpi * k, dpi * i))
                    self.ground_group.add(ground)
                if self.get(Coord(k, i)) == self.empty:
                    wall = Wall((offset + dpi * k, dpi * i),
                                self.check_down(k, i))
                    self.wall_group.add(wall)
        self.wall_group.draw(screen)
        self.ground_group.draw(screen)
        self.new_stairs()

    def random_coord_creature(self):
        cellule_good = []
        for cellule in filter(lambda case: (math.sqrt(math.pow((self.player.rect.x - case.rect.x), 2) + math.pow((self.player.rect.y - case.rect.y), 2))/dpi) > 4, self.ground_group):
            cellule_good.append(cellule)
        if len(cellule_good) > 0:
            ground = random.choice(cellule_good)
            cellule_good.remove(ground)
        else:
            ground = random.choice(list(self.ground_group))

        for group in self.all_creatures, self.player_group:
            for sprite in group:
                while ground.rect == sprite.rect:
                    if len(cellule_good) > 0:
                        ground = random.choice(cellule_good)
                        cellule_good.remove(ground)
                    else:
                        ground = random.choice(list(self.ground_group))

        pos = (ground.rect.x, ground.rect.y)
        return pos

    def random_coord_equipment(self):
        ground = random.choice(list(self.ground_group))
        for group in self.all_equipments, self.player_group, self.all_creatures:
            for sprite in group:
                while ground.rect == sprite.rect:
                    ground = random.choice(list(self.ground_group))
            pos = (ground.rect.x, ground.rect.y)
            return pos

    def spawn_random_creature(self, pos):
        # [[List of textures], size, hp, hpmax, strenght, xp_gived]
        monsters = [[["dragon_front.png", "dragon_back.png", "dragon_right.png", "dragon_left.png"], "distance", dpi, 20, 20, 5, 5, 1], [["dark_front.png", "dark_back.png", "dark_right.png", "dark_left.png"],
                                                                                                                                         "cac", dpi, 15, 15, 3, 3, 2], [["piege.png", "piege.png", "piege.png", "piege.png"], "piege", dpi, 0.1, 0.1, 5, 0, 0]]  # ["dark.png",dpi , 20, 20, 0.2, 2]] # Image, Taille, Vie, Force
        spec = random.choice(monsters)
        creature = Creature(
            pos, spec[0], spec[1], spec[2], spec[3], spec[4], spec[5], spec[6], spec[7])
        self.all_creatures.add(creature)
        spec = []

    def spawn_random_equipment(self, pos):
        equipment = [["sword", "sword.png", "sword.png", dpi, 10, 3, 0], ["potion", "potion_vie", "potion_vie.png", dpi, 0, 0, 20], ["potion", "potion_magie", "potion_magie.png", dpi, 0, 0, 5], [
            "shuriken", "shuriken.png", "shuriken.png", dpi, 1, 15, 0], ["arrow", "arc.png", "arc.png", dpi, 3, 5, 0], ["armour", "armure.png", "armor.png", dpi, 15, 0, 10], ["amulet", "amulet_bronze.png", "amulet_bronze.png", dpi, 0, 0, 5]]
        spec = random.choice(equipment)
        equipment = Equipment(
            pos, spec[0], spec[1], spec[2], spec[3], spec[4], spec[5], spec[6])
        self.all_equipments.add(equipment)
        spec = []

    def new_stage(self):
        global dpi, offset

        # Delete all the groups except the player.
        self.ground_group.empty()
        self.wall_group.empty()
        self.wall_prox_group.empty()
        self.ground_prox_group.empty()
        self.all_creatures.empty()
        self.all_equipments.empty()
        self.player.all_projectiles.empty()
        self.health_bar_group.empty()

        # New maps's specifications.
        self._size = random.choice(self._size_possible)
        self.nb_rooms = random.choice(self.nb_rooms_possible)
        dpi = height/self._size
        offset = (width/2) - (self._size*dpi)/2

        # Create the new map.
        self._mat = []
        self._elem = {}
        self._rooms = []
        self._roomsToReach = []
        for i in range(self._size):
            self._mat.append([Map.empty] * self._size)
        self.generateRooms(self.nb_rooms)
        self.reachAllRooms()
        self.border()
        self.draw()

        # Elements on the new map.
        self.player.resize()
        self.player.rect.x, self.player.rect.y = offset + dpi * \
            self._rooms[0].center().x, dpi * self._rooms[0].center().y
        self.nb_creature = random.choice(self.nb_creature_possible)
        self.nb_equipment = random.choice(self.nb_equipment_possible)
        for i in range(self.nb_creature):
            self.spawn_random_creature(self.random_coord_creature())
        for f in range(self.nb_equipment):
            self.spawn_random_equipment(self.random_coord_equipment())
        self.health_bar()
        self.player.speed = 40/M._size

    def go_down(self):
        for sprite in self.stairs_group:
            if sprite.rect.colliderect(self.player.rect):
                self.new_stage()
                M.sound.play("escalier")

    def new_interface(self):
        self.left_interface = Interface(image="left_interface.png")
        self.right_interface = Interface(
            (offset + self._size * dpi, 0), image="right_interface.png")
        self.left_interface.add(self.interface_group)
        self.right_interface.add(self.interface_group)

    def interface_update(self):
        self.interface_group.draw(screen)
        self.left_interface.update()
        self.right_interface.update()

    def health_bar(self):
        for i in [0, 1]:
            self.health_bar_group.add(self.player.health_bar()[i])
        for sprite in self.all_creatures:
            if sprite.type != "piege":
                for i in [0, 1]:
                    self.health_bar_group.add(sprite.health_bar()[i])

    def update(self):
        global dpi
        Map.timer = time.time()
        dpi = height/M._size
        self.player.update()
        self.all_equipments.update()
        self.all_creatures.update()
        self.health_bar_group.update()
        for projectile in M.player.all_projectiles:
            projectile.move()
            projectile.update()
        self.ground_prox_group.draw(screen)
        self.wall_prox_group.draw(screen)
        self.stairs_group.draw(screen)
        self.all_equipments.draw(screen)
        self.all_creatures.draw(screen)
        self.player_group.draw(screen)
        self.player.all_projectiles.draw(screen)
        self.health_bar_group.draw(screen)
        self.interface_update()

    def game_over(self):
        self.is_playing = False

    def start(self):
        self.is_playing = True
        self.player = Player((offset + dpi * self._rooms[0].center(
        ).x, dpi * self._rooms[0].center().y), 40/self._size, 50, 50, 3, 0, 10, 10, 10, False)
        self.player_group.add(self.player)
        self.new_stage()


class Stairs(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = loadscale("stairs.png", dpi, dpi)
        self.rect = self.image.get_rect(topleft=pos)


class Ground(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = loadscale("smooth.png", dpi, dpi)
        self.rect = self.image.get_rect(topleft=pos)


class Wall(pygame.sprite.Sprite):
    def __init__(self, pos, filled=True):
        super().__init__()
        if filled == True:
            self.image = loadscale("wall_filled.png", dpi, dpi)
        else:
            self.image = loadscale("wall_down.png", dpi, dpi)
        self.rect = self.image.get_rect(
            center=(pos[0] + dpi/2, pos[1] + dpi/2))


class Equipment(pygame.sprite.Sprite):
    potion_cooldown = 10

    def __init__(self, pos, type, type_equipment, image, size, durability, strenght, health):
        super().__init__()
        self.pos = pos
        self.type = type
        self.type_equipment = type_equipment
        self.durability = durability
        self.strenght = strenght  # Strenght provided
        self.health = health  # Life provided
        self.png = image
        self.image = loadscale(image, size, size)
        self.rect = self.image.get_rect(topleft=pos)


class Creature(pygame.sprite.Sprite):
    other_group = pygame.sprite.Group()

    def __init__(self, pos, images, type, size, hp, hpmax, strenght, xp_gived, speed=1):
        super().__init__()

        # Texture setup
        self.front = loadscale(images[0], size, size)
        self.back = loadscale(images[1], size, size)
        self.right = loadscale(images[2], size, size)
        self.left = loadscale(images[3], size, size)

        # Global setup
        self.type = type
        self.image = self.front
        self.pos = pygame.math.Vector2((pos[0] + dpi/2, pos[1] + dpi/2))
        self.rect = self.image.get_rect(center=self.pos)

        # Movement
        self.speed = speed
        self.movement = 0
        self.direction = pygame.math.Vector2(0, 1)

        # Path
        self.path = []
        self.collision_rects = []

        # Specification
        self.hp = hp
        self.hpmax = hpmax
        self.strenght = strenght
        self.xp_gived = xp_gived
        self.attack_cooldown = 1
        self.all_projectiles = pygame.sprite.Group()
        self.projectile_cooldown = 0

    def damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            M.player.xp += self.xp_gived
            if M.player.xp >= M.player.xpmax:
                M.player.xp -= M.player.xpmax
                M.player.xpmax += round(M.player.xpmax*0.2)
                M.player.pa_magie_max += 2
                M.player.pa_magie = M.player.pa_magie_max
                M.player.strenght += 0.2
                M.player.hpmax += 10
                M.player.hp = M.player.hpmax
            M.all_creatures.remove(self)

    def health_bar(self):
        back_bar = Health_Bar(self.rect, self, False)
        health_bar = Health_Bar(self.rect, self, True)
        return [back_bar, health_bar]

    def get_coord(self):
        center = self.rect.center
        return Coord(math.floor((center[0] - offset)/dpi), math.floor(center[1]/dpi))

    def path_to_player(self):
        start = self.get_coord()
        end = M.player.get_coord()
        to_visit = [start]
        visited = [start]
        parents = collections.defaultdict(lambda: None)
        while to_visit:
            current = to_visit.pop(0)
            if current == end:
                path = []
                while current is not None:
                    path.insert(0, current)
                    current = parents[current]
                del path[0]
                return path
            possibles = [Coord(1, 0), Coord(0, 1), Coord(-1, 0), Coord(0, -1)]
            for possible in possibles:
                neighbour = current + possible
                if 0 <= neighbour.x < M._size and 0 <= neighbour.y < M._size and M.get(neighbour) != Map.empty and neighbour not in visited:
                    visited.append(neighbour)
                    parents[neighbour] = current
                    to_visit.append(neighbour)

    def distance_to_player(self):
        return math.sqrt(math.pow((M.player.rect.x - self.rect.x), 2) + math.pow((M.player.rect.y - self.rect.y), 2))/dpi

    def create_collision_rects(self):
        if self.path:
            self.collision_rects = []
            for point in self.path:
                x = ((point.x + 0.5) * dpi) + offset
                y = ((point.y + 0.5) * dpi)
                rect = pygame.Rect(x, y, dpi/10, dpi/10)
                self.collision_rects.append(rect)

    def direction_to_creature(self, creature):
        start = pygame.math.Vector2(self.pos)
        end = pygame.math.Vector2(creature.pos)
        vector = end - start
        if vector != pygame.math.Vector2(0, 0):
            self.direction = (end - start).normalize()

    def direction_to_wall(self, wall):
        start = pygame.math.Vector2(self.pos)
        end = pygame.math.Vector2(wall.rect.center)
        vector = end - start
        if vector != pygame.math.Vector2(0, 0):
            self.direction = (end - start).normalize()

    def path_direction(self):
        if self.collision_rects:
            start = pygame.math.Vector2(self.pos)
            end = pygame.math.Vector2(self.collision_rects[0].center)
            self.direction = (end - start).normalize()
        else:
            self.direction = pygame.math.Vector2(0, 0)
            self.path = []
        self.path = self.path_to_player()

    def set_path(self):
        self.create_collision_rects()
        self.path_direction()

    def check_collide(self):
        if self.path:
            for rect in self.collision_rects:
                if rect.collidepoint(self.pos):
                    self.rect.center = rect.center
                    del self.path[0]
                    self.path_direction()

    def texture_update(self):
        angle = self.direction.angle_to(pygame.math.Vector2(1, 0))
        if -45 <= angle < 45:
            self.image = self.right
        elif 45 <= angle < 135:
            self.image = self.back
        elif -45 > angle >= -135:
            self.image = self.front
        else:
            self.image = self.left

    def launch_projectile(self):
        if self.type == "distance":
            shot = 0
            if self.distance_to_player() < 5:
                if M.player.projectile_cooldown < Map.timer:
                    if M.player.rect.x == self.rect.x:
                        if abs(M.player.rect.y - self.rect.y) >= 3*dpi:
                            if M.player.rect.y < self.rect.y:
                                centre_creature_x = M.player.rect.center[0]
                                centre_creature_y = M.player.rect.center[1]
                                hauteur = self.rect.center[1] - \
                                    M.player.rect.center[1]
                                weight = dpi/2
                            elif M.player.rect.y > self.rect.y:
                                centre_creature_x = self.rect.center[0]
                                centre_creature_y = self.rect.center[1]
                                hauteur = M.player.rect.center[1] - \
                                    self.rect.center[1]
                                weight = dpi/2
                            for mur in M.wall_group:
                                if pygame.Rect(mur).colliderect((centre_creature_x,  centre_creature_y), (weight, hauteur)):
                                    shot = 1
                            M.all_creatures.remove(self)
                            for monstre in M.all_creatures:
                                if monstre.type != "piege":
                                    if pygame.Rect(monstre).colliderect((centre_creature_x,  centre_creature_y), (weight, hauteur)):
                                        shot = 1
                            M.all_creatures.add(self)
                            if shot == 0:
                                M.player.launch_projectile(
                                    self, "fireball", 10, False)
                                M.player.projectile_cooldown = Map.timer + 2

                    if M.player.rect.y == self.rect.y:
                        if abs(M.player.rect.x - self.rect.x) >= 3*dpi:
                            if M.player.rect.x < self.rect.x:
                                centre_creature_x = M.player.rect.center[0]
                                centre_creature_y = M.player.rect.center[1]
                                hauteur = dpi/2
                                weight = self.rect.center[0] - \
                                    M.player.rect.center[0]
                            elif M.player.rect.x > self.rect.x:
                                centre_creature_x = self.rect.center[0]
                                centre_creature_y = self.rect.center[1]
                                hauteur = dpi/2
                                weight = M.player.rect.center[0] - \
                                    self.rect.center[0]
                            for mur in M.wall_group:
                                if pygame.Rect(mur).colliderect((centre_creature_x,  centre_creature_y), (weight, hauteur)):
                                    shot = 1
                            M.all_creatures.remove(self)
                            for monstre in M.all_creatures:
                                if monstre.type != "piege":
                                    if pygame.Rect(monstre).colliderect((centre_creature_x,  centre_creature_y), (weight, hauteur)):
                                        shot = 1
                            M.all_creatures.add(self)

                            if shot == 0:
                                M.player.launch_projectile(
                                    self, "fireball", 10, False)
                                M.player.projectile_cooldown = Map.timer + 2

    def update(self):
        # Surrounding textures
        for sprite in M.wall_group:
            if self.rect.x - dpi <= sprite.rect.x <= self.rect.x + dpi and self.rect.y - dpi <= sprite.rect.y <= self.rect.y + dpi:
                M.wall_prox_group.add(sprite)
        for sprite in M.ground_group:
            if self.rect.x - dpi <= sprite.rect.x <= self.rect.x + dpi and self.rect.y - dpi <= sprite.rect.y <= self.rect.y + dpi:
                M.ground_prox_group.add(sprite)

        # Movement when player is nearby
        if self.type != "piege":
            if self.distance_to_player() < 5:
                self.set_path()
                Creature.other_group.empty()
                for creature in M.all_creatures:
                    if creature != self:
                        Creature.other_group.add(creature)
                if any(pygame.sprite.spritecollide(self, M.player_group, False)):
                    self.pos -= self.direction * self.speed
                    self.rect.center = self.pos
                    self.check_collide()
                else:
                    self.pos += self.direction * self.speed
                    self.rect.center = self.pos
                    self.check_collide()
                for creature in Creature.other_group:
                    if pygame.Rect.colliderect(self.rect, creature.rect):
                        self.direction_to_creature(creature)
                        self.pos -= self.direction * self.speed
                        self.rect.center = self.pos
                        self.check_collide()
                for wall in M.wall_prox_group:
                    if pygame.Rect.colliderect(self.rect, wall.rect):
                        self.direction_to_wall(wall)
                        self.pos -= self.direction * self.speed

        # Texture update
        self.texture_update()

        # Projectiles
        self.launch_projectile()


class Player(pygame.sprite.Sprite):
    def __init__(self, pos, speed, hp, hpmax, strenght, xp, xpmax, pa_magie, pa_magie_max, etat_piege):
        super().__init__()

        # Texture setup
        self.left_caracter = loadscale("Mage_left.png", dpi, dpi)
        self.right_caracter = loadscale("Mage_right.png", dpi, dpi)
        self.front_caracter = loadscale("Mage_front.png", dpi, dpi)
        self.back_caracter = loadscale("Mage_back.png", dpi, dpi)

        # Animation setup
        images = [["Mage_walking_right_1.png", "Mage_walking_right_2.png", "Mage_walking_right_3.png", "Mage_walking_right_4.png", "Mage_walking_right_5.png", "Mage_walking_right_6.png", "Mage_walking_right_7.png", "Mage_walking_right_8.png", "Mage_walking_right_9.png"], ["Mage_walking_up_1.png", "Mage_walking_up_2.png", "Mage_walking_up_3.png", "Mage_walking_up_4.png", "Mage_walking_up_5.png", "Mage_walking_up_6.png", "Mage_walking_up_7.png", "Mage_walking_up_8.png", "Mage_walking_up_9.png"], [
            "Mage_walking_left_1.png", "Mage_walking_left_2.png", "Mage_walking_left_3.png", "Mage_walking_left_4.png", "Mage_walking_left_5.png", "Mage_walking_left_6.png", "Mage_walking_left_7.png", "Mage_walking_left_8.png", "Mage_walking_left_9.png"], ["Mage_walking_down_1.png", "Mage_walking_down_2.png", "Mage_walking_down_3.png", "Mage_walking_down_4.png", "Mage_walking_down_5.png", "Mage_walking_down_6.png", "Mage_walking_down_7.png", "Mage_walking_down_8.png", "Mage_walking_down_9.png"]]
        self.sprites = []
        direction = []
        for directions in images:
            for image in directions:
                direction.append(loadscale(image, dpi, dpi))
            self.sprites.append(direction.copy())
            direction.clear()
        self.current_sprite = 0

        # Global
        self.image = self.front_caracter
        self.rect = self.image.get_rect(topleft=pos)
        self.direction = pygame.math.Vector2(0, 1)
        self.pos = pos
        self.xp = xp
        self.xpmax = xpmax
        self.pa_magie = pa_magie
        self.pa_magie_max = pa_magie_max
        self.etat_piege = etat_piege

        # Projectiles
        self.all_projectiles = pygame.sprite.Group()
        self.projectile_cooldown = 0

        # Speed
        self.speed = speed

        # Attribut
        self.inventory = []
        self.weapon = []
        self.armour = []
        self.amulet = []
        self.hp = hp
        self.hpmax = hpmax
        self.strenght = strenght

        # Regeneration and life
        self.regen_cooldown = 0
        self.last_regen = 0
        self.attack_cooldown = 1
        self.projectile_cooldown = 0
        self.piege_cooldown = 0
        self.cooldown_magie = 0

    def launch_projectile(self, lanceur, type, damage, rotation):
        self.all_projectiles.add(Projectile(lanceur, type, damage, rotation))

    def get_input(self):
        keys = pygame.key.get_pressed()

        if keys[pygame.K_RIGHT]:
            self.direction = pygame.math.Vector2(1, 0)
            self.image = self.right_caracter
            self.move()
            self.animate(0)

        if keys[pygame.K_LEFT]:
            self.direction = pygame.math.Vector2(-1, 0)
            self.image = self.left_caracter
            self.move()
            self.animate(2)

        if keys[pygame.K_UP]:
            self.direction = pygame.math.Vector2(0, -1)
            self.image = self.back_caracter
            self.move()
            self.animate(1)

        if keys[pygame.K_DOWN]:
            self.direction = pygame.math.Vector2(0, 1)
            self.image = self.front_caracter
            self.move()
            self.animate(3)

        if keys[pygame.K_SPACE]:
            if (Map.timer - self.projectile_cooldown) > 1:
                if self.pa_magie > 0:
                    self.target = M.player.direction
                    self.launch_projectile(self, "fireball", 5, False)
                    M.sound.play("boule_feu")
                    self.pa_magie -= 1
                self.projectile_cooldown = Map.timer

        if keys[pygame.K_v]:
            if (Map.timer - self.projectile_cooldown) > 1:
                if self.weapon != []:
                    self.target = M.player.direction
                    if self.weapon[0].type == "shuriken":
                        self.launch_projectile(
                            self, "shuriken", self.weapon[0].strenght, True)
                        self.weapon.remove(self.weapon[0])
                    elif self.weapon[0].type == "sword":
                        self.launch_projectile(
                            self, "sword", self.weapon[0].strenght, True)
                        self.strenght -= self.weapon[0].strenght
                        self.weapon.remove(self.weapon[0])
                    elif self.weapon[0].type == "arrow":
                        self.launch_projectile(
                            self, "arrow", self.weapon[0].strenght, False)
                        self.weapon[0].durability -= 1
                        if self.weapon[0].durability <= 0:
                            self.weapon.remove(self.weapon[0])
                self.projectile_cooldown = Map.timer

        if keys[pygame.K_n]:
            M.go_down()

        if keys[pygame.K_1]:
            self.use_potion(0)

        if keys[pygame.K_2]:
            self.use_potion(1)

        if keys[pygame.K_3]:
            self.use_potion(2)

        if keys[pygame.K_w]:
            if len(self.weapon) == 1:
                if self.weapon[0].type == "sword":
                    self.strenght -= self.weapon[0].strenght
                self.weapon.remove(self.weapon[0])

        if keys[pygame.K_x]:
            if len(self.armour) == 1:
                self.hpmax -= self.armour[0].health
                if self.hp > self.hpmax:
                    self.hp = self.hpmax
                self.armour.remove(self.armour[0])

        if keys[pygame.K_c]:
            if len(self.amulet) == 1:
                self.pa_magie_max -= self.amulet[0].health
                if self.pa_magie > self.pa_magie_max:
                    self.pa_magie = self.pa_magie_max
                self.amulet.remove(self.amulet[0])

        if keys[pygame.K_b]:
            if (Map.timer - self.cooldown_magie) > 1:
                if self.pa_magie >= 5:
                    self.pa_magie -= 5
                    l = []
                    for map in M._rooms:
                        if self not in map:
                            l.append(map)
                    random_room = random.choice(l)
                    l = []
                    self.rect.x, self.rect.y = offset + dpi * random_room.center().x, dpi * \
                        random_room.center().y
                self.cooldown_magie = Map.timer

    def resize(self):
        self.left_caracter = loadscale("Mage_left.png", dpi, dpi)
        self.right_caracter = loadscale("Mage_right.png", dpi, dpi)
        self.front_caracter = loadscale("Mage_front.png", dpi, dpi)
        self.back_caracter = loadscale("Mage_back.png", dpi, dpi)
        self.image = self.front_caracter
        self.rect = self.image.get_rect()

        # Animation's textures
        images = [["Mage_walking_right_1.png", "Mage_walking_right_2.png", "Mage_walking_right_3.png", "Mage_walking_right_4.png", "Mage_walking_right_5.png", "Mage_walking_right_6.png", "Mage_walking_right_7.png", "Mage_walking_right_8.png", "Mage_walking_right_9.png"], ["Mage_walking_up_1.png", "Mage_walking_up_2.png", "Mage_walking_up_3.png", "Mage_walking_up_4.png", "Mage_walking_up_5.png", "Mage_walking_up_6.png", "Mage_walking_up_7.png", "Mage_walking_up_8.png", "Mage_walking_up_9.png"], [
            "Mage_walking_left_1.png", "Mage_walking_left_2.png", "Mage_walking_left_3.png", "Mage_walking_left_4.png", "Mage_walking_left_5.png", "Mage_walking_left_6.png", "Mage_walking_left_7.png", "Mage_walking_left_8.png", "Mage_walking_left_9.png"], ["Mage_walking_down_1.png", "Mage_walking_down_2.png", "Mage_walking_down_3.png", "Mage_walking_down_4.png", "Mage_walking_down_5.png", "Mage_walking_down_6.png", "Mage_walking_down_7.png", "Mage_walking_down_8.png", "Mage_walking_down_9.png"]]
        self.sprites = []
        direction = []
        for directions in images:
            for image in directions:
                direction.append(loadscale(image, dpi, dpi))
            self.sprites.append(direction.copy())
            direction.clear()

    def move(self):
        scaled_direction = tuple([round(c * self.speed)
                                 for c in self.direction])
        self.rect.move_ip(scaled_direction)
        if any(pygame.sprite.spritecollide(self, M.wall_group, False)):
            self.rect.move_ip((-scaled_direction[0], -scaled_direction[1]))

        for creature in M.all_creatures:
            if pygame.Rect.colliderect(self.rect, creature.rect):
                if creature.type == "piege":
                    self.speed = 0
                    self.etat_piege = True
                    self.piege_cooldown = Map.timer + 3

        if self.etat_piege == True:
            if Map.timer > self.piege_cooldown:
                self.speed = 40/M._size
                self.etat_piege = False
        for equipment in M.all_equipments:
            if pygame.Rect.colliderect(self.rect, equipment.rect):
                self.take_equipment(equipment)

    def damage(self, amount):
        if self.hp - amount > amount:
            self.hp -= amount
        else:
            M.game_over()

    def regeneration(self, amount):
        if self.hp + amount < self.hpmax:
            self.hp += amount
        else:
            self.hp = self.hpmax

    def regeneration_magie(self, amount):
        if self.pa_magie + amount < self.pa_magie_max:
            self.pa_magie += amount
        else:
            self.pa_magie = self.pa_magie_max

    def take_equipment(self, equipment):

        if equipment.type == "sword":
            if len(self.weapon) == 0:
                self.weapon.append(equipment)
                self.strenght += equipment.strenght
                self.durability = equipment.durability
                M.all_equipments.remove(equipment)

        if equipment.type == "shuriken":
            if len(self.weapon) == 0:
                self.weapon.append(equipment)
                M.all_equipments.remove(equipment)

        if equipment.type == "arrow":
            if len(self.weapon) == 0:
                self.weapon.append(equipment)
                M.all_equipments.remove(equipment)

        if equipment.type == "armour":
            if len(self.armour) == 0:
                self.armour.append(equipment)
                self.hpmax += equipment.health
                M.all_equipments.remove(equipment)

        if equipment.type == "potion":
            if len(self.inventory) < 3:
                self.inventory.append(equipment)
                M.all_equipments.remove(equipment)

        if equipment.type == "amulet":
            if len(self.amulet) == 0:
                self.amulet.append(equipment)
                self.pa_magie_max += self.amulet[0].health
                M.all_equipments.remove(equipment)

    def use_potion(self, n):
        if (Map.timer - Equipment.potion_cooldown) > 3:
            if n < len(self.inventory) and self.inventory != []:
                if self.inventory[n].type_equipment == "potion_vie":
                    self.hp += self.inventory[n].health
                    if self.hp > self.hpmax:
                        self.hp = self.hpmax
                if self.inventory[n].type_equipment == "potion_magie":
                    self.pa_magie += self.inventory[n].health
                    if self.pa_magie > self.pa_magie_max:
                        self.pa_magie = self.pa_magie_max
                self.inventory.remove(self.inventory[n])
                Equipment.potion_cooldown = Map.timer

    def health_bar(self):
        back_bar = Health_Bar(self.rect, self, False)
        health_bar = Health_Bar(self.rect, self, True)
        return [back_bar, health_bar]

    def get_coord(self):
        center = self.rect.center
        return Coord(math.floor((center[0] - offset)/dpi), math.floor(center[1]/dpi))

    def animate(self, direction):
        self.current_sprite += 0.3

        if direction == 0:
            if self.current_sprite >= len(self.sprites[0]):
                self.current_sprite = 0
            self.image = self.sprites[0][int(self.current_sprite)]

        elif direction == 1:
            if self.current_sprite >= len(self.sprites[1]):
                self.current_sprite = 0
            self.image = self.sprites[1][int(self.current_sprite)]

        elif direction == 2:
            if self.current_sprite >= len(self.sprites[2]):
                self.current_sprite = 0
            self.image = self.sprites[2][int(self.current_sprite)]

        else:
            if self.current_sprite >= len(self.sprites[3]):
                self.current_sprite = 0
            self.image = self.sprites[3][int(self.current_sprite)]

    def update(self):
        # Surrounding textures
        M.wall_prox_group.empty()
        M.ground_prox_group.empty()
        update = 2 * dpi
        for sprite in M.wall_group:
            if self.rect.x - update <= sprite.rect.x <= self.rect.x + update and self.rect.y - update <= sprite.rect.y <= self.rect.y + update:
                M.wall_prox_group.add(sprite)
        for sprite in M.ground_group:
            if self.rect.x - update <= sprite.rect.x <= self.rect.x + update and self.rect.y - update <= sprite.rect.y <= self.rect.y + update:
                M.ground_prox_group.add(sprite)

        # Inputs
        self.get_input()

        # Damage
        for creature in M.all_creatures:
            if pygame.Rect.colliderect(self.rect, creature.rect):
                if creature.attack_cooldown < Map.timer:
                    self.damage(creature.strenght)
                    if len(self.armour) == 1:
                        self.armour[0].durability -= 1
                        if self.armour[0].durability == 0:
                            self.hpmax -= self.armour[0].health
                            if self.hp > self.hpmax:
                                self.hp = self.hpmax
                            self.armour.remove(self.armour[0])
                    if len(self.weapon) == 1:
                        if self.weapon[0].type == "sword":
                            self.weapon[0].durability -= 1
                            if self.weapon[0].durability == 0:
                                self.strenght -= self.weapon[0].strenght
                                self.weapon.remove(self.weapon[0])
                    creature.attack_cooldown = Map.timer + 0.3
                if self.attack_cooldown < Map.timer:
                    creature.damage(self.strenght)
                    self.attack_cooldown = Map.timer + 0.3

        # Regeneration cooldown
        self.regen_cooldown = Map.timer
        if self.regen_cooldown > self.last_regen + 10:
            self.regeneration(1)
            self.regeneration_magie(1)
            self.last_regen = self.regen_cooldown


class Projectile(pygame.sprite.Sprite):
    cooldown = Map.timer

    def __init__(self, lanceur, type, damage, rotation=False):
        super().__init__()

        # Specifications
        self.velocity = 3
        self.player = M.player
        self.lanceur = lanceur
        self.type = type

        # Type of projectiles
        self.fireball = ["fireball_right.png", "fireball_up.png",
                         "fireball_left.png", "fireball_down.png"]
        self.arrow = ["arrow_right.png", "arrow_up.png",
                      "arrow_left.png", "arrow_down.png"]
        self.shuriken = ["shuriken.png", "shuriken.png",
                         "shuriken.png", "shuriken.png"]
        self.weapon = ["sword.png", "sword.png", "sword.png", "sword.png"]

        if self.type == "fireball":
            self.textures = self.fireball
        elif self.type == "shuriken":
            self.textures = self.shuriken
        elif self.type == "arrow":
            self.textures = self.arrow
        elif self.type == "sword":
            self.textures = self.weapon
        else:
            raise ValueError("Not a projectile")

        if self.textures:
            self.right = loadscale(self.textures[0], dpi//2, dpi//2)
            self.up = loadscale(self.textures[1], dpi//2, dpi//2)
            self.left = loadscale(self.textures[2], dpi//2, dpi//2)
            self.down = loadscale(self.textures[3], dpi//2, dpi//2)

        # Sprite
        self.image = self.down
        self.rect = self.image.get_rect(
            center=(lanceur.rect.x + dpi/3, lanceur.rect.y + dpi/3))

        # Rotation
        self.angle = 0
        self.rotation = rotation

        # Direction
        self.direction = lanceur.direction
        self.damage = damage
        self.origine_image = self.image

    def rotate(self):
        if self.rotation == True:
            self.angle += 5
            self.image = pygame.transform.rotozoom(
                self.origine_image, self.angle, 1)
            self.rect = self.image.get_rect(center=self.rect.center)

    def remove(self):
        M.player.all_projectiles.remove(self)

    def move(self):

        if self.lanceur == M.player:
            for group in M.wall_group, M.all_creatures:
                for sprite in group:
                    if sprite.rect.colliderect(self.rect):
                        self.remove()
                        if sprite in M.all_creatures:
                            sprite.damage(self.damage)
        else:
            for sprite in M.wall_group:
                if sprite.rect.colliderect(self.rect):
                    self.remove()

            if M.player.rect.colliderect(self.rect):
                M.player.damage(self.damage)
                self.remove()

            for monstre in filter(lambda creature: creature is not self.lanceur, M.all_creatures):
                if monstre.type != "piege":
                    if monstre.rect.colliderect(self.rect):
                        monstre.damage(self.damage)
                        self.remove()

        angle = self.direction.angle_to(pygame.math.Vector2(1, 0))
        if -45 <= angle < 45:
            self.image = self.right
            self.rect.x += self.velocity
        elif 45 <= angle < 135:
            self.image = self.up
            self.rect.y -= self.velocity
        elif -45 > angle >= -135:
            self.image = self.down
            self.rect.y += self.velocity
        else:
            self.image = self.left
            self.rect.x -= self.velocity
        self.rotate()

    def update(self):
        for sprite in M.wall_group:
            if self.rect.x - 1.5 * dpi <= sprite.rect.x <= self.rect.x + 1.5 * dpi and self.rect.y - 1.5 * dpi <= sprite.rect.y <= self.rect.y + 1.5 * dpi:
                M.wall_prox_group.add(sprite)
        for sprite in M.ground_group:
            if self.rect.x - 1.5 * dpi <= sprite.rect.x <= self.rect.x + 1.5 * dpi and self.rect.y - 1.5 * dpi <= sprite.rect.y <= self.rect.y + 1.5 * dpi:
                M.ground_prox_group.add(sprite)


class Interface(pygame.sprite.Sprite):
    def __init__(self, pos=(0, 0), image=None):
        super().__init__()
        self.pos = pos
        self.image = loadscale(image, offset, height)
        self.rect = self.image.get_rect(topleft=pos)
        self.icon_group = pygame.sprite.Group()

    def left_interface(self):
        # Font
        font = pygame.font.Font('Gabriola.ttf', 45)
        hp = font.render(str(round(M.player.hp))+"/" +
                         str(round(M.player.hpmax)), True, (22, 196, 44))
        hp_rect = hp.get_rect(topleft=(width/7, height/1.44))
        magic = font.render(str(round(M.player.pa_magie))+"/" +
                            str(round(M.player.pa_magie_max)), True, (0, 110, 255))
        magic_rect = magic.get_rect(topleft=(width/7, height/1.3))
        strenght = font.render(
            str(round(M.player.strenght)), True, (203, 17, 20))
        strenght_rect = strenght.get_rect(topleft=(width/7, height/1.2))
        exp = font.render(str(round(M.player.xp))+"/" +
                          str(round(M.player.xpmax)), True, (255, 216, 0))
        exp_rect = exp.get_rect(topleft=(width/7, height/1.1))
        screen.blit(hp, hp_rect)
        screen.blit(magic, magic_rect)
        screen.blit(strenght, strenght_rect)
        screen.blit(exp, exp_rect)

        # Icons
        self.icon_group.empty()
        for i in range(len(M.player.inventory)):
            potion = loadscale(M.player.inventory[i].png, height/10, height/10)
            icon = Icon(potion, (width/17.3 + i*width/19, height/1.59))
            self.icon_group.add(icon)
        if M.player.armour != []:
            armour = loadscale(M.player.armour[0].png, height/10, height/10)
            icon = Icon(armour, (width/15.3, height/2.15))
            self.icon_group.add(icon)
        if M.player.weapon != []:
            sword = loadscale(M.player.weapon[0].png, height/13, height/13)
            icon = Icon(sword, (width/6.4, height/2.15))
            self.icon_group.add(icon)
        if M.player.amulet != []:
            amulet = loadscale(M.player.amulet[0].png, height/15, height/15)
            icon = Icon(amulet, (width/9.1, height/12.7))
            self.icon_group.add(icon)
        self.icon_group.draw(screen)

    def update(self):
        if self == M.left_interface:
            self.left_interface()


class Health_Bar(pygame.sprite.Sprite):
    def __init__(self, pos, owner, type=True):
        super().__init__()
        self.owner = owner
        self.type = type
        self.pos = pos

        if type == True:
            self.image = pygame.Surface(((dpi*owner.hp)/owner.hpmax, dpi/10))
            self.rect = self.image.get_rect(topleft=(pos.x, pos.y))
            self.image.fill((111, 210, 46))
        else:
            self.image = pygame.Surface((dpi, dpi/10))
            self.rect = self.image.get_rect(topleft=(pos.x, pos.y))
            self.image.fill((60, 63, 60))

    def update(self):

        if self.owner.hp > 0:
            if self.type == True:
                self.image = pygame.Surface(
                    ((dpi*self.owner.hp)/self.owner.hpmax, dpi/10))
                self.image.fill((111, 210, 46))
            if self.type == False:
                self.image.fill((60, 63, 60))
            self.rect = self.image.get_rect(topleft=self.owner.rect.topleft)
        else:
            M.health_bar_group.remove(self)

        # Surrounding textures
        for sprite in M.wall_group:
            if self.rect.x - 1.5 * dpi <= sprite.rect.x <= self.rect.x + 1.5 * dpi and self.rect.y - 1.5 * dpi <= sprite.rect.y <= self.rect.y + 1.5 * dpi:
                M.wall_prox_group.add(sprite)
        for sprite in M.ground_group:
            if self.rect.x - 1.5 * dpi <= sprite.rect.x <= self.rect.x + 1.5 * dpi and self.rect.y - 1.5 * dpi <= sprite.rect.y <= self.rect.y + 1.5 * dpi:
                M.ground_prox_group.add(sprite)


class Sound:
    def __init__(self):
        self.sounds = {'boule_feu': pygame.mixer.Sound(
            "son/boule_feu.ogg"), 'escalier': pygame.mixer.Sound("son/escalier.ogg")}

    def play(self, name):
        self.sounds[name].play()


class Icon(pygame.sprite.Sprite):
    def __init__(self, image, pos):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect(center=pos)


# General setup
pygame.init()
clock = pygame.time.Clock()

# Game screen
size = width, height = 1920, 1080
screen = pygame.display.set_mode(size)

# Map setup
mapsize = [8, 10, 12, 20]
nb_rooms_possible = [6, 8, 5, 4, 3]
nb_creature = [2, 3, 5, 7]
nb_equipment = [2, 3, 5, 7, 8]

M = Map(nb_rooms_possible, mapsize, nb_equipment, nb_creature)

# Start Menu
banner = loadscale("ecran_play.png", width, height)
button = loadscale("button_play.png", 330, 150)
button_rect = button.get_rect(center=(width/2, height/2))

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            truc.quit()
            pygame.quit()
            sys.exit()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if M.is_playing == False:
                if button_rect.collidepoint(event.pos):
                    M.start()
    pygame.display.flip()
    if M.is_playing:
        M.update()
    else:
        screen.blit(banner, (0, 0))
        screen.blit(button, (button_rect))
    clock.tick(60)
