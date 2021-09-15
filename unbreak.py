import os
from glob import glob
import re
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--path", required=False, default='/home/pdavies/models/tv-remote/', help="The path to .nc files which need conversion")
args = parser.parse_args()

lines_to_remove = ['(When using Fusion 360 for Personal Use, the feedrate of)',
                   '(rapid moves is reduced to match the feedrate of cutting)',
                   '(moves, which can increase machining time. Unrestricted rapid)',
                   '(moves are available with a Fusion 360 Subscription.)']

nc_folder = args.path
matching_filenames = glob(nc_folder + '*.nc')
# matching_filenames = glob(nc_folder + 'detail.nc')
fp_pattern = '[-+]?(\\d+(\\.\\d*)?|\\.\\d+)([eE][-+]?\\d+)?'


def isXY(line_str):
    return re.match('X%s Y%s' % (fp_pattern, fp_pattern), line_str)


WAITING_FOR_FIRST_Z = 1
WAITING_FOR_MOVE_LINE = 2
WAITING_FOR_FINAL_Z = 3
WAITING_FOR_POSITIVE_Za = 4
WAITING_FOR_G0 = 5
WAITING_FOR_POSITIVE_Zb = 6

# print(re.match('Z%s' % fp_pattern, 'Z-6.5 F333.3'))
# print(re.match('Z%s ' % fp_pattern, 'Z-6.5'))
# exit(2)

for matching_filename in matching_filenames:
    if '-fm.nc' not in matching_filename:
        with open(matching_filename, 'r') as infile:
            parts = os.path.split(matching_filename)
            fname = parts[1]
            basename = fname[:-len('.nc')]
            lines = infile.readlines()
            xylines = 0
            # print(len(lines), 'lines in file')
            with open(nc_folder + str(basename) + '-fm.nc', 'w') as outfile:
                xzx_state = WAITING_FOR_FIRST_Z
                zmove_state = WAITING_FOR_POSITIVE_Za
                xyline = None
                second_zs = 0
                za_line = None
                g0_line = None
                line_num = 0
                last_line = ''
                for line in lines:
                    line_num += 1
                    unterminated_line = line[:-1]
                    if any(line_to_remove in line for line_to_remove in lines_to_remove):
                        # print('One of those comment lines')
                        continue

                    if zmove_state == WAITING_FOR_POSITIVE_Za:
                        if re.match('Z%s ' % fp_pattern, unterminated_line):
                            try:
                                zval = float(unterminated_line[1:])
                                if zval > 0.0:
                                    print('Got first +Z')
                                    # Save this line
                                    za_line = unterminated_line
                                    zmove_state = WAITING_FOR_G0
                            except ValueError:
                                # print('Failed to parse line %s:%d: %s' % (matching_filename, line_num, unterminated_line))
                                pass
                    elif zmove_state == WAITING_FOR_G0:
                        if isXY(unterminated_line):
                            # save this line
                            print('save XY line')
                            g0_line = unterminated_line
                            zmove_state = WAITING_FOR_POSITIVE_Zb
                        else:
                            zmove_state = WAITING_FOR_POSITIVE_Za
                    elif zmove_state == WAITING_FOR_POSITIVE_Zb:
                        if re.match('Z%s' % fp_pattern, unterminated_line):
                            zval = float(unterminated_line[1:])
                            if zval < 0.0:
                                print('Got second +Z')
                                # write first Z line,
                                # rapid move G0,
                                # second Z line
                                # outfile.write('### %s\n' % za_line)
                                outfile.write('(%s)\n' % g0_line)
                                # outfile.write('### %s\n' % unterminated_line)
                                second_zs += 1
                                zmove_state = WAITING_FOR_POSITIVE_Za
                            else:
                                zmove_state = WAITING_FOR_POSITIVE_Za
                        else:
                            zmove_state = WAITING_FOR_POSITIVE_Za

                    if xzx_state == WAITING_FOR_FIRST_Z:
                        if line.startswith('Z') and re.match('Z%s' % fp_pattern, unterminated_line):
                            # still output this line
                            print(line)
                            outfile.write(line)
                            xzx_state = WAITING_FOR_MOVE_LINE
                        else:
                            outfile.write(line)
                            if line.startswith('G54'):
                                # Safe retract height
                                outfile.write('G0 Z5    ;Safe retract height\n')
                    elif xzx_state == WAITING_FOR_MOVE_LINE:
                        if isXY(unterminated_line):
                            # outfile.write('(Got XY line)\n')
                            xyline = line
                            xylines += 1
                            xzx_state = WAITING_FOR_FINAL_Z
                        else:
                            # outfile.write('(Got something else)\n')
                            outfile.write(line)
                            modify_zxz_lines = WAITING_FOR_FIRST_Z

                    elif xzx_state == WAITING_FOR_FINAL_Z:
                        if line.startswith('Z') and re.match('Z%s' % fp_pattern, unterminated_line):
                            # Write out the saved XY line, but modified to a rapid move
                            outfile.write('G0 ' + xyline)
                            # outfile.write('(XY line placed)\n')
                            outfile.write(line)
                            # outfile.write('(Final Z placed)\n')
                        else:
                            # outfile.write('(Failed to get final Z with %s)\n' % unterminated_line)
                            outfile.write(xyline)
                            outfile.write(line)
                        xzx_state = WAITING_FOR_FIRST_Z
                    last_line = line
                print(basename, xylines, 'xy lines')
                print(second_zs, 'G0 rewrites')
