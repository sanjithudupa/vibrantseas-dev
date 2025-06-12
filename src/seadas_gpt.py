import subprocess
import os
import json
import sys

if len(sys.argv) < 3:
    print("Usage: python3 seadas_gpt.py <seadas_products_nc> <output_folder>")
    sys.exit(1)


GPT_LOCATION = '/usr/local/seadas-7.5.3/bin/gpt.sh'
COLOR_PALLETE_LOCATION = '/mit/color_palletes'

seadas_products_nc = sys.argv[1]

output_folder = sys.argv[2]
os.makedirs(output_folder, exist_ok=True)

images = json.load(open('/mit/scripts/image_attributes.json'))

# /usr/local/seadas-7.5.3/bin/gpt.sh WriteImage -Ssource=/mit/seadas_products.nc -PcolourScaleMax=0.742 -PcolourScaleMin=0.103 -PcpdFilePath=/mit/gpt/diatoms.cpd -PfilePath=/mit/output.tif -PformatName=tif -PsourceBandName=diatoms_hirata
def create_image(band, color_pallete, min, max, output_filename):
    cmd = [
        GPT_LOCATION,
        'WriteImage',
        f'-Ssource={seadas_products_nc}',
        f'-PcolourScaleMax={max}',
        f'-PcolourScaleMin={min}',
        f'-PcpdFilePath={COLOR_PALLETE_LOCATION}/{color_pallete}',
        f'-PfilePath={os.path.join(output_folder, output_filename)}',
        f'-PformatName=tiff',
        f'-PsourceBandName={band}'
    ]
    
    subprocess.run(cmd, check=True)

def main():
    for image in images:
        print('starting ', image)
        band = images[image]['band']
        color_pallete = images[image]['color_pallete']
        min = images[image]['min']
        max = images[image]['max']
        output_filename = image
        create_image(band, color_pallete, min, max, output_filename)
        print('finished ', image)
    print('done')

if __name__ == '__main__':
    main()