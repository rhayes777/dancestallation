class Note(object):
    def __init__(self, position=(0, 0), velocity=(0, 0), acceleration=(0, 0)):
        self.position = position
        self.velocity = velocity
        self.acceleration = acceleration

    def step_forward(self):
        self.velocity = tuple(sum(pair) for pair in zip(self.velocity, self.acceleration))
        self.position = tuple(sum(pair) for pair in zip(self.position, self.velocity))


class TestNote(object):
    def test_no_movement(self):
        note = Note(position=(0, 0), velocity=(0, 0))
        note.step_forward()

        assert note.position == (0, 0)

    def test_up_movement(self):
        note = Note(position=(0, 0), velocity=(1, 0))
        note.step_forward()

        assert note.position == (1, 0)

    def test_right_movement(self):
        note = Note(position=(0, 0), velocity=(0, 1))
        note.step_forward()

        assert note.position == (0, 1)

    def test_left_movement(self):
        note = Note(position=(0, 0), velocity=(0, -1))
        note.step_forward()

        assert note.position == (0, -1)

    def test_double_movement(self):
        note = Note(position=(0, 0), velocity=(1, 1))
        note.step_forward()
        note.step_forward()

        assert note.position == (2, 2)

    def test_acceleration(self):
        note = Note(position=(0, 0), velocity=(0, 0), acceleration=(1, 0))

        note.step_forward()

        assert note.velocity == (1, 0)
        assert note.position == (1, 0)

        note.step_forward()

        assert note.velocity == (2, 0)
        assert note.position == (3, 0)