
import os


def read_lipsync_data(path):
    """Read lipsync data from the given path."""
    # Expected structure: 
    # Lipsync/<layer name>.dat.
    # Each .dat file is for a specific layer and contains Moho format lipsync data.
    data = {}
    for filename in os.listdir(path):
        if filename.endswith(".dat"):
            layer_name = os.path.splitext(filename)[0]
            with open(os.path.join(path, filename), "r") as f:
                data[layer_name] = read_moho_lipsync_data(f)
                
    return data


def read_moho_lipsync_data(f):
    """Read Moho format lipsync data from the given file object."""
    # Each line is in the format: <frame> <mouth shape>.
    # Mouth shape is a name from the Preston Blair set.
    # AI, E, O, U, WQ, L, FV, MBP, etc, rest.
    # The first line is a header and should be "MohoSwitch1".
    _ = f.readline().strip()
    
    data = []
    for line in f:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2:
            continue
        frame_number = int(parts[0])
        mouth_shape = parts[1]
        data.append((frame_number, mouth_shape))

    return data