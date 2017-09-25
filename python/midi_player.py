import mido
from Queue import Queue
import music
from threading import Thread
import logging
from datetime import datetime
import os

path = os.path.realpath(__file__)
dir_path = os.path.dirname(os.path.realpath(__file__))

print dir_path

# noinspection PyUnresolvedReferences
input_names = mido.get_output_names()

REFACE = 'reface DX'
MPX = 'MPX16'
SIMPLE_SYNTH = 'SimpleSynth virtual input'

CHANNEL_PARTITION = 8

simple_port = None

# noinspection PyBroadException
try:
    instrument = music.MidiInstrument()
except Exception:
    logging.warn("Midi instrument could not be opened")


# Creates a port object corresponding to an instrument if it exists, else to a Simple inbuilt synth
def make_port(name):
    for input_name in input_names:
        if name in input_name:
            name = input_name
    global simple_port
    try:
        # noinspection PyUnresolvedReferences
        return mido.open_output(name)
    except IOError:
        logging.warn("{} not found.".format(name))
        if simple_port is None:
            # noinspection PyUnresolvedReferences
            simple_port = mido.open_output()
        return simple_port


keys_port = make_port(REFACE)
drum_port = make_port(MPX)


# Class representing key-value pairs that can be queued as commands
class Command:
    def __init__(self, name, value=None):
        self.name = name
        self.value = value

    add_effect = "add_effect"
    remove_effect = "remove_effect"
    pitch_bend = "pitch_bend"
    volume = "volume"
    fade_out = "fade_out"
    stop = "stop"


class Effect:
    def __init__(self, func):
        self.func = func

    def apply(self, msg_array):
        return self.func(msg_array)

    @staticmethod
    def repeat(msg_array):
        for msg in msg_array:
            new_msg = msg.copy()
            new_msg.time += 0.5
            msg_array.append(new_msg)
        return msg_array

    @staticmethod
    def fifth(msg_array):
        for msg in msg_array:
            if msg.note + 7 > 127:
                continue
            new_msg = msg.copy()
            new_msg.note += 7
            msg_array.append(new_msg)
        return msg_array


# Class representing individual midi channel
class Channel:
    note_off = "note_off"
    note_on = "note_on"

    def __init__(self, number, volume=1.0, fade_rate=0.1, note_on_listener=None):
        self.note_on_listener = note_on_listener
        self.number = number
        # Decides which port output should be used depending on the channel number
        self.port = keys_port if number < CHANNEL_PARTITION else drum_port
        self.volume = volume
        self.fade_rate = fade_rate
        self.queue = Queue()
        self.fade_start = None
        self.playing_notes = []
        self.effects = []

    # Send a midi message to this channel
    def send_message(self, msg):

        try:
            # Are there any commands waiting?
            if not self.queue.empty():
                command = self.queue.get()
                # Volume changing command. Overrides current fades
                if command.name == Command.volume:
                    self.volume = command.value
                    self.fade_start = None
                # Fade out command. Fade out occurs constantly until silent or overridden by volume change
                elif command.name == Command.fade_out:
                    # Fade out command has no effect if fadeout already underway
                    if self.fade_start is None:
                        # When did the fadeout start?
                        self.fade_start = datetime.now()
                elif command.name == Command.add_effect:
                    self.effects.append(command.value)
                elif command.name == Command.remove_effect and command.value in self.effects:
                    self.effects.remove(command.value)

            # True if a fade out is in progress
            if self.fade_start is not None:
                # How long has the fade been occurring?
                seconds = (datetime.now() - self.fade_start).total_seconds()
                self.volume *= (1 - self.fade_rate * seconds)
                if self.volume < 0:
                    self.volume = 0
                    self.fade_start = None
            msg.velocity = int(self.volume * msg.velocity)

            msgs = self.apply_effects(msg.copy())

            for msg in msgs:
                # Actually send the midi message
                self.port.send(msg)
            # Check if it was a note message
            if msg.type == Channel.note_on:
                # Keep track of notes that are currently playing
                self.playing_notes.append(msg.note)
                self.playing_notes.sort()
                if self.note_on_listener is not None:
                    self.note_on_listener(msg)
            elif msg.type == Channel.note_off:
                self.playing_notes.remove(msg.note)
        except AttributeError as e:
            logging.exception(e)
        except ValueError as e:
            logging.exception(e)

    def add_effect(self, effect):
        self.queue.put(Command(Command.add_effect, effect))

    def remove_effect(self, effect):
        self.queue.put(Command(Command.remove_effect, effect))

    # Stop all currently playing notes
    def stop_playing_notes(self):
        for note in self.playing_notes:
            self.stop_note(note)

    # Stop a specific note
    def stop_note(self, note):
        # noinspection PyTypeChecker
        self.send_message(mido.Message(type=Channel.note_off, velocity=0, note=note))

    # Set the volume of this channel (float from 0 - 1)
    def set_volume(self, volume):
        self.queue.put(Command(Command.volume, volume))

    # Start fading out this channel
    def fade_out(self):
        self.queue.put(Command(Command.fade_out))

    def apply_effects(self, msg):
        msg_array = [msg]
        for effect in self.effects:
            msg_array = effect.apply(msg_array)
        return msg_array


