import trackpy as tp
import pandas as pd
import matplotlib.pyplot as plt


#####################################
############### 44/09 ###############
#####################################

right = pd.read_feather(
    "/Users/wheelenj/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-miracidia_photosensation/red_blue/20251218a01bas_20251218_125938.24568709/20251218a01bas_20251218_125938_tracks.feather"
)
left = pd.read_feather(
    "/Users/wheelenj/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-miracidia_photosensation/red_blue/20251218a01bas_20251218_125938.24568744/20251218a01bas_20251218_125938_tracks.feather"
)

# for 44/09, have to flip the right camera (09)
max_x_val = max(right["x"])
min_x_val = min(right["x"])

right = right.drop("particle", axis=1)
right["x"] = max_x_val - right["x"] + min_x_val

# for 44/09, have to make the left camera negative
left = left.drop("particle", axis=1)
left["x"] = left["x"] * -1

combined = pd.concat([left, right])

search_range = 45
memory = 25
adaptive_stop = 30

t = tp.link(
    combined, search_range=search_range, memory=memory, adaptive_stop=adaptive_stop
)

feather_path = "/Users/wheelenj/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-miracidia_photosensation/red_blue/20251218a01bas_20251218_125938_top_tracks.feather"
t.to_feather(feather_path)

pdf_path = "/Users/wheelenj/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-miracidia_photosensation/red_blue/20251218a01bas_20251218_125938_top_tracks.pdf"
fig = plt.figure()
ax = plt.gca()
t1 = tp.filter_stubs(t, 200)
tp.plot_traj(t1, ax=ax)
fig.savefig(pdf_path)


#####################################
############### 14/38 ###############
#####################################

right = pd.read_feather(
    "/Users/wheelenj/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-miracidia_photosensation/red_blue/20251218a01bas_20251218_125938.25128038/20251218a01bas_20251218_125938_tracks.feather"
)
left = pd.read_feather(
    "/Users/wheelenj/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-miracidia_photosensation/red_blue/20251218a01bas_20251218_125938.25112214/20251218a01bas_20251218_125938_tracks.feather"
)

# for 14/38, right camera remains the same
right = right.drop("particle", axis=1)

# for 14/38, left camera is flipped and made negative
left = left.drop("particle", axis=1)
max_x_val = max(left["x"])
min_x_val = min(left["x"])

left["x"] = max_x_val - left["x"] + min_x_val
left["x"] = left["x"] * -1

combined = pd.concat([left, right])

search_range = 45
memory = 25
adaptive_stop = 30

t = tp.link(
    combined, search_range=search_range, memory=memory, adaptive_stop=adaptive_stop
)

feather_path = "/Users/wheelenj/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-miracidia_photosensation/red_blue/20251218a01bas_20251218_125938_bottom_tracks.feather"
t.to_feather(feather_path)

pdf_path = "/Users/wheelenj/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-miracidia_photosensation/red_blue/20251218a01bas_20251218_125938_bottom_tracks.pdf"
fig = plt.figure()
ax = plt.gca()
t1 = tp.filter_stubs(t, 200)
tp.plot_traj(t1, ax=ax)
fig.savefig(pdf_path)
