library(parallel)
library(future)
library(future.apply)
library(furrr)
library(dplyr)
library(purrr)
library(tibble)

read_pickle_file <- function(file_path) {
  # Ensure reticulate is loaded
  if (!requireNamespace("reticulate", quietly = TRUE)) {
    stop("Package 'reticulate' is required but not installed.")
  }

  # Import Python modules
  pickle <- reticulate::import("pickle")
  gzip <- reticulate::import("gzip")

  # Read the gzip-compressed pickle file
  # Using Python code through reticulate
  py_code <- sprintf(
    "
import pickle
import gzip
import pandas as pd

with gzip.open('%s', 'rb') as f:
    data = pickle.load(f)

# Convert to pandas DataFrame if it's not already
if not isinstance(data, pd.DataFrame):
    data = pd.DataFrame(data)
",
    file_path
  )

  # Execute Python code and get the data
  reticulate::py_run_string(py_code)

  # Get the data from Python environment and convert to R dataframe
  df <- reticulate::py$data

  # Convert to tibble for consistency with tidyverse workflow
  if (!is.null(df)) {
    df <- as_tibble(df)
  }

  return(df)
}

quick_nest <- function(df, nest_cols) {
  df |>
    group_by(across(all_of(nest_cols))) |>
    nest()
}

split_trajectory <- function(data, frame_rate = 15, chunk_duration_sec = 10) {
  # Number of frames per chunk
  frames_per_chunk <- frame_rate * chunk_duration_sec

  # If data has fewer than one chunk's worth of frames, return NULL
  if ((max(data$frame) - min(data$frame) + 1) < frames_per_chunk) {
    return(NULL)
  }

  # Calculate chunk number for each row based on time since the first frame
  data <- data |>
    mutate(
      chunk_id = floor((frame - min(frame)) / frames_per_chunk),
      subparticle = paste0(particle, "_", chunk_id + 1) # +1 to start IDs at 1
    )

  return(data)
}

