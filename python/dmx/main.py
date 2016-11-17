import pysimpledmx
import lights

# Make an object to talk to DMX by giving it the number of the USB port the adapter is connected to
dmx = pysimpledmx.DMXConnection(3)

# Create an instance of my light class, giving it the DMX object and a number from 1-512 indicating the address of a light
light = lights.Light(dmx, 1)

# Set colour values using the instance of the light class
light.set_r(255)
light.set_g(0)
light.set_b(255)

# Set some other stuff (I'm not sure what master does yet)
light.set_brightness(255)
light.set_strobe_speed(0)
light.set_master(255)

# Update all lights with values that have just been set
dmx.render()

# Example from https://github.com/c0z3n/pySimpleDMX
# dmx = pysimpledmx.DMXConnection(3)
#
# dmx.setChannel(1, 255)  # set DMX channel 1 to full
# dmx.setChannel(2, 128)  # set DMX channel 2 to 128
# dmx.setChannel(3, 0)  # set DMX channel 3 to 0
# dmx.render()  # render all of the above changes onto the DMX network
#
# dmx.setChannel(4, 255, autorender=True)  # set channel 4 to full and render to the network