# A bass channel that plays a note from a chord shifted down two octaves on a drum beat
class BassChannel(Channel, object):
    def __init__(self, number, chord_channel, drum_channel, volume=1.0, octave_shift=2):
        super(BassChannel, self).__init__(number, volume)
        self.chord_channel = chord_channel
        self.drum_channel = drum_channel
        self.drum_channel.note_on_listener = self.on_drum_played
        self.pressed_positions = []
        self.octave_shift = octave_shift
        self.pressed_positions_queue = Queue()

    # Called when a drum beat is played
    def on_drum_played(self, msg):
        # Stop all playing notes
        self.stop_playing_notes()
        # Updated pressed positions if waiting in queue
        if not self.pressed_positions_queue.empty():
            self.pressed_positions = self.pressed_positions_queue.get()
        for position in self.pressed_positions:
            try:
                note = self.chord_channel.playing_notes[position % len(self.chord_channel.playing_notes)]
                shift = position / len(self.chord_channel.playing_notes)

                msg.channel = self.number
                msg.note = note + 12 * (shift - self.octave_shift)

                self.send_message(msg)
            except ZeroDivisionError as e:
                logging.exception(e)

    # Set the positions of pressed notes
    def set_pressed_positions(self, pressed_positions):
        self.pressed_positions_queue.put(pressed_positions)


# Represents a midi song loaded from a file
class Song:
    def __init__(self, filename="channels_test.mid", is_looping=False):
        self.filename = filename
        self.queue = Queue()
        self.is_stopping = False
        self.is_looping = is_looping
        self.mid = mido.MidiFile("{}/media/{}".format(dir_path, self.filename))
        self.channels = map(Channel, range(0, 16))

    # Play the midi file (should be called on new thread)
    def play_midi_file(self):
        self.is_stopping = False

        # Take midi messages from a generator
        for msg in self.mid.play():
            # Break if should stop
            if self.is_stopping:
                break
            # Check if any commands in queue
            if not self.queue.empty():
                command = self.queue.get()
                if isinstance(command, Command):
                    if command.name == Command.pitch_bend:
                        instrument.pitch_bend(command.value)
                    if command.name == Command.stop:
                        self.is_stopping = True
            try:
                # Send a message to its assigned channel
                self.channels[msg.channel].send_message(msg)
            except AttributeError as e:
                logging.exception(e)
            except IndexError as e:
                logging.exception(e)
        # Loop again if set to do so
        if self.is_looping and not self.is_stopping:
            self.play_midi_file()

    # Start this song on a new thread
    def start(self):
        t = Thread(target=self.play_midi_file)
        t.start()

    # Stop this song
    def stop(self, *args):
        print "STOP"
        self.send_command(Command.stop)

    # Queue up a command
    def send_command(self, name, value=None):
        self.queue.put(Command(name, value))

    # Set which channels should be playing
    def set_included_channels(self, pressed_positions):
        for channel in self.channels:
            if channel.number in pressed_positions:
                channel.set_volume(1.0)
            else:
                channel.fade_out()

    # Play all channels
    def include_all_channels(self):
        for channel in self.channels:
            channel.set_volume(1.0)


repeat = Effect(Effect.repeat)
fifth = Effect(Effect.fifth)
