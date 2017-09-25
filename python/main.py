import midi_player
import dancemat
from time import sleep
import signal

mat = dancemat.DanceMat()
track = midi_player.Song(filename="bicycle-ride.mid", is_looping=True)

play = True


def stop(*args):
    global play
    track.stop()
    play = False


signal.signal(signal.SIGINT, stop)

channels = track.channels

chord_channel = channels[0]
drum_channel = channels[8]

bass_channel = midi_player.BassChannel(2, chord_channel, drum_channel)
channels[2] = bass_channel

# Relate button names to positions in the scale
position_dict = {dancemat.Button.triangle: 0,
                 dancemat.Button.down: 1,
                 dancemat.Button.square: 2,
                 dancemat.Button.left: 3,
                 dancemat.Button.right: 4,
                 dancemat.Button.x: 5,
                 dancemat.Button.up: 6,
                 dancemat.Button.circle: 7}


# Function to listen for changes to button state
def listener(status_dict):
    pressed_positions = [position_dict[button] for button in status_dict.keys() if status_dict[button]]
    track.set_included_channels(pressed_positions)
    # bass_channel.set_pressed_positions(pressed_positions)


# Attach that listener function to the dancemat
mat.set_button_listener(listener)

track.start()

# Keep reading forever
while play:
    mat.read()
    sleep(0.05)
