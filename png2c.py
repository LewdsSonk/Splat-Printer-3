#!/bin/python

import sys, os, getopt
from PIL import Image

def main(argv):
  long_opt_list = ["help",
                   "preview",
                   "savebilevel",
                   "invertcmap",
                   "nodither",
                   "cautious",
                   "opposite",
                   "slowmode",
                   "endsave",
                   "vertical"]
  opts, args = getopt.getopt(argv, "hpbcosein", long_opt_list)
  option_list = {'previewBilevel': False, 
                 'saveBilevel': False,
                 'invertColormap': False,
                 'no_dither': False,
                 'cautious': False,
                 'opposite': False,
                 'slowmode': False,
                 'endsave': False,
                 'vertical': False}

  for opt, arg in opts:
    if opt in ['-h', '--help']:
      usage()
      sys.exit()
    elif opt in ['-p', '--preview']:
      option_list['previewBilevel'] = True
    elif opt in ['-b', '--savebilevel']:
      option_list['saveBilevel'] = True
    elif opt in ['-n', '--nodither']:
      option_list['no_dither'] = True
    elif opt in ['-c', '--cautious']:
      option_list['cautious'] = True
    elif opt in ['-o', '--opposite']:
      option_list['opposite'] = True
    elif opt in ['-s', '--slowmode']:
      option_list['slowmode'] = True
    elif opt in ['-e', '--endsave']:
      option_list['endsave'] = True
    elif opt in ['-i', '--invertcmap']:
      option_list['invertColormap'] = True
    elif opt in ['-v', '--vertical']:
      option_list['vertical'] = True

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
  if option_list['no_dither']:
    im = im.convert("1", dither = None) # this also adds dithering if wanted
  else:
    im = im.convert("1", dither = Image.Dither.FLOYDSTEINBERG)

  if option_list['previewBilevel']:
    print(f"Previewing {filename_direct}!")
    im.show()
  
  if option_list['saveBilevel']:
    im.save(f"preview-images\\bilevel_{filename_direct}")
    print("Bilevel preview version of " + filename_direct + " saved as bilevel_" + filename_direct)
  
  if not (option_list['previewBilevel'] or option_list['saveBilevel']):
    im_px = im.load()
    data = []
    for i in range(0,120):                # iterate over the columns
      for j in range(0,320):              # and convert 255 vals to 0 to match logic in Joystick.c and invertColormap option
         data.append(0 if im_px[j,i] == 255 else 1)

    str_out = "#include <stdint.h>\n#include <avr/pgmspace.h>\n\nconst uint8_t image_data[0x12c2] PROGMEM = {"
    options = hex(2**0 * option_list['cautious'] # Adding printing options to the code file
                  + 2**1 * option_list['opposite'] 
                  + 2**2 * option_list['slowmode'] 
                  + 2**3 * option_list['endsave'] 
                  + 2**4 * option_list['vertical'])
    str_out += options + ", "
    for i in range(0, 4800): # 320 x 120 / 8
       val = 0

       for j in range(0, 8):
          val |= data[(i * 8) + j] << j

       if (option_list['invertColormap']):
          val = ~val & 0xFF
       else:
          val = val & 0xFF

       str_out += hex(val) + ", "         # append hexidecimal bytes
                                          # to the output .c array of bytes
    str_out += "0x0};\n"                  # End byte is always 0x0

    with open('splat_image.c', 'w') as f:       # save output into image.c
      f.write(str_out)

    if (option_list['invertColormap']):
       print("{} converted with inverted colormap and saved to splat_image.c".format(filename))
    else:
       print("{} converted with original colormap and saved to splat_image.c".format(filename))
    print(f"Black Pixel Count: {sum(data)}")
    print(f"White Pixel Count: {38400 - sum(data)}")
    print(f"\n-= Options chosen =-")
    for opt in option_list:
        print(f"{opt}: {option_list[opt]}")

    if sum(data) > 38400/2 and option_list['opposite'] != True:
      print(f"There's {round((sum(data)/(38400 - sum(data)) - 1) * 100, 2)}% less inputs to print in opposite mode. Try re-printing with \"-o\" as an option?")

def usage():
  print("To convert to splat_image.c: png2c.py [-options] <yourImage.png>")
  print("\n--help [-h]: Show this help list")
  print("--invertcmap [-i]: Convert to an inverted splat_image.c")
  print("--preview [-p]: Preview bilevel splat_image.c")
  print("--savebilevel [-b]: Save bilevel splat_image.c")
  print("\n-=CONFIGS=-")
  print("--cautious [-c]: To print in cautious mode")
  print("  * Cautious mode adds extra, 3 blank inputs to each line print, that way, any dropped inputs in a line (as long as it's under 3 inputs) won't affect following lines.")
  print("--opposite [-l]: To print in opposite mode")
  print("  * Sometimes, printing by instead erasing a black image will result in less inputs, which can lead to less dropped inputs, and as such, less mistakes.")
  print("--slowmode [-s]: To print in slowmode")
  print("  * Slowmode separates moving and inking into 2 separate actions. This doubles the time spent printing, but makes it extremely unlikely for there to be dropped inputs. Recommended for complex images.")
  print("--endsave [-e]: To have Splatoon 3 save and close the image after printing it.")
  print("  * Since saving at the end overwrites whatever you had before, sometimes it's not ideal to have the image save on top. If you don't mind that, though, enable this option.")
  print("--vertical [-v]: To print in vertical mode. This mode basically just prints column per column rather than line per line. Due to having more \"turns\", it might result in a slightly longer time, but any printing mistakes (especially with cautious mode on) will be less significant.")

if __name__ == "__main__":
  if len(sys.argv[1:]) == 0:
    usage()
    sys.exit
  else:
    main(sys.argv[1:])