calculate_track_features <- function(
  nested_tracks_df,
  fps = 25,
  pixel_to_mm = 1
) {
  feature_quantiles <- function(x, prefix, probs = c(0.1, 0.5, 0.9)) {
    q <- quantile(x, probs = probs, na.rm = TRUE)
    names(q) <- paste0(prefix, "_q", probs * 100)
    # Convert to tibble while preserving names
    tibble(!!!as.list(q))
  }

  # Helper function for circular statistics
  circular_mean <- function(angles) {
    mean_x <- mean(cos(angles), na.rm = TRUE)
    mean_y <- mean(sin(angles), na.rm = TRUE)
    atan2(mean_y, mean_x)
  }

  circular_var <- function(angles) {
    r <- sqrt(
      mean(cos(angles), na.rm = TRUE)^2 + mean(sin(angles), na.rm = TRUE)^2
    )
    1 - r
  }

  calc_features <- function(track_df) {
    track_df <- track_df %>%
      arrange(frame) %>%
      mutate(
        # Basic derivatives
        dx = lead(x) - x,
        dy = lead(y) - y,
        dt = (lead(frame) - frame) / fps, # Convert to seconds

        # Convert to real units
        dx_mm = dx * pixel_to_mm,
        dy_mm = dy * pixel_to_mm,

        # Speed and acceleration
        speed = sqrt(dx_mm^2 + dy_mm^2) / dt,
        acceleration = c(NA, diff(speed) / dt[-length(dt)]),
        jerk = c(
          NA,
          diff(acceleration, na.rm = TRUE) / dt[-c(length(dt) - 1, length(dt))]
        ),

        # Angular measures
        heading = atan2(dy, dx),
        angular_velocity = c(NA, diff(heading) / dt[-length(dt)]),
        angular_acceleration = c(
          NA,
          diff(angular_velocity, na.rm = TRUE) /
            dt[-c(length(dt) - 1, length(dt))]
        ),

        # Curvature (rate of change of heading with respect to distance)
        ds = sqrt(dx_mm^2 + dy_mm^2),
        curvature = ifelse(ds > 0, abs(c(NA, diff(heading))) / ds, 0),

        # Distance from starting point
        dist_from_start = sqrt((x - x[1])^2 + (y - y[1])^2) * pixel_to_mm
      )

    # Clean dataframe
    clean_df <- track_df %>%
      drop_na(speed, acceleration, angular_velocity)

    # Path-based metrics
    path_length <- sum(clean_df$ds, na.rm = TRUE)
    net_disp <- sqrt(
      (last(track_df$x) - first(track_df$x))^2 +
        (last(track_df$y) - first(track_df$y))^2
    ) *
      pixel_to_mm
    duration <- max(track_df$frame) - min(track_df$frame)
    duration_sec <- duration / fps

    # Spatial metrics
    centroid <- c(mean(track_df$x), mean(track_df$y))
    radius_of_gyration <- sqrt(mean(
      (track_df$x - centroid[1])^2 +
        (track_df$y - centroid[2])^2
    )) *
      pixel_to_mm

    # Bounding box and convex hull
    bbox_aspect_ratio <- {
      xrange <- range(track_df$x)
      yrange <- range(track_df$y)
      diff(xrange) / diff(yrange)
    }

    hull_area <- {
      if (nrow(track_df) >= 3) {
        ch <- grDevices::chull(track_df$x, track_df$y)
        sum(abs(
          track_df$x[ch] *
            c(track_df$y[ch[-1]], track_df$y[ch[1]]) -
            track_df$y[ch] * c(track_df$x[ch[-1]], track_df$x[ch[1]])
        )) /
          2 *
          (pixel_to_mm^2)
      } else {
        0
      }
    }

    # Angular metrics with circular statistics
    total_turn <- sum(abs(clean_df$angular_velocity), na.rm = TRUE)
    mean_heading <- circular_mean(clean_df$heading)
    heading_variance <- circular_var(clean_df$heading)

    # Directional persistence
    directional_persistence <- abs(cos(clean_df$heading - mean_heading)) %>%
      mean(na.rm = TRUE)

    # Straightness index (alternative to tortuosity)
    straightness <- net_disp / path_length

    # Movement efficiency (net displacement per unit time)
    movement_efficiency <- net_disp / duration_sec

    # Fractal dimension (simplified box-counting approximation)
    fractal_dim <- {
      if (path_length > 0 && net_disp > 0) {
        log(path_length) / log(net_disp)
      } else {
        NA_real_
      }
    }

    # Sinuosity (alternative measure of path complexity)
    sinuosity <- path_length / net_disp

    # Maximum distance from start
    max_dist_from_start <- max(clean_df$dist_from_start, na.rm = TRUE)

    # Turning bias (preference for left vs right turns)
    signed_turns <- clean_df$angular_velocity[!is.na(clean_df$angular_velocity)]
    turning_bias <- mean(signed_turns, na.rm = TRUE)

    # Autocorrelation measures (lag-1)
    speed_autocorr <- if (length(clean_df$speed) > 1) {
      cor(
        clean_df$speed[-length(clean_df$speed)],
        clean_df$speed[-1],
        use = "complete.obs"
      )
    } else {
      NA_real_
    }

    heading_autocorr <- if (length(clean_df$heading) > 1) {
      cor(
        clean_df$heading[-length(clean_df$heading)],
        clean_df$heading[-1],
        use = "complete.obs"
      )
    } else {
      NA_real_
    }

    tibble(
      frame_start = min(track_df$frame),
      frame_end = max(track_df$frame),
      duration_frames = duration,
      duration_sec = duration_sec,
      mean_x = mean(track_df$x),
      mean_y = mean(track_df$y),
      sd_x = sd(track_df$x),
      sd_y = sd(track_df$y),

      # Path metrics
      path_length = path_length,
      net_displacement = net_disp,
      tortuosity = path_length / net_disp,
      straightness = straightness,
      sinuosity = sinuosity,
      movement_efficiency = movement_efficiency,
      fractal_dimension = fractal_dim,

      # Speed metrics
      speed_mean = mean(clean_df$speed, na.rm = TRUE),
      speed_var = var(clean_df$speed, na.rm = TRUE),
      speed_max = max(clean_df$speed, na.rm = TRUE),
      speed_autocorr = speed_autocorr,

      # Acceleration metrics
      acceleration_mean = mean(clean_df$acceleration, na.rm = TRUE),
      acceleration_var = var(clean_df$acceleration, na.rm = TRUE),
      jerk_mean = mean(clean_df$jerk, na.rm = TRUE),

      # Angular metrics
      angular_velocity_mean = mean(clean_df$angular_velocity, na.rm = TRUE),
      angular_velocity_var = var(clean_df$angular_velocity, na.rm = TRUE),
      angular_acceleration_mean = mean(
        clean_df$angular_acceleration,
        na.rm = TRUE
      ),
      total_turn = total_turn,
      turning_bias = turning_bias,
      mean_curvature = mean(clean_df$curvature, na.rm = TRUE),

      # Directional metrics
      mean_heading = mean_heading,
      heading_variance = heading_variance,
      directional_persistence = directional_persistence,
      heading_autocorr = heading_autocorr,

      # Spatial metrics
      radius_of_gyration = radius_of_gyration,
      convex_hull_area = hull_area,
      bbox_aspect_ratio = bbox_aspect_ratio,
      max_dist_from_start = max_dist_from_start
    ) %>%
      bind_cols(
        as_tibble(feature_quantiles(clean_df$speed, "speed")),
        as_tibble(feature_quantiles(clean_df$acceleration, "accel")),
        as_tibble(feature_quantiles(clean_df$angular_velocity, "angvel")),
        as_tibble(feature_quantiles(clean_df$angular_acceleration, "angacc")),
        as_tibble(feature_quantiles(clean_df$curvature, "curv"))
      )
  }

  nested_tracks_df %>%
    mutate(features = map(data, calc_features)) %>%
    unnest(features)
}

