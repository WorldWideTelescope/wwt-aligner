# Copyright 2020-2021 the .NET Foundation
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
from PIL import Image as pil_image
from pyavm import AVM
import sep
import subprocess
from toasty.builder import Builder
from toasty.image import ImageLoader


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
    output_path = None,
    tile_path = None,
    work_dir = '',
    anet_bin_prefix = '',
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

    print('Finding sources in', fits_path, '...')

    bkg = sep.Background(data)
    #print('SEP background level:', bkg.globalback)
    #print('SEP background rms:', bkg.globalrms)

    bkg.subfrom(data)
    objects = sep.extract(data, 3, err=bkg.globalrms)
    #print('SEP object count:', len(objects))

    coords = wcs.pixel_to_world(objects['x'], objects['y'])
    tbl = Table([coords.ra.deg, coords.dec.deg, objects['flux']], names=('RA', 'DEC', 'FLUX'))

    objects_fits = os.path.join(work_dir, 'objects.fits')
    tbl.write(objects_fits, format='fits', overwrite=True)

    # Generate the Astrometry.Net index

    index_fits = os.path.join(work_dir, 'index.fits')

    argv = [
        anet_bin_prefix + 'build-astrometry-index',
        '-i', objects_fits,
        '-o', index_fits,
        '-E',  # objects table is much less than all-sky
        '-f',  # our sort column is flux-like, not mag-like
        '-S', 'FLUX',
        '-P', str(image_size_to_anet_preset(large_scale.deg))
    ]

    index_log = os.path.join(work_dir, 'build-index.log')
    print('Generating Astrometry.Net index ...')

    with open(index_log, 'wb') as log:
        subprocess.check_call(
            argv,
            stdout = log,
            stderr = subprocess.STDOUT,
            shell = False,
        )

    # Write out config file

    cfg_path = os.path.join(work_dir, 'aligner.cfg')

    with open(cfg_path, 'wt') as f:
        print('add_path', work_dir, file=f)
        print('inparallel', file=f)
        print('index', index_fits, file=f)

    # Solve our input image
    #
    # XXX we can't use the "WCS" file super conveniently because it doesn't
    # contain NAXIS data. It would be nice if we could because it's small and we
    # could avoid rewriting the full image data. XXXX: use IMAGEW, IMAGEH.

    wcs_file = os.path.join(work_dir, 'solved.fits')

    # https://manpages.debian.org/testing/astrometry.net/solve-field.1.en.html
    argv = [
        anet_bin_prefix + 'solve-field',
        '--config', cfg_path,
        '--scale-units', 'arcminwidth',
        '--scale-low', str(width.arcmin / 2),
        '--scale-high', str(width.arcmin * 2),
        '--cpulimit', '600',  # seconds
        '--dir', work_dir,
        '-N', wcs_file,
        '--no-plots',
        '--no-tweak',
        '--downsample', '2',
        rgb_path,
    ]

    solve_log = os.path.join(work_dir, 'solve-field.log')
    print('Launching Astrometry.Net solver ...')

    with open(solve_log, 'wb') as log:
        subprocess.check_call(
            argv,
            stdout = log,
            stderr = subprocess.STDOUT,
            shell = False,
        )

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
    #
    # pyavm can't convert image formats, so if we've been asked to emit a tagged
    # imagine in a format different than the image format, we need to do that
    # conversion manually. We're not in a great position to be clever so we
    # assess "format" from filename extensions.

    in_name_pieces = os.path.splitext(os.path.basename(rgb_path))

    if output_path is None:
        output_path = in_name_pieces[0] + '_tagged' + in_name_pieces[1]

    input_ext = in_name_pieces[1].lower()
    output_ext = os.path.splitext(output_path)[1].lower()

    if input_ext != output_ext:
        print('Converting input image to create:', output_path)
        img.save(output_path)

        print('Adding AVM tags to:', output_path)
        avm.embed(output_path, output_path)
    else:
        print('Writing AVM-tagged image to:', output_path)
        avm.embed(rgb_path, output_path)

    # Tile it for WWT, if requested

    if tile_path is not None:
        from toasty.merge import averaging_merger, cascade_images
        from toasty.pyramid import PyramidIO

        print('Creating base layer of WWT tiling ...')

        pio = PyramidIO(tile_path, default_format=img.default_format)
        builder = Builder(pio)
        builder.make_thumbnail_from_other(img)
        builder.tile_base_as_study(img, cli_progress=True)
        builder.apply_wcs_info(wcs, img.width, img.height)
        builder.set_name(in_name_pieces[0])
        builder.write_index_rel_wtml()

        print('Cascading tiles ...')
        cascade_images(
            pio,
            builder.imgset.tile_levels,
            averaging_merger,
            cli_progress=True
        )
