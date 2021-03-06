import unittest
from Queue import Queue


class Key(object):
    C = 0
    C_Sharp = 1
    D = 2
    D_Sharp = 3
    E = 4
    F = 5
    F_Sharp = 6
    G = 7
    G_Sharp = 8
    A = 9
    A_Sharp = 10
    B = 11

    @classmethod
    def all(cls):
        return range(12)


# Represents a chord
class Chord(object):
    # These lists are positions within a scale. [0, 2, 4] is first, third and fifth which is a regular triad
    triad = [0, 2, 4]
    triad_octave = [0, 2, 4, 7]
    suspended_second = [0, 2, 3]
    suspended_fourth = [0, 2, 5]
    seventh = [0, 2, 4, 7]
    seventh_octave = [0, 2, 4, 6, 7]
    sixth = [0, 2, 4, 5, 7]

    all = [triad, triad_octave, suspended_second, suspended_fourth, seventh, seventh_octave, sixth]


# Represents a scale
class Scale(object):
    major = [0, 2, 4, 5, 7, 9, 11]
    minor = [0, 2, 3, 5, 7, 8, 10]
    minor_pentatonic = [0, 3, 5, 7, 10]
    minor_blues = [0, 3, 5, 6, 7, 10]

    all = [major, minor, minor_pentatonic, minor_blues]

    # Make a new scale with a scale passed to it (e.g. scale = Scale(minor_blues))
    def __init__(self, scale, key=Key.C, base_octave=3):
        self.scale = scale
        self.length = len(scale)
        self.base_octave = base_octave
        self.key = key
        interval = -7
        self.all_positions = []
        while True:
            position = self.interval_to_position(interval)
            if position > 127:
                break
            if position >= 0:
                self.all_positions.append(position)
            interval += 1
        self.position_index_dict = {self.all_positions[n]: n for n in range(len(self.all_positions))}

    def interval_to_position(self, interval):
        return self.key + self.scale[interval % self.length] + 12 * (interval / self.length + self.base_octave)

    def position_at_interval(self, position, interval):
        root_index = self.position_index_dict[position]
        return self.all_positions[root_index + interval]

    # Get a position from this scale starting with a given interval from the root (0, 1, 2, 3 etc.)
    def position(self, interval):
        position = self.interval_to_position(interval)
        return position

    # Get a chord from this scale starting with a given interval from the root (0, 1, 2, 3 etc.) Set the chord type
    # using intervals (e.g. chord = scale.chord(0, intervals=Chord.triad) gives the root triad. Chords always in key!)
    def chord(self, interval, intervals=Chord.triad):
        positions = map(lambda i: self.interval_to_position(interval + i), intervals)
        return positions

    # Go up by number of octaves
    def change_octave(self, by):
        self.base_octave = self.base_octave + by


scale_array = map(lambda key: Scale(Scale.major, key, base_octave=0), range(12))

keys_array = [set() for _ in range(128)]
for k in Key.all():
    for pos in scale_array[k].all_positions:
        keys_array[pos].add(k)


def possible_keys(positions):
    key_set = set(range(12))
    for position in positions:
        key_set = key_set.intersection(keys_array[position])
    return key_set


class KeyTracker(object):
    """
    Decides possible keys given the last few midi note positions passed
    """

    def __init__(self, capacity=16):
        """

        :param capacity: The amount of notes to keep in memory when deciding what the key is
        """
        self.queue = Queue()
        self.capacity = capacity

    def add_note(self, note):
        """

        :param note: An integer giving the midi position (0 - 127)
        """
        self.queue.put(note)
        if len(self.queue.queue) > self.capacity:
            self.queue.get()

    @property
    def key(self):
        """

        :return: The most likely key given the notes that have been passed in
        """
        return list(self.keys)[0]

    @property
    def scale(self):
        """

        :return: A scale object corresponding to the most likely key
        """
        return scale_array[self.key]

    @property
    def keys(self):
        """

        :return: A list of possible keys given notes recently passed in
        """
        if len(self.queue.queue) == 0:
            return Key.C
        keys = []
        note_list = list(self.queue.queue)
        while len(keys) == 0:
            keys = possible_keys(note_list)
            note_list = note_list[1:]
        return keys


class KeySelectionTestCase(unittest.TestCase):
    def test_keys_array(self):
        self.assertTrue(Key.C in keys_array[0])
        self.assertTrue(Key.C not in keys_array[1])

    def test_positions(self):
        self.assertTrue(0 in scale_array[Key.C].all_positions)
        self.assertTrue(1 not in scale_array[Key.C].all_positions)
        self.assertTrue(1 in scale_array[Key.C_Sharp].all_positions)

    def test_possible_keys(self):
        self.assertTrue(Key.C in possible_keys([0, 2, 4]))
        self.assertTrue(Key.C_Sharp not in possible_keys([0, 2, 4]))

        self.assertTrue(Key.C not in possible_keys([1, 3, 5]))
        self.assertTrue(Key.C_Sharp in possible_keys([1, 3, 5]))

    def test_key_tracker(self):
        key_tracker = KeyTracker()
        key_tracker.add_note(0)
        key_tracker.add_note(2)
        self.assertTrue(Key.C in key_tracker.keys)
        self.assertTrue(Key.G in key_tracker.keys)
        self.assertTrue(Key.C_Sharp not in key_tracker.keys)
        self.assertTrue(Key.D not in key_tracker.keys)

        key_tracker = KeyTracker(capacity=1)
        key_tracker.add_note(0)
        self.assertTrue(Key.C in key_tracker.keys)
        self.assertTrue(Key.D not in key_tracker.keys)

        key_tracker.add_note(2)
        self.assertTrue(Key.C in key_tracker.keys)
        self.assertTrue(Key.D in key_tracker.keys)

    def test_key_change(self):
        key_tracker = KeyTracker()
        key_tracker.add_note(0)
        self.assertTrue(Key.C in key_tracker.keys)
        self.assertTrue(Key.D not in key_tracker.keys)

        key_tracker.add_note(1)
        key_tracker.add_note(2)
        self.assertTrue(Key.C not in key_tracker.keys)
        self.assertTrue(Key.D in key_tracker.keys)


if __name__ == "__main__":
    unittest.main()
