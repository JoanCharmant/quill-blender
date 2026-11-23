import bpy
import logging
import numpy as np

def convert(name, picture_data):
        """Convert Quill picture data to Blender image object"""

        # picture_data.pixels has shape (height, width, 3 or 4), normalized to [0,1].
        # Blender's image buffer always expects flat RGBA, with the bottom row first.
        
        width, height = picture_data.width, picture_data.height
        channels = 4 if picture_data.hasAlpha else 3
        pixels = np.asarray(picture_data.pixels, dtype=np.float32)
        if pixels.shape != (height, width, channels):
            raise ValueError(f"Invalid decoded picture shape: {pixels.shape}")

        if channels == 3:
            rgba = np.ones((height, width, 4), dtype=np.float32)
            rgba[:, :, :3] = pixels
        else:
            rgba = pixels

        # Vertical flip to match Blender's bottom-up image buffer.
        rgba = rgba[::-1, :, :]

        image = bpy.data.images.new(name, width=width, height=height,
                                    alpha=picture_data.hasAlpha, float_buffer=False)
        try:
            image.pixels.foreach_set(np.ascontiguousarray(rgba).ravel())
            image.alpha_mode = 'STRAIGHT'
            image.update()
        except Exception:
            bpy.data.images.remove(image)
            raise

        # Store the recovered pixels inside the .blend instead of relying on the
        # missing original file. Failure to pack should not break this import.
        try:
            image.pack()
        except (RuntimeError, TypeError, OSError) as e:
            logging.warning("Could not pack Qbin image %s: %s", name, e)
        return image