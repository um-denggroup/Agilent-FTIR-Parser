# Agilent-FTIR-Parser
Parse and Convert Agilent (formerly Varian?) Resolutions Pro *.bsp multi-spectrum files

# Installation

*I am using Python 3.10.12 on Kubuntu. I have used this to parse files from the Agilent 670 FT-IR microscope controlled with Resolutions Pro version 5.2.0. You can probably use other versions and operating systems, but I have not tested them.*

1. Clone the repository `git clone https://github.com/um-denggroup/Agilent-FTIR-Parser.git`
2. Enter the repository `cd Agilent-FTIR-Parser`
3. *Optional:* I recommend using virtual environment to keep these packages isolated from the rest of your system, but you do not have to. 
    - To create the virtual environment, you can run `python3 -m venv agilent`.
    - You will then need to activate by running `. agilent/bin/activate`.
4. Install the packages from requirements.txt `pip install -r requirements.txt`
5. Create the output directory `mkdir out`

# Usage

You should now be able to run `python3 extract-spectra.py YOUR_AGILENT_FILE.bsp`, which will extract the spectra stored in the file to CSV, JSON, and JPEG files. These will have `filename={index}_{name}` according to the table of spectra shown in Resolutions Pro.

- There will be two CSV files generated. 
    1. The first is the calculated spectrum, with Wavenumber vs either raw Response (Voltage?) values for backgrounds or %Transmission|%Reflection relative to the background for sample scans.
    2. The second is the raw interferogram data (Optical Retardation (cm) vs Volts). Presumably, you could do the Fourier transform on this yourself to obtain the data from 1., though I haven't tried it.
- The JSON file contains all the metadata for the spectrum that was stored in the sub-file of the .bsp file for the spectrum. E.g. the parameters used to take the scan. Some of these seem to be special values for the software (e.g. `"DisplayDirection": 20301`), though most are human readable (and even the software itself wrote it out to the CSV with the same sort of value and not converted to a string.
- The JPEG seems to be the image from the camera when the spectrum was taken. As far as I know there will only be one, but I'm not certain, so the script adds a `.{i}` before `.jpg` according to the image index of that spectrum.


# More Information

* The .bsp file itself seems to be an OLE2 files (also called Structured Storage, Compound File Binary Format or Compound Document File Format, and used in Microsoft Office 97-2003 documents, as well as other software). It acts somewhat like a zip file, containing multiple internal streams/documents/files.
* A spectrum document from the bsp file seems to be somewhat like a binary, untyped version of JSON. The overall structure seems to be somewhat like a tree (with top level Data, Parms, and Properties having other info inside themselves, with sequences sometimes having labels (e.g. at the top level) and sometimes not (e.g. the Data > 1.00 'object' has no names for it's values, though it has four of them. Fortunately, the sizes of everything in the file seem to be written into the file itself, and is not only inside the software's code. This allows reading the data out of the file even if we don't always know what it means (like the DisplayDirection).
* Since the Properties all have labels, so it's just a few values from Parms that are completely unknown at this point.