calculate_track_features_parallel <- function(
  nested_tracks_df,
  fps = 25,
  pixel_to_mm = 1,
  n_cores = parallel::detectCores() - 1,
  chunk_size = 500
) {
  # Set up parallel processing
  plan(multisession, workers = n_cores)

  feature_quantiles <- function(x, prefix, probs = c(0.1, 0.5, 0.9)) {
    q <- quantile(x, probs = probs, na.rm = TRUE)
    names(q) <- paste0(prefix, "_q", probs * 100)
    tibble(!!!as.list(q))
  }

  # Helper function for circular statistics
  circular_mean <- function(angles) {
    mean_x <- mean(cos(angles), na.rm = TRUE)
    mean_y <- mean(sin(angles), na.rm = TRUE)
    atan2(mean_y, mean_x)
  }

  circular_var <- function(angles) {
    r <- sqrt(
      mean(cos(angles), na.rm = TRUE)^2 + mean(sin(angles), na.rm = TRUE)^2
    )
    1 - r
  }

  calc_features <- function(track_df) {
    track_df <- track_df %>%
      arrange(frame) %>%
      mutate(
        # Basic derivatives
        dx = lead(x) - x,
        dy = lead(y) - y,
        dt = (lead(frame) - frame) / fps,

        # Convert to real units
        dx_mm = dx * pixel_to_mm,
        dy_mm = dy * pixel_to_mm,

        # Speed and acceleration
        speed = sqrt(dx_mm^2 + dy_mm^2) / dt,
        acceleration = c(NA, diff(speed) / dt[-length(dt)]),
        jerk = c(
          NA,
          diff(acceleration, na.rm = TRUE) / dt[-c(length(dt) - 1, length(dt))]
        ),

        # Angular measures
        heading = atan2(dy, dx),
        angular_velocity = c(NA, diff(heading) / dt[-length(dt)]),
        angular_acceleration = c(
          NA,
          diff(angular_velocity, na.rm = TRUE) /
            dt[-c(length(dt) - 1, length(dt))]
        ),

        # Curvature
        ds = sqrt(dx_mm^2 + dy_mm^2),
        curvature = ifelse(ds > 0, abs(c(NA, diff(heading))) / ds, 0),

        # Distance from starting point
        dist_from_start = sqrt((x - x[1])^2 + (y - y[1])^2) * pixel_to_mm
      )

    # Clean dataframe
    clean_df <- track_df %>%
      drop_na(speed, acceleration, angular_velocity)

    # Path-based metrics
    path_length <- sum(clean_df$ds, na.rm = TRUE)
    net_disp <- sqrt(
      (last(track_df$x) - first(track_df$x))^2 +
        (last(track_df$y) - first(track_df$y))^2
    ) *
      pixel_to_mm
    duration <- max(track_df$frame) - min(track_df$frame)
    duration_sec <- duration / fps

    # Spatial metrics
    centroid <- c(mean(track_df$x), mean(track_df$y))
    radius_of_gyration <- sqrt(mean(
      (track_df$x - centroid[1])^2 +
        (track_df$y - centroid[2])^2
    )) *
      pixel_to_mm

    # Bounding box and convex hull
    bbox_aspect_ratio <- {
      xrange <- range(track_df$x)
      yrange <- range(track_df$y)
      diff(xrange) / diff(yrange)
    }

    hull_area <- {
      if (nrow(track_df) >= 3) {
        ch <- grDevices::chull(track_df$x, track_df$y)
        sum(abs(
          track_df$x[ch] *
            c(track_df$y[ch[-1]], track_df$y[ch[1]]) -
            track_df$y[ch] * c(track_df$x[ch[-1]], track_df$x[ch[1]])
        )) /
          2 *
          (pixel_to_mm^2)
      } else {
        0
      }
    }

    # Angular metrics with circular statistics
    total_turn <- sum(abs(clean_df$angular_velocity), na.rm = TRUE)
    mean_heading <- circular_mean(clean_df$heading)
    heading_variance <- circular_var(clean_df$heading)

    # Directional persistence
    directional_persistence <- abs(cos(clean_df$heading - mean_heading)) %>%
      mean(na.rm = TRUE)

    # Straightness index
    straightness <- net_disp / path_length

    # Movement efficiency
    movement_efficiency <- net_disp / duration_sec

    # Fractal dimension
    fractal_dim <- {
      if (path_length > 0 && net_disp > 0) {
        log(path_length) / log(net_disp)
      } else {
        NA_real_
      }
    }

    # Sinuosity
    sinuosity <- path_length / net_disp

    # Maximum distance from start
    max_dist_from_start <- max(clean_df$dist_from_start, na.rm = TRUE)

    # Turning bias
    signed_turns <- clean_df$angular_velocity[!is.na(clean_df$angular_velocity)]
    turning_bias <- mean(signed_turns, na.rm = TRUE)

    # Autocorrelation measures
    speed_autocorr <- if (length(clean_df$speed) > 1) {
      cor(
        clean_df$speed[-length(clean_df$speed)],
        clean_df$speed[-1],
        use = "complete.obs"
      )
    } else {
      NA_real_
    }

    heading_autocorr <- if (length(clean_df$heading) > 1) {
      cor(
        clean_df$heading[-length(clean_df$heading)],
        clean_df$heading[-1],
        use = "complete.obs"
      )
    } else {
      NA_real_
    }

    tibble(
      frame_start = min(track_df$frame),
      frame_end = max(track_df$frame),
      duration_frames = duration,
      duration_sec = duration_sec,
      mean_x = mean(track_df$x),
      mean_y = mean(track_df$y),
      sd_x = sd(track_df$x),
      sd_y = sd(track_df$y),

      # Path metrics
      path_length = path_length,
      net_displacement = net_disp,
      tortuosity = path_length / net_disp,
      straightness = straightness,
      sinuosity = sinuosity,
      movement_efficiency = movement_efficiency,
      fractal_dimension = fractal_dim,

      # Speed metrics
      speed_mean = mean(clean_df$speed, na.rm = TRUE),
      speed_var = var(clean_df$speed, na.rm = TRUE),
      speed_max = max(clean_df$speed, na.rm = TRUE),
      speed_autocorr = speed_autocorr,

      # Acceleration metrics
      acceleration_mean = mean(clean_df$acceleration, na.rm = TRUE),
      acceleration_var = var(clean_df$acceleration, na.rm = TRUE),
      jerk_mean = mean(clean_df$jerk, na.rm = TRUE),

      # Angular metrics
      angular_velocity_mean = mean(clean_df$angular_velocity, na.rm = TRUE),
      angular_velocity_var = var(clean_df$angular_velocity, na.rm = TRUE),
      angular_acceleration_mean = mean(
        clean_df$angular_acceleration,
        na.rm = TRUE
      ),
      total_turn = total_turn,
      turning_bias = turning_bias,
      mean_curvature = mean(clean_df$curvature, na.rm = TRUE),

      # Directional metrics
      mean_heading = mean_heading,
      heading_variance = heading_variance,
      directional_persistence = directional_persistence,
      heading_autocorr = heading_autocorr,

      # Spatial metrics
      radius_of_gyration = radius_of_gyration,
      convex_hull_area = hull_area,
      bbox_aspect_ratio = bbox_aspect_ratio,
      max_dist_from_start = max_dist_from_start
    ) %>%
      bind_cols(
        feature_quantiles(clean_df$speed, "speed"),
        feature_quantiles(clean_df$acceleration, "accel"),
        feature_quantiles(clean_df$angular_velocity, "angvel"),
        feature_quantiles(clean_df$angular_acceleration, "angacc"),
        feature_quantiles(clean_df$curvature, "curv")
      )
  }

  # Process chunks for accurate progress tracking
  n_rows <- nrow(nested_tracks_df)
  n_chunks <- ceiling(n_rows / chunk_size)

  cat(sprintf(
    "Processing %d tracks in %d chunks of ~%d tracks each...\n",
    n_rows,
    n_chunks,
    chunk_size
  ))

  # Split into chunks
  nested_tracks_df$chunk_id <- ceiling(seq_len(n_rows) / chunk_size)
  chunks <- split(nested_tracks_df, nested_tracks_df$chunk_id)

  # Process chunk function
  process_chunk <- function(chunk_df) {
    chunk_df %>%
      select(-chunk_id) %>% # Remove the chunk_id column
      mutate(features = map(data, calc_features)) %>%
      unnest(features)
  }

  # Process chunks with real progress tracking
  results <- list()
  pb <- txtProgressBar(min = 0, max = length(chunks), style = 3)

  for (i in seq_along(chunks)) {
    results[[i]] <- process_chunk(chunks[[i]])
    setTxtProgressBar(pb, i)
  }

  close(pb)

  # Combine results
  result <- bind_rows(results)

  # Clean up parallel backend
  plan(sequential)

  return(result)
}
