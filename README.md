# unbreak
Fix the GRBL toolpath files that Fusion 360 generates

Running it be like:
unbreak ~/nc-files/

It then creates a bunch of <filename>-fm.nc files without long comment lines, a safe start Z and some actual G0 travel moves

The safe Z is set to 5mm. I can make it an arg if there's greater than zero interest.
