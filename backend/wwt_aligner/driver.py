# Copyright 2020 the .NET Foundation
# Licensed under the MIT License

"""
Main tool driver.
"""

__all__ = ['go']

from astropy.io import fits
from astropy.table import Table
from astropy.wcs import WCS
import math
import os.path
from pyavm import AVM
import sep
import subprocess
from toasty.builder import Builder
from toasty.image import ImageLoader
from toasty.merge import averaging_merger, cascade_images
from toasty.pyramid import PyramidIO


def image_size_to_anet_preset(size_deg):
    """
    Get an astrometry.net "preset" size from an image size. Docs say:

    0 => ~6 arcmin
    2 => ~12 arcmin
    4 => ~24 arcmin

    etc.
    """
    return 6 + 2 * math.log2(size_deg)


def go(
    fits_path = None,
    rgb_path = None,
):
    """
    Do the whole thing.
    """

    # Check our FITS image and get some basic quantities. We need
    # to read in the data to sourcefind with SEP.

    with fits.open(fits_path) as hdul:
        hdu = hdul[0]
        wcs = WCS(hdu)
        data = hdu.data
        height, width = data.shape[-2:]

    data = data.byteswap(inplace=True).newbyteorder()

    midx = width // 2
    midy = height // 2
    coords = wcs.pixel_to_world(
        [midx, midx + 1, 0, width, 0, width],
        [midy, midy + 1, 0, height, midy, midy],
    )

    small_scale = coords[0].separation(coords[1])
    #print('small scale:', small_scale)
    large_scale = coords[2].separation(coords[3])
    #print('large scale:', large_scale)
    width = coords[4].separation(coords[5])

    # Use SEP to find sources

    bkg = sep.Background(data)
    print('SEP background level:', bkg.globalback)
    print('SEP background rms:', bkg.globalrms)

    bkg.subfrom(data)
    objects = sep.extract(data, 3, err=bkg.globalrms)
    print('SEP object count:', len(objects))
    print('columns:', objects.dtype.names)
    print('first object:', objects[0])

    coords = wcs.pixel_to_world(objects['x'], objects['y'])
    tbl = Table([coords.ra.deg, coords.dec.deg, objects['flux']], names=('RA', 'DEC', 'FLUX'))

    print('XXX hardcoded object table name')
    objects_fits = 'objects.fits'
    tbl.write(objects_fits, format='fits', overwrite=True)

    # Generate the Astrometry.Net index

    index_fits = 'index.fits'
    print('XXX hardcoded index FITS table name')

    argv = [
        '/a/wwt/aligner/astrometry.net/solver/build-astrometry-index', # XXXX
        '-i', objects_fits,
        '-o', index_fits,
        '-E',  # objects table is much less than all-sky
        '-f',  # our sort column is flux-like, not mag-like
        '-S', 'FLUX',
        '-P', str(image_size_to_anet_preset(large_scale.deg))
    ]
    subprocess.check_call(argv, shell=False)

    # Write out config file

    index_dir = os.getcwd()
    cfg_path = 'aligner.cfg'
    print('XXX hardcoded config file')

    with open(cfg_path, 'wt') as f:
        print('add_path', index_dir, file=f)
        print('inparallel', file=f)
        print('index', index_fits, file=f)

    # Solve our input image
    #
    # XXX we can't use the "WCS" file super conveniently because it doesn't
    # contain NAXIS data. It would be nice if we could because it's small and we
    # could avoid rewriting the full image data. XXXX: use IMAGEW, IMAGEH.

    wcs_file = 'solved.fits'

    argv = [
        '/a/wwt/aligner/astrometry.net/solver/solve-field', # XXXX
        '--config', cfg_path,
        '--scale-units', 'arcminwidth',
        '--scale-low', str(width.arcmin / 2),
        '--scale-high', str(width.arcmin * 2),
        '-N', wcs_file,
        '--no-plots',
        '--no-tweak',
        rgb_path,
    ]
    subprocess.check_call(argv, shell=False)

    # Convert solution to AVM, with hardcoded parity
    # inversion

    img = ImageLoader().load_path(rgb_path)

    with fits.open(wcs_file) as hdul:
        header = hdul[0].header
        wcs = WCS(header)

    hdwork = wcs.to_header()
    hdwork['CRPIX2'] = img.height + 1 - hdwork['CRPIX2']
    hdwork['PC1_2'] *= -1
    hdwork['PC2_2'] *= -1
    wcs = WCS(hdwork)
    avm = AVM.from_wcs(wcs)

    # Apply AVM

    in_name_pieces = os.path.splitext(os.path.basename(rgb_path))
    out_name = in_name_pieces[0] + '_tagged' + in_name_pieces[1]
    print('Writing to:', out_name)
    avm.embed(rgb_path, out_name)

    # Basic toasty tiling

    print('basic tiling ...')
    tile_dir = in_name_pieces[0] + '_tiled'

    pio = PyramidIO(tile_dir, default_format=img.default_format)
    builder = Builder(pio)
    builder.make_thumbnail_from_other(img)
    builder.tile_base_as_study(img, cli_progress=True)
    builder.apply_wcs_info(wcs, img.width, img.height)
    builder.set_name(in_name_pieces[0])
    builder.write_index_rel_wtml()

    print('cascading ...')
    cascade_images(
        pio,
        builder.imgset.tile_levels,
        averaging_merger,
        cli_progress=True
    )

    print()
    print(f'try:    wwtdatatool preview {tile_dir}/index_rel.wtml')
