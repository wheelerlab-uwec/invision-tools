library(tidyverse)
library(reticulate)
use_condaenv('sandbox')

source_python('~/GitHub/invision-tools/utils/read_pickle.py')

df <- read_pickle_file('/Users/njwheeler/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-miracidia_sensation/invision/20240111/scw_response_double_agar1_20240111_20240111_125604.24568744/scw_response_double_agar1_20240111_20240111_125604_tracks.pkl.gz')

calc_dist <- function(df) {
  
  df <- df %>% 
    drop_na() %>% 
    arrange(particle, frame) %>% 
    group_by(particle) %>%
    mutate(
      smooth_x = predict(loess(x ~ seq(1:length(x)), span = 1)),
      smooth_y = predict(loess(y ~ seq(1:length(y)), span = 1))
    ) %>% 
    mutate(
      diff_x = c(0, diff(smooth_x)),
      diff_y = c(0, diff(smooth_y)),
      change_x = case_when(
        sign(diff_x) != sign(lead(diff_x)) & diff_x != 0 ~ TRUE,
        TRUE ~ FALSE),
      change_y = case_when(
        sign(diff_y) != sign(lead(diff_y)) & diff_y != 0 ~ TRUE,
        TRUE ~ FALSE)
    ) %>% 
    mutate(dist = sqrt((lead(smooth_x) - smooth_x)^2 + (lead(smooth_y) - smooth_y)^2),
           w = atan2(lead(smooth_y) - smooth_y, lead(smooth_x) - smooth_x) - atan2(smooth_y - lag(smooth_y), x - lag(smooth_x)))
  
  return(df)
  
}

longest <- df %>% 
  group_by(particle) %>% 
  summarise(n = n()) %>% 
  filter(n > 200)

plot <- df %>% 
  filter(particle %in% longest$particle) %>% 
  group_by(particle) %>% 
  arrange(frame) %>% 
  ggplot() +
  geom_path(aes(x = x, y = y, group = particle, color = frame)) +
  scale_color_viridis_c() +
  # scale_x_continuous(limits = c(0, 5400)) +
  # scale_y_continuous(limits = c(0, 3400)) +
  theme_minimal() +
  theme(panel.grid = element_blank()) +
  NULL

cowplot::save_plot('/Users/njwheeler/Library/CloudStorage/OneDrive-UW-EauClaire/WheelerLab/Data/project-miracidia_sensation/invision/20240111/scw_response_double_agar1_20240111_20240111_125604.24568744/temp_r.pdf',
                   plot)
