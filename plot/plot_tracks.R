library(ggplot2)
library(dplyr)
library(magrittr)
library(stringr)
library(purrr)
library(tidyr)
library(reticulate)
library(ggrepel)
library(fs)
library(cowplot)
library(gganimate)
# reticulate::virtualenv_create("r-reticulate", force = TRUE)
# reticulate::virtualenv_install(envname = 'r-reticulate', packages = 'pandas')
reticulate::use_virtualenv('r-reticulate')
library(here)

# args <- commandArgs(trailingOnly = TRUE)

source_python("~/GitHub/invision-tools/utils/read_pickle.py")

set_here("/Users/njwheeler/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-mosquito_sensation/videos/20240301-a01-MRB_20240301_144112.24568709")

left_file = '/Users/njwheeler/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-mosquito_sensation/videos/20240301-a01-MRB_20240301_144112.24568709/20240301-a01-MRB_20240301_144112_tracks.pkl.gz'
right_file = '/Users/njwheeler/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-mosquito_sensation/videos/20240301-a01-MRB_20240301_144112.24568744/20240301-a01-MRB_20240301_144112_tracks.pkl.gz'

right <- read_pickle_file(right_file) %>%
  mutate(particle = str_c("right_", particle))
left <- read_pickle_file(left_file) %>%
  mutate(
    particle = str_c("left_", particle),
    x = x - 5496
  )
joined <- bind_rows(right, left)

calc_dist <- function(df) {
  df <- df %>%
    arrange(frame) %>%
    slice(c(1, n())) %>%
    mutate(
      dist = sqrt((lead(x) - x)^2 + (lead(y) - y)^2)
    )

  return(df$dist[1])
}

df_dist <- joined %>%
  group_nest(particle) %>%
  # slice(1:15) %>%
  mutate(
    n_frames = map_int(data, ~ count(.x)$n)
  ) %>%
  filter(n_frames > 200) %>%
  mutate(
    dist = map_dbl(data, calc_dist)
  )

filtered <- df_dist %>%
  filter(dist > 500) %>%
  unnest(data)

labels <- filtered %>%
  group_by(particle) %>%
  arrange(frame, .by_group = TRUE) %>%
  slice(1)

# initial <- filtered %>%
#   group_by(particle) %>%
#   arrange(frame) %>%
#   ggplot() +
#   geom_path(aes(x = x, y = y, group = particle, color = frame)) +
#   scale_color_viridis_c() +
#   scale_x_continuous(breaks = seq(-6000, 6000, 500)) +
#   theme_minimal() +
#   theme(
#     # panel.grid = element_blank(),
#     # legend.position = 'empty'
#   ) +
#   NULL

shifted <- filtered %>%
  mutate(
    x = case_when(
      str_detect(particle, "right") ~ x - 385,
      TRUE ~ x
    ),
    y = case_when(
      str_detect(particle, "right") ~ y + 125,
      TRUE ~ y
    )
  )

post <- shifted %>%
  group_by(particle) %>%
  arrange(frame) %>%
  ggplot() +
  annotate("rect",
    xmin = -385, xmax = 0,
    ymin = -Inf, ymax = Inf,
    fill = "grey", alpha = .5
  ) +
  # annotate("rect",
  #   xmin = -5496 + 1296, xmax = -5496 + 1296 + 1110,
  #   ymin = 1380, ymax = 1380 + 1164,
  #   fill = "indianred", alpha = .25
  # ) +
  # annotate("rect",
  #   xmin = 3342 - 385, xmax = 3342 + 1050 - 385,
  #   ymin = 1326, ymax = 1326 + 1104,
  #   fill = "steelblue", alpha = .25
  # ) +
  geom_path(aes(x = x, y = y, group = particle, color = frame),
    linewidth = 1, lineend = "round"
  ) +
  scale_color_viridis_c() +
  coord_equal() +
  scale_x_continuous(breaks = seq(-5100, 5100, 500),
                     limits = c(-5100, 5100)) +
  scale_y_continuous(breaks = seq(0, 3750, 500)) +
  theme_minimal() +
  theme(
    panel.grid = element_blank(),
    legend.position = "none"
  ) +
  NULL
post

save_plot()

# anim <- animate(post + transition_reveal(frame),
#                            nframes = 650,
#                            fps = 50,
#                            renderer = gifski_renderer(),
#                            width = 11 * 300, height = 5 * 300, units = 'px'
# )
#
# anim_save(filename = '/Users/njwheeler/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-miracidia_sensation/invision/20240111/scw_response_double_agar1.gif',
#                      animation = anim)

save_plot("/Users/njwheeler/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-miracidia_sensation/invision/20240111/scw_response_double_agar1.gif",
  post,
  base_height = 5,
  base_width = 11
)
