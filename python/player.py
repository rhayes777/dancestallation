import mido
from Queue import Queue
from threading import Thread
import logging
from datetime import datetime
import os
import music

path = os.path.realpath(__file__)
dir_path = os.path.dirname(os.path.realpath(__file__))

# noinspection PyUnresolvedReferences
input_names = mido.get_output_names()

REFACE = 'reface DX'
MPX = 'MPX16'
SIMPLE_SYNTH = 'SimpleSynth virtual input'

CHANNEL_PARTITION = 8
DEFAULT_VOLUME = 0.5
DEFAULT_TEMPO_SHIFT = 1

simple_port = None

# TODO: Consider passing the key tracker only into select tracks
key_tracker = music.KeyTracker()


# noinspection PyClassHasNoInit
class InstrumentType:
    """Different types of midi instrument. The program number of each instrument ranges from n * 8 to (n + 1) * 8"""
    piano = 0
    chromatic_percussion = 1
    organ = 2
    guitar = 3
    bass = 4
    strings = 5
    ensemble = 6
    brass = 7
    reed = 8
    pipe = 9
    synth_lead = 10
    synth_pad = 11
    synth_effects = 12
    ethnic = 13
    percussive = 14
    sound_effects = 15


def make_port(name):
    """
    Create a port with the given name, defaulting to the SimpleSynth port otherwise
    :param name: The name of the port
    :return: A port through which midi messages can be sent
    """
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


class Intervals:
    """Class used to apply set of intervals to a note, using the most likely key"""

    def __init__(self, intervals):
        """

        :param intervals: A series of intervals. For example, [2, 4] would turn a note into a triad
        """
        self.intervals = intervals

    def __call__(self, msg):
        """

        :param msg: A midi note_on message
        :return: An array of midi messages
        """
        new_array = []

        for interval in self.intervals:
            new_msg = msg.copy()
            note = key_tracker.scale.position_at_interval(msg.note, interval)
            if 0 <= note <= 127:
                new_msg.note = note
                new_msg.time = 0
                new_array.append(new_msg)

        return new_array


