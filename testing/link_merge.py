import trackpy as tp
import pandas as pd
import pickle
import gzip


right = pd.read_pickle(
    "/Users/njwheeler/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-miracidia_sensation/invision/double_agar/20240725/20240725-a04-RVH_20240725_142210.24568709/20240725-a04-RVH_20240725_142210_tracks.pkl.gz"
)
left = pd.read_pickle(
    "/Users/njwheeler/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-miracidia_sensation/invision/double_agar/20240725/20240725-a04-RVH_20240725_142210.24568744/20240725-a04-RVH_20240725_142210_tracks.pkl.gz"
)

# Fix for TypeError: 'float' object is not callable
max_x_val = max(right["x"])
min_x_val = min(right["x"])
right["x"] = max_x_val - right["x"] + min_x_val - 475
right = right[right["x"] >= -10]
right["y"] = right["y"] - 125
right = right.drop("particle", axis=1)

left = left.drop("particle", axis=1)
left["x"] = left["x"] * -1
combined = pd.concat([left, right])

search_range = 45
memory = 25
adaptive_stop = 30

t = tp.link(
    combined, search_range=search_range, memory=memory, adaptive_stop=adaptive_stop
)

pickle_path = "/Users/njwheeler/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-miracidia_sensation/invision/double_agar/20240725/20240725-a04-RVH_tracks.pkl.gz"

with gzip.open(pickle_path, "wb") as f:
    print("Writing pickle file.")
    pickle.dump(t, f)


###########################################################

right = pd.read_pickle(
    "/Users/njwheeler/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-miracidia_sensation/invision/double_agar/20240627/20240627-a01-RVH_20240627_135846.24568709/20240627-a01-RVH_20240627_135846_tracks.pkl.gz"
)
left = pd.read_pickle(
    "/Users/njwheeler/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-miracidia_sensation/invision/double_agar/20240627/20240627-a01-RVH_20240627_135846.24568744/20240627-a01-RVH_20240627_135846_tracks.pkl.gz"
)

# Fix for TypeError: 'float' object is not callable
max_x_val = max(right["x"])
min_x_val = min(right["x"])
right["x"] = max_x_val - right["x"] + min_x_val - 475
right = right[right["x"] >= -10]
right["y"] = right["y"] - 125
right = right.drop("particle", axis=1)

left = left.drop("particle", axis=1)
left["x"] = left["x"] * -1
combined = pd.concat([left, right])

search_range = 45
memory = 25
adaptive_stop = 30

t = tp.link(
    combined, search_range=search_range, memory=memory, adaptive_stop=adaptive_stop
)

pickle_path = "/Users/njwheeler/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-miracidia_sensation/invision/double_agar/20240627/20240627-a01-RVH_tracks.pkl.gz"

with gzip.open(pickle_path, "wb") as f:
    print("Writing pickle file.")
    pickle.dump(t, f)

###########################################################

right = pd.read_pickle(
    "/Users/njwheeler/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-miracidia_sensation/invision/double_agar/20240619/20240619-a01-RVH_20240619_140433.24568709/20240619-a01-RVH_20240619_140433_tracks.pkl.gz"
)
left = pd.read_pickle(
    "/Users/njwheeler/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-miracidia_sensation/invision/double_agar/20240619/20240619-a01-RVH_20240619_140433.24568744/20240619-a01-RVH_20240619_140433_tracks.pkl.gz"
)

# Fix for TypeError: 'float' object is not callable
max_x_val = max(right["x"])
min_x_val = min(right["x"])
right["x"] = max_x_val - right["x"] + min_x_val - 475
right = right[right["x"] >= -10]
right["y"] = right["y"] - 125
right = right.drop("particle", axis=1)

left = left.drop("particle", axis=1)
left["x"] = left["x"] * -1
combined = pd.concat([left, right])

search_range = 45
memory = 25
adaptive_stop = 30

t = tp.link(
    combined, search_range=search_range, memory=memory, adaptive_stop=adaptive_stop
)

pickle_path = "/Users/njwheeler/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-miracidia_sensation/invision/double_agar/20240829/20240829-a01-RVH.pkl.gz"

with gzip.open(pickle_path, "wb") as f:
    print("Writing pickle file.")
    pickle.dump(t, f)


###########################################################

right = pd.read_pickle(
    "/Users/njwheeler/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-miracidia_sensation/invision/double_agar/20240619/20240619-a01-RVH_20240619_140433.24568709/20240619-a01-RVH_20240619_140433_tracks.pkl.gz"
)
left = pd.read_pickle(
    "/Users/njwheeler/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-miracidia_sensation/invision/double_agar/20240619/20240619-a01-RVH_20240619_140433.24568744/20240619-a01-RVH_20240619_140433_tracks.pkl.gz"
)

# Fix for TypeError: 'float' object is not callable
max_x_val = max(right["x"])
min_x_val = min(right["x"])
right["x"] = max_x_val - right["x"] + min_x_val - 475
right = right[right["x"] >= -10]
right["y"] = right["y"] - 125
right = right.drop("particle", axis=1)

left = left.drop("particle", axis=1)
left["x"] = left["x"] * -1
combined = pd.concat([left, right])

search_range = 45
memory = 25
adaptive_stop = 30

t = tp.link(
    combined, search_range=search_range, memory=memory, adaptive_stop=adaptive_stop
)

pickle_path = "/Users/njwheeler/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-miracidia_sensation/invision/double_agar/20240829/20240829-a01-RVH.pkl.gz"

with gzip.open(pickle_path, "wb") as f:
    print("Writing pickle file.")
    pickle.dump(t, f)
