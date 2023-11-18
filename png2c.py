#!/bin/python

import sys, os, getopt
import re
import tqdm
import math
from PIL import Image
from generate_route import *
from typing import Union


def main(argv):
  fix_values = [0, 0]
  fix_value = []
  long_opt_list = ["help",
                   "preview",
                   "savebilevel",
                   "invertcmap",
                   "nodither",
                   "cautious",
                   "optimal",
                   "slowmode",
                   "endsave",
                   "vertical",
                   "fix="]
  opts, args = getopt.getopt(argv, "hpbcoseinvf:", long_opt_list)
  option_list = {'previewBilevel': False, 
                 'saveBilevel': False,
                 'invertColormap': False,
                 'no_dither': False,
                 'cautious': False,
                 'optimal': False,
                 'slowmode': False,
                 'endsave': False,
                 'vertical': False,
                 'fix': False}
  #print(opts, args)
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
    elif opt in ['-o', '--optimal']:
      option_list['optimal'] = True
    elif opt in ['-s', '--slowmode']:
      option_list['slowmode'] = True
    elif opt in ['-e', '--endsave']:
      option_list['endsave'] = True
    elif opt in ['-i', '--invertcmap']:
      option_list['invertColormap'] = True
    elif opt in ['-v', '--vertical']:
      option_list['vertical'] = True
    elif opt in ['-f', '--fix']:
      all_to_fix = []
      arglist = arg.split(',')
      option_list['fix'] = True
      for argument in arglist:
        fix_value = re.search('(^[0-9]{1,3}-[0-9]{1,3}\n{0,1}$|^[0-9]{1,3}\n{0,1}$)', argument)
        if fix_value == None:
          print("A fix value was invalid! Ignoring fix option!")
          option_list['fix'] = False
          break
        else:
          fix_values = list(map(lambda x: int(x), fix_value.group().split('-')))
          if option_list['vertical'] == False and option_list['fix'] == True:
            if fix_values[0] > 120:
              fix_values[0] = 120
          if fix_values[0] > 320:
            fix_values[0] = 320
          if fix_values[0] < 1:
            fix_values[0] = 1

          all_to_fix.append(fix_values[0])

          if len(fix_values) > 1:
            if option_list['vertical'] == False and option_list['fix'] == True:
              if fix_values[1] > 120:
                fix_values[1] = 120
            if fix_values[1] > 320:
              fix_values[1] = 320
            if fix_values[1] < 1:
              fix_values[1] = 1

            if fix_values[0] > fix_values[1]:
              fix_values[0], fix_values[1] = fix_values[1], fix_values[0]
          
            all_to_fix.extend(list(range(fix_values[0] + 1, fix_values[1] + 1)))
      all_to_fix = list(sorted(set(all_to_fix)))

  all_to_fix = []
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

  if option_list['optimal']:
    invert = False
    if np.sum(np.array(im)) < 38400/2:
      invert = True
    if invert == True:
      divided_image = divide_image(np.array(im))
    else:
      divided_image = divide_image(1 - np.array(im))
    visit_list: list[Union[ResetPosition, np.ndarray]] = []
    for item in tqdm.tqdm(divided_image, desc="Blocks to be visited"):
        visit_list += generate_block_visit(item[1], np.array(item[0]))
        if len(visit_list) == 0 or isinstance(visit_list[-1], ResetPosition):
            continue
        visit_list.append(find_nearest_reset_position(visit_list[-1]))
    bin_command_list = generate_order(visit_list)
    summarize_difficulties(im, bin_command_list) #check if suboptimal, then remove optimal if so

  if not (option_list['previewBilevel'] or option_list['saveBilevel']):
    im_px = im.load()
    data = []
    for i in range(0, 120):                # iterate over the columns
      for j in range(0, 320):              # and convert 255 vals to 0 to match logic in Joystick.c and invertColormap option
         data.append(0 if im_px[j, i] == 255 else 1)

    bytecount = 1 #Starts at 1 since the last byte is always 0x0.
    str_out = "#include <stdint.h>\n#include <avr/pgmspace.h>\n\nconst uint8_t image_data[] PROGMEM = {"
    
    options = hex(  2**0 * option_list['cautious'] # Adding printing options to the code file
                  + 2**1 * option_list['optimal'] 
                  + 2**2 * option_list['slowmode'] 
                  + 2**3 * option_list['endsave'] 
                  + 2**4 * option_list['vertical']
                  + 2**5 * option_list['fix'])

    str_out += options + ", "
    bytecount += 1

    fix_data = []
    for i in range(1, 321):
      if i in all_to_fix:
        fix_data.append(1)
      else:
        fix_data.append(0)

    for i in range(40):
      bytecount += 1
      val = 0
      for j in range(0, 8):
          val |= fix_data[(i * 8) + j] << j
      str_out += hex(val) + ", "

    for i in range(0, 4800): # 320 x 120 / 8
      bytecount += 1
      val = 0

      for j in range(0, 8):
        val |= data[(i * 8) + j] << j

      if (option_list['invertColormap']):
        val = ~val & 0xFF
      else:
        val = val & 0xFF

      str_out += hex(val) + ", "          # append hexidecimal bytes
                                          # to the output .c array of bytes

    if option_list['optimal']:
      bytecount += 2 #To define the length of bin_command_list
      if len(bin_command_list) > 256:
        optimal_size_part1 = hex(len(bin_command_list))[:4]
        optimal_size_part2 = "0x" + hex(len(bin_command_list))[4:] #Divide hex into 2 parts; You attach them directly, so for example, 0x17 0xff => 0x17ff
        str_out += optimal_size_part1 + ", " + optimal_size_part2 + ", "
      else:
        str_out += hex(len(bin_command_list)) + ", " + hex(0) + ", "

      for i in range(0, len(bin_command_list), 4): #Put 4 commands into one hex value.
        bytecount += 1
        if i + 3 <= len(bin_command_list):
          str_out += hex(bin_command_list[i] + bin_command_list[i + 1]*2**2 + bin_command_list[i + 2]*2**4 + bin_command_list[i + 3]*2**6)
        else:
          final_command_sum = bin_command_list[i]
          if i + 1 < len(bin_command_list):
            final_command_sum += bin_command_list[i + 1]*2**2
          if i + 2 < len(bin_command_list):
            final_command_sum += bin_command_list[i + 2]*2**4
          str_out += hex(final_command_sum)
        str_out += ", "

    str_out += "0x0};\n"                  # End byte is always 0x0

    str_out = str_out[:72] + hex(bytecount) + str_out[72:] #Inserting the total byte count to allocate for PROGMEM

    with open('splat_image.c', 'w') as f:       # save output into image.c
      f.write(str_out)

    if (option_list['invertColormap']):
       print("{} converted with inverted colormap and saved to splat_image.c!".format(filename))
    else:
       print("{} converted with original colormap and saved to splat_image.c!".format(filename))
    print(f"Black Pixel Count: {sum(data)}")
    print(f"White Pixel Count: {38400 - sum(data)}")
    print(f"\n-= Options chosen =-")
    for opt in option_list:
        print(f"{opt}: {option_list[opt]}")

    if option_list["fix"] == True:
      fix_column_or_line = "line"
      if option_list["vertical"] == True:
        fix_column_or_line = "column"
      if len(all_to_fix) == 1:
        print(f"\nFix mode will try to fix {fix_column_or_line} {all_to_fix}!")
      else:
        print(f"\nFix mode will try to fix {fix_column_or_line}s {all_to_fix}!")

    #if sum(data) > 38400/2 and option_list['opposite'] != True:
      #print(f"\nThere's {round((sum(data)/(38400 - sum(data)) - 1) * 100, 2)}% less inputs to print in opposite mode. Try re-printing with \"-o\" as an option?")

def usage():
  print("To convert to splat_image.c: png2c.py [-options] <yourImage.png>")
  print("\n--help [-h]: Show this help list")
  print("--invertcmap [-i]: Convert to an inverted splat_image.c")
  print("--preview [-p]: Preview bilevel splat_image.c")
  print("--savebilevel [-b]: Save bilevel splat_image.c")
  print("\n-=CONFIGS=-")
  print("--cautious [-c]: To print in cautious mode")
  print("  * Cautious mode adds extra, 3 blank inputs to each line print, that way, any dropped inputs in a line")
  print("    (as long as it's under 3 inputs) won't affect following lines.")
  print("")
  print("--opposite [-o]: To print in opposite mode")
  print("  * Sometimes, printing by instead erasing a black image will result in less inputs, which can lead to less dropped inputs,")
  print("    and as such, less mistakes.")
  print("")
  print("--slowmode [-s]: To print in slowmode")
  print("  * Slowmode separates moving and inking into 2 separate actions. This doubles the time spent printing,")
  print("    but makes it extremely unlikely for there to be dropped inputs. Heavily recommended for complex images.")
  print("")
  print("--endsave [-e]: To have Splatoon 3 save and close the image after printing it.")
  print("  * Since saving at the end overwrites whatever you had before, sometimes it's not ideal to have the image save on top.")
  print("    If you don't mind that, though, enable this option.")
  print("")
  print("--vertical [-v]: To print in vertical mode")
  print("  * This mode basically just prints column per column rather than line per line. Due to having more \"turns\",")
  print("    it might result in a slightly longer time, but any printing mistakes (especially with cautious mode on) will be less significant.")
  print("")
  print("--fix [-f] X,X-Y,...,X: To print in fix mode, based on the X and Y values.")
  print("  * Fix mode will only draw lines/columns from X to Y. If Y is left blank, it will only fix line X.")
  print("     * Example: 12 will choose [12]. 12-15 will choose [12, 13, 14, 15].")
  print("  * Putting values between commas allows you to choose multiple, separated lines/columns. Order does not matter.")
  print("     * Example: 2,7-10,3 will choose [2, 3, 7, 8, 9, 10].")
  print("  * Fix mode *does not work with \"--opposite\"*; it will skip making the image fully black.")
  print("  * Heavily recommended to use \"--slowmode\" with fix mode, to guarantee the fix will go through.")
  print("  * If the values are improper (less than 1, greater than 120 for horizontal printing and 320 for vertical printing,")
  print("    or the left value is bigger than the right value), it will try to fix the values automatically. Otherwise,")
  print("    it will ignore fix mode (e.g. negative values, letters, improper syntax).")

if __name__ == "__main__":
  if len(sys.argv[1:]) == 0:
    usage()
    sys.exit
  else:
    main(sys.argv[1:])