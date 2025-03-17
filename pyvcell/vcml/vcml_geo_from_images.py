# write a script using imageio to read a directory of image files into a 3D image and return it as a numpy array
# the files should be in lexicographic order.
import tarfile
from pathlib import Path

import imageio
import numpy as np

import pyvcell.vcml as vc
from pyvcell.sim_results.var_types import NDArray3Du8


def read_images_to_volume(image_path: Path) -> NDArray3Du8:
    if not image_path.is_dir():
        raise ValueError(f"{image_path} is not a directory")
    image_files = sorted(image_path.glob("*.png"))
    images = [imageio.v3.imread(str(f)) for f in image_files]
    return np.stack(images)


# def ndarray_to_vcml_image(ndarray_3d_u8: NDArray3Du8, name: str) -> vc.Image:
#     size: tuple[int, int, int] = ndarray_3d_u8.shape[0], ndarray_3d_u8.shape[1], ndarray_3d_u8.shape[2]
#
#     unique_values = np.unique(ndarray_3d_u8)
#     pixel_classes: list[vc.PixelClass] = []
#     for value in unique_values:
#         pixel_class = vc.PixelClass(name=f"class_{str(value)}", pixel_value=value)
#         pixel_classes.append(pixel_class)
#
#     raw_pixels: bytes = ndarray_3d_u8.flatten().tobytes()
#     compressed_bytes: bytes = zlib.compress(raw_pixels)
#     return vc.Image(name=name, size=size,
#                     compressed_size=len(raw_pixels), compressed_content=compressed_bytes.hex(),
#                     pixel_classes=pixel_classes)


if __name__ == "__main__":
    geometry_data_dir = Path(__file__).parent.parent.parent / "examples" / "geometry"
    archive_file = geometry_data_dir / "bunny.tgz"
    # unzip archive into geometry_data_dir
    with tarfile.open(archive_file, "r:gz") as tar:
        tar.extractall(geometry_data_dir)

    orig_image_array: NDArray3Du8 = read_images_to_volume(image_path=geometry_data_dir)
    print(orig_image_array.shape)

    # remove extracted files and directory
    for f in geometry_data_dir.glob("*.png"):
        f.unlink()

    vcell_image: vc.Image = vc.Image.from_ndarray_3d_u8(ndarray_3d_u8=orig_image_array, name="bunny")
    vcell_image_array = vcell_image.ndarray_3d_u8
    print(vcell_image.pixel_classes)
