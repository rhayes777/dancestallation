import copy
import math
from Queue import Queue
from os import path
from random import randint

import pygame

import config
import model
from audio import player as pl
from audio.player import play_note
from control import input
from visual import visual

note_queue = Queue()


def message_read_listener(msg):
    if msg.type == "note_on":
        note_queue.put(msg)


directory = path.dirname(path.realpath(__file__))

play = True

INDENT = 50

pygame.init()
pygame.display.init()
clock = pygame.time.Clock()

track = pl.Track("{}/media/audio/{}".format(directory, config.TRACK_NAME), is_looping=True,
                 message_read_listener=message_read_listener, play_notes=False)

controller = input.Controller(pygame)

player = model.MassiveObject()

model_instance = model.Model(player, visual.SCREEN_SHAPE)

model_instance.player.position = (visual.SCREEN_SHAPE[0] / 2, visual.SCREEN_SHAPE[1] / 2)

last_buttons = {'x': False,
                'up': False,
                'circle': False,
                'right': False,
                'square': False,
                'down': False,
                'triangle': False,
                'left': False,
                'start': False,
                'select': False}

boost_dict = {'x': (-1, -1),
              'up': (0, -1),
              'circle': (1, -1),
              'right': (1, 0),
              'square': (1, 1),
              'down': (0, 1),
              'triangle': (-1, 1),
              'left': (-1, 0),
              'start': (0, 0),
              'select': (0, 0)}


def button_listener(button_dict):
    global last_buttons
    new_buttons = [button for button, is_on in button_dict.items() if is_on and not last_buttons[button]]
    last_buttons = button_dict

    if len(new_buttons) > 0:
        model_instance.boost(boost_dict[new_buttons[0]])


controller.button_listener = button_listener


def rand_tuple():
    return float(randint(0, visual.SCREEN_SHAPE[0])), float(randint(0, visual.SCREEN_SHAPE[1]))


def get_new_range_value(old_range_min, old_range_max, old_value, new_range_min, new_range_max):
    if old_value > old_range_max:
        old_value = old_range_max
    if old_value < old_range_min:
        old_value = old_range_min
    return (old_value - old_range_min) * (new_range_max - new_range_min) / (
            old_range_max - old_range_min) + new_range_min


class Side(object):
    def __init__(self, name, position, direction, colour):
        self.name = name
        self.generator = model.NoteGenerator(position, direction)
        self.position = position
        self.direction = direction
        self.colour = colour
        self.glow = visual.EnergyGlow(position, colour)
        self.scorer = model.Scorer()
        self.channels = list(map(int, config.parser.get(self.name, "channels").split(",")))

    def update(self):
        visual.make_score_notice(self.scorer.score, self.position, 5, self.colour)
        self.glow.set_alpha(min(255, self.scorer.score))

    def add_note(self, side_note):
        model_instance.notes.add(self.generator.make_note(side_note, self.colour))
        track.channels[side_note.channel].send_message(side_note)


sides = [
    Side("left", (INDENT, visual.SCREEN_SHAPE[1] / 2), math.pi / 2, visual.color_dict[0]),
    Side("right", (visual.SCREEN_SHAPE[0] - INDENT, visual.SCREEN_SHAPE[1] / 2), 1.5 * math.pi, visual.color_dict[1]),
    Side("bottom", (visual.SCREEN_SHAPE[0] / 2, visual.SCREEN_SHAPE[1] - INDENT), math.pi, visual.color_dict[2]),
    Side("top", (visual.SCREEN_SHAPE[0] / 2, INDENT), 2 * math.pi, visual.color_dict[3]),
]

for side in sides:
    model_instance.generators.append(side.generator)
    model_instance.scorers.append(side.scorer)

rotation_frame = 0

track.start()

# Keep reading forever
while play:
    rotation_frame += 1
    controller.read()
    clock.tick(24)
    model_instance.step_forward()
    visual.player_cursor_instance.draw(player.position)
    for note in model_instance.notes:
        visual.Note(visual.sprite_sheet.image_for_angle(note.angle), note.position, note.colour, 255)

    while not note_queue.empty():
        note = note_queue.get()
        for side in sides:
            if note.channel in side.channels:
                side.add_note(note)

    # Collision for Score.Notice creation
    for note in model_instance.dead_notes:
        for side in sides:
            if note.note.channel in side.channels:
                side.scorer.add_points(config.POINTS_PER_NOTE)

        visual.make_score_notice(config.POINTS_PER_NOTE, note.position, 30, note.colour)
        visual.make_circle_explosion(visual.Color.GREY, 5, note.position)

        midi_note = copy.copy(note.note)
        midi_note.channel = 9
        midi_note.time = 0
        play_note(midi_note)

    for side in sides:
        side.update()

    visual.draw()
    visual.sprite_group_notes.empty()
