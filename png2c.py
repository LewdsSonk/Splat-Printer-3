#!/bin/python

import sys, os, getopt
from PIL import Image

def main(argv):
  long_opt_list = ["help",
                   "preview",
                   "save",
                   "invertcmap"
                   "opposite",
                   "cautious",
                   "nodither"]
  opts, args = getopt.getopt(argv, "pshinoc", long_opt_list)
  previewBilevel = False
  saveBilevel = False
  invertColormap = False
  no_dither = False
  opposite = False
  cautious = False

  for opt, arg in opts:
    if opt in ['-h', '--help']:
      usage()
      sys.exit()
    elif opt in ['-p', '--preview']:
      previewBilevel = True
    elif opt in ['-s', '--save']:
      saveBilevel = True
    elif opt in ['-o', '--opposite']:
      opposite = True
    elif opt in ['-c', '--cautious']:
      cautious = True
    elif opt in ['-i', '--invertcmap']:
      invertColormap = True
    elif opt in ['-n', '--nodither']:
      no_dither = True

  filename = args[0]
  filename_direct = os.path.basename(filename)
  if not os.path.isdir("splat-images"):
      os.mkdir("splat-images")
  if not os.path.isdir("preview-images"):
      os.mkdir("preview-images")

  if not os.path.isfile(filename):
    filename = "splat-images\\" + filename
  im = Image.open(filename)                # import 320x120 png

  if (im.size[0] == 120 and im.size[1] == 320):
    print("Rotating image counter-clockwise to make it 320px by 120px!")
    im = im.transpose(Image.Transpose.ROTATE_90)
  
  if not (im.size[0] == 320 and im.size[1] == 120):
    print("ERROR: Image must be 320px by 120px!")
    sys.exit()

  # Convert to bilevel image
  if no_dither:
    im = im.convert("1", dither = None) # this also adds dithering if wanted
  else:
    im = im.convert("1", dither = Image.Dither.FLOYDSTEINBERG)

  if previewBilevel:
    print(f"Previewing {filename_direct}!")
    im.show()
  
  if saveBilevel:
    im.save(f"preview-images\\bilevel_{filename_direct}")
    print("Bilevel preview version of " + filename_direct + " saved as bilevel_" + filename_direct)
  
  if not (previewBilevel or saveBilevel):
    im_px = im.load()
    data = []
    for i in range(0,120):                # iterate over the columns
      for j in range(0,320):              # and convert 255 vals to 0 to match logic in Joystick.c and invertColormap option
         data.append(0 if im_px[j,i] == 255 else 1)

    str_out = "#include <stdint.h>\n#include <avr/pgmspace.h>\n\nconst uint8_t image_data[0x12c2] PROGMEM = {"
    options = hex(2**0 * opposite + 2**1 * cautious) # Adding printing options to the code file
    str_out += options + ", "
    for i in range(0, 4800):            # 320 x 120 / 8
       val = 0

       for j in range(0, 8):
          val |= data[(i * 8) + j] << j

       if (invertColormap):
          val = ~val & 0xFF
       else:
          val = val & 0xFF

       str_out += hex(val) + ", "         # append hexidecimal bytes
                                          # to the output .c array of bytes
    str_out += "0x0};\n"                  # End byte is always 0x0

    with open('splat_image.c', 'w') as f:       # save output into image.c
      f.write(str_out)

    if (invertColormap):
       print("{} converted with inverted colormap and saved to splat_image.c".format(filename))
    else:
       print("{} converted with original colormap and saved to splat_image.c".format(filename))
    print(f"Black Pixel Count: {sum(data)}")
    print(f"White Pixel Count: {38400 - sum(data)}")

    if sum(data) > 38400/2 and opposite != True:
      print(f"It's {round((sum(data)/(38400 - sum(data)) - 1) * 100, 2)}% more optimal to print in opposite mode. Try re-printing with \"-o\" as an option?")

def usage():
  print("To convert to splat_image.c: png2c.py <yourImage.png>")
  print("To convert to an inverted splat_image.c: png2c.py -i <yourImage.png>")
  print("To preview bilevel splat_image: png2c.py -p <yourImage.png>")
  print("To save bilevel splat_image: png2c.py -s <yourImage.png>")
  print("-=CONFIGS=-")
  print("To print in cautious mode: png2c.py -c <yourImage.png>")
  print("To print in optimal mode: png2c.py -o <yourImage.png>")

if __name__ == "__main__":
  if len(sys.argv[1:]) == 0:
    usage()
    sys.exit
  else:
    main(sys.argv[1:])
