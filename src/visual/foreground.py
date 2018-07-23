import pygame
import util
import math
import random

# Colour Constants

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (180, 60, 30)
GREEN = (46, 190, 60)
BLUE = (30, 48, 180)
PINK_MASK = (255, 0, 255)

# Get display info

info = pygame.display.Info()
screen = pygame.display.set_mode((info.current_w, info.current_h))

# Create pygame group for sprites
all_sprites = pygame.sprite.Group()

# Camera - this is the (abstract) point from which we are viewing the scene
#
# Z = 0 is the furthest away from the camera/viewer we will render
# as an object's Z value becomes larger, the object is closer to the viewer
# and will be rendered larger, giving a sense of perspective and scale

# For now, camera is fixed at dead centre of screen...

CAM_x = screen.get_width() / 2
CAM_y = screen.get_height() / 2

# ...and is placed 500px back from the scene

CAM_z = 500


class Flash(object):
    def __init__(self, time):
        self.time = time
        self.blit_surface = pygame.Surface((info.current_w, info.current_h))

        self.blit_surface.fill((255, 255, 255))
        self.timer = -2

    def make_flash(self):
        self.timer = self.time

    def render(self, this_screen):
        self.this_screen = this_screen

        if self.timer >= 0:
            alpha = util.get_new_range_value(1, self.time, self.timer, 0, 255)
            print(alpha)
            self.timer -= 1
            self.blit_surface.set_alpha(alpha)
            self.this_screen.blit(self.blit_surface, (0, 0))

    def is_flashing(self):
        return self.timer > 1  # if timer is greater than 1, is_flashing is true


class NoteSprite(object):
    def __init__(self, pos_x, pos_y, pos_z, size, ref,
                 angle_xy=math.radians(random.randint(0, 360)),
                 angle_zx=math.radians(random.randint(0, 180)),
                 velocity=random.randint(1, 6)):
        """ x, y, z co-ordinates """
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.pos_z = pos_z

        """ This is the 'original' size of the object: The size it has when rendered at Z = 0 """

        self.size = size

        self.ref = ref

        """ angle_zx is the angle at which the object is moving along the Z-X axis... """
        """ So it's the 'bird's eye view' angle of movement of the object """
        """ 0 will be fully "left" as you're looking at it, with object not moving towards viewer at all """
        """ 180 would be fully "right" so the opposite direction, still no Z axis movement - """
        """ 90 is exactly towards the viewer (so no x-axis movement) """

        self.angle_zx = math.radians(angle_zx)

        """ angle_xy is along the 'normal' 2D plane ie. x and y """
        """ so 0 is directly up the screen, 180 is directly down etc """

        self.angle_xy = math.radians(angle_xy)
        self.velocity = velocity

        self.size_render = self.size
        self.this_screen = None

        self.is_on = False

    def update(self):
        """ Do movement calculations """

        x_add = self.velocity * math.sin(self.angle_xy)
        y_add = self.velocity * math.cos(self.angle_xy)
        z_add = self.velocity * math.sin(self.angle_zx)

        """ Update position """

        self.pos_x = self.pos_x + x_add
        self.pos_y = self.pos_y + y_add
        self.pos_z = self.pos_z + z_add

        print(self.pos_z)

        """ Figuring out scale """

        max_scale = screen.get_width() / self.size

        x_distance_to_cam = abs(self.pos_x - CAM_x)
        z_distance_to_cam = abs(CAM_z - self.pos_z)

        z_scale = util.get_new_range_value(0, CAM_z, z_distance_to_cam, 1, max_scale/10)
        x_scale = util.get_new_range_value(0, screen.get_width() / 2, x_distance_to_cam, max_scale/10, 1)

        # print("x_distance_to_cam: ", x_distance_to_cam)

        combined_scale = z_scale - x_scale / z_scale + x_scale

        scale = combined_scale

        if scale <= 1:
            scale = 1
        if scale >= 250:
            scale = 250

        # print("3D Obj scale: ", scale)

        self.size_render = self.size * scale

    def show(self, this_screen):

        self.this_screen = this_screen
        if self.is_on:
            # determine colour based on position
            color = [
                util.get_new_range_value(0, info.current_w, self.pos_x, 30, 255),  # Red
                util.get_new_range_value(0, info.current_h, self.pos_y, 20, 140),  # Green
                util.get_new_range_value(0, info.current_h, self.pos_y, 120, 255)  # Blue
            ]

            pygame.draw.ellipse(this_screen, color,
                                [self.pos_x - (self.size_render / 2),
                                 self.pos_y - (self.size_render / 2),
                                 self.size_render,
                                 self.size_render], 0)