class Channel(object):
    """Represents an individual midi channel through which messages are passed"""
    note_off = "note_off"
    note_on = "note_on"

    def __init__(self, number, volume=DEFAULT_VOLUME, fade_rate=1, note_on_listener=None):
        """

        :param number: The number of this channel (0-15)
        :param volume: The initial volume of this channel (0.0 - 1.0)
        :param fade_rate: The rate at which this channel should fade
        :param note_on_listener: A listener that is called every time a note_on is played by this channel
        """
        self.note_on_listener = note_on_listener
        self.message_send_listener = None
        self.number = number
        # Decides which port output should be used depending on the channel number
        self.port = keys_port if number < CHANNEL_PARTITION else drum_port
        self.__volume = volume
        self.__volume_queue = Queue()
        self.fade_rate = fade_rate
        self.__fade_start = None
        self.__fade_start_queue = Queue()
        self.playing_notes = set()
        self.__intervals = None
        self.__intervals_queue = Queue()
        self.__program = 0

    @property
    def volume(self):
        while not self.__volume_queue.empty():
            self.__volume = self.__volume_queue.get()
        return self.__volume

    @volume.setter
    def volume(self, volume):
        self.fade_start = None
        self.__volume_queue.put(volume)

    @property
    def fade_start(self):
        while not self.__fade_start_queue.empty():
            if self.__fade_start is None:
                self.__fade_start = datetime.now()
        return self.__fade_start

    @fade_start.setter
    def fade_start(self, fade_start):
        self.__fade_start = fade_start

    def fade(self):
        self.__fade_start_queue.put("start")

    @property
    def intervals(self):
        """The set of intervals currently applied to notes played on this channel"""
        while not self.__intervals_queue.empty():
            self.__intervals = self.__intervals_queue.get()
        return self.__intervals

    @intervals.setter
    def intervals(self, intervals):
        self.__intervals_queue.put(intervals)

    @property
    def program(self):
        """The program (i.e. instrument) of this channel"""
        return self.__program

    @program.setter
    def program(self, program):
        self.__program = program
        self.port.send(mido.Message('program_change', program=self.__program, time=0, channel=self.number))

    @property
    def instrument_type(self):
        """The type of instrument (see InstrumentType above)"""
        return self.program / 8

    @instrument_type.setter
    def instrument_type(self, instrument_type):
        if 0 <= instrument_type < 16:
            self.program = 8 * instrument_type + self.instrument_version

    @property
    def instrument_version(self):
        """The version of the instrument. Each instrument has 8 versions."""
        return self.program % 8

    @instrument_version.setter
    def instrument_version(self, instrument_version):
        if 0 <= instrument_version < 8:
            self.program = 8 * self.instrument_type + instrument_version

    def pitch_bend(self, value):
        """
        Send a pitch bend to this channel
        :param value: The value of the pitch bend
        """
        self.port.send(mido.Message('pitchwheel', pitch=value, time=0, channel=self.number))

    # Send a midi message to this channel
    def send_message(self, msg):

        try:
            # True if a fade out is in progress
            if self.fade_start is not None:
                # How long has the fade been occurring?
                seconds = (datetime.now() - self.fade_start).total_seconds()
                self.volume *= (1 - self.fade_rate * seconds)
                if self.volume < 0:
                    self.volume = 0
                    self.fade_start = None

            if hasattr(msg, 'velocity'):
                msg.velocity = int(self.volume * msg.velocity)

            if hasattr(msg, "note"):
                # Update the key tracker
                key_tracker.add_note(msg.note)

            if hasattr(msg, 'velocity') and self.intervals is not None:
                msgs = self.intervals(msg)
            else:
                msgs = [msg]

            for msg in msgs:
                if callable(self.message_send_listener):
                    self.message_send_listener(msg)
                # Actually send the midi message
                self.port.send(msg)
            if hasattr(msg, 'type'):
                # Check if it was a note message
                if msg.type == Channel.note_on:
                    # Keep track of notes that are currently playing
                    self.playing_notes.add(msg.note)
                    if self.note_on_listener is not None:
                        self.note_on_listener(msg)
                elif msg.type == Channel.note_off and msg.note in self.playing_notes:
                    self.playing_notes.remove(msg.note)
        except AttributeError as e:
            logging.exception(e)
        except ValueError as e:
            logging.exception(e)

    # Stop all currently playing notes
    def stop_playing_notes(self):
        for note in self.playing_notes:
            self.stop_note(note)

    # Stop a specific note
    def stop_note(self, note):
        # noinspection PyTypeChecker
        self.send_message(mido.Message(type=Channel.note_off, velocity=0, note=note))


# Represents a midi song loaded from a file
class Track(Thread):
    def __init__(self, filename="media/channels_test.mid", is_looping=False):
        super(Track, self).__init__()
        self.filename = filename
        self.is_stopping = False
        self.is_looping = is_looping
        self.mid = mido.MidiFile("{}/{}".format(dir_path, self.filename))
        self.original_tempo = self.mid.ticks_per_beat
        self.channels = map(Channel, range(0, 16))
        self.__tempo_shift = DEFAULT_TEMPO_SHIFT
        self.__tempo_shift_queue = Queue()

    @property
    def tempo_shift(self):
        return self.__tempo_shift

    @tempo_shift.setter
    def tempo_shift(self, tempo_shift):
        self.mid.ticks_per_beat = tempo_shift * self.original_tempo
        self.__tempo_shift = tempo_shift

    def channels_with_instrument_type(self, instrument_type):
        return filter(lambda c: c.instrument_type == instrument_type, self.channels)

    # Play the midi file
    def run(self):
        self.is_stopping = False
        play = self.mid.play(meta_messages=True)

        while True:

            # Take midi messages from a generator
            for msg in play:

                # Break if should stop
                if self.is_stopping:
                    break

                try:
                    if isinstance(msg, mido.MetaMessage):
                        continue
                    # Send a message to its assigned channel
                    self.channels[msg.channel].send_message(msg)
                except AttributeError as e:
                    logging.exception(e)
                except IndexError as e:
                    logging.exception(e)

            if self.is_looping:
                play = self.mid.play(meta_messages=True)
                continue
            break

    # Stop this song
    # noinspection PyUnusedLocal
    def stop(self, *args):
        self.is_stopping = True
