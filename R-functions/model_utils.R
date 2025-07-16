library(broom.mixed)
library(broom)
library(lme4)
library(lmerTest)

# Function to fit model with fallback strategies
# fit_model.R

fit_model <- function(feature, data) {
  formula <- reformulate(
    "region + (1 | date/video/particle)",
    response = feature
  )

  # Helper to add residuals as nested tibble
  add_residuals_nested <- function(
    model,
    clean_data,
    feature,
    note = NA_character_
  ) {
    preds <- tryCatch(predict(model), error = function(e) {
      rep(NA_real_, nrow(clean_data))
    })
    resids <- tryCatch(residuals(model), error = function(e) {
      rep(NA_real_, nrow(clean_data))
    })
    residuals_df <- tibble(
      row_id = seq_len(nrow(clean_data)),
      observed = clean_data[[feature]],
      predicted = preds,
      residual = resids
    )
    tidy_out <- tidy(model, effects = "fixed") %>%
      filter(str_detect(term, "^region")) %>%
      mutate(feature = feature)
    if (!is.na(note)) {
      tidy_out <- tidy_out %>% mutate(note = note)
    }
    tidy_out %>% mutate(residuals_df = list(residuals_df))
  }

  tryCatch(
    {
      clean_data <- data %>%
        filter(is.finite(.data[[feature]])) %>%
        drop_na(all_of(c(feature, "region", "date", "video", "particle")))

      if (nrow(clean_data) < 1000) {
        stop("Insufficient data after removing infinite values")
      }

      model <- lmer(
        formula,
        data = clean_data,
        control = lmerControl(optimizer = "bobyqa")
      )

      if (isSingular(model)) {
        warning(paste(
          "Singular fit for",
          feature,
          "- random effects may be unreliable"
        ))
      }

      add_residuals_nested(model, clean_data, feature)
    },
    error = function(e1) {
      tryCatch(
        {
          clean_data <- data %>%
            drop_na(all_of(c(feature, "region", "date", "video", "particle")))

          model <- lmer(
            formula,
            data = clean_data,
            control = lmerControl(optimizer = "bobyqa")
          )

          if (isSingular(model)) {
            warning(paste(
              "Singular fit for",
              feature,
              "after cleaning - random effects may be unreliable"
            ))
          }

          add_residuals_nested(model, clean_data, feature)
        },
        error = function(e2) {
          tryCatch(
            {
              simple_formula <- reformulate(
                "region + (1 | date)",
                response = feature
              )
              clean_data <- data %>%
                drop_na(all_of(c(feature, "region", "date")))

              model <- lmer(
                simple_formula,
                data = clean_data,
                control = lmerControl(optimizer = "bobyqa")
              )

              add_residuals_nested(
                model,
                clean_data,
                feature,
                note = "simplified_random_effects"
              )
            },
            error = function(e3) {
              tryCatch(
                {
                  fixed_formula <- reformulate("region", response = feature)
                  clean_data <- data %>%
                    drop_na(all_of(c(feature, "region")))

                  model <- lm(fixed_formula, data = clean_data)

                  add_residuals_nested(
                    model,
                    clean_data,
                    feature,
                    note = "fixed_effects_only"
                  )
                },
                error = function(e4) {
                  levels <- unique(data$region)
                  reference <- levels[1]
                  contrasts <- setdiff(levels, reference)
                  tibble(
                    effect = "fixed",
                    term = paste0("region", contrasts),
                    estimate = NA_real_,
                    std.error = NA_real_,
                    statistic = NA_real_,
                    df = NA_real_,
                    p.value = NA_real_,
                    feature = feature,
                    note = "model_failed",
                    residuals_df = list(tibble())
                  )
                }
              )
            }
          )
        }
      )
    }
  )
}


fit_model_base <- function(feature, data) {
  formula <- reformulate(
    "tissue + (1 | date/video/particle)",
    response = feature
  )

  # Helper to add residuals as nested tibble
  add_residuals_nested <- function(
    model,
    clean_data,
    feature,
    note = NA_character_
  ) {
    preds <- tryCatch(predict(model), error = function(e) {
      rep(NA_real_, nrow(clean_data))
    })
    resids <- tryCatch(residuals(model), error = function(e) {
      rep(NA_real_, nrow(clean_data))
    })
    residuals_df <- tibble(
      row_id = seq_len(nrow(clean_data)),
      observed = clean_data[[feature]],
      predicted = preds,
      residual = resids
    )
    tidy_out <- tidy(model, effects = "fixed") %>%
      filter(str_detect(term, "^tissue")) %>%
      mutate(feature = feature)
    if (!is.na(note)) {
      tidy_out <- tidy_out %>% mutate(note = note)
    }
    tidy_out %>% mutate(residuals_df = list(residuals_df))
  }

  tryCatch(
    {
      clean_data <- data %>%
        filter(is.finite(.data[[feature]])) %>%
        drop_na(all_of(c(feature, "tissue", "date", "video", "particle")))

      if (nrow(clean_data) < 1000) {
        stop("Insufficient data after removing infinite values")
      }

      model <- lmer(
        formula,
        data = clean_data,
        control = lmerControl(optimizer = "bobyqa")
      )

      if (isSingular(model)) {
        warning(paste(
          "Singular fit for",
          feature,
          "- random effects may be unreliable"
        ))
      }

      add_residuals_nested(model, clean_data, feature)
    },
    error = function(e1) {
      tryCatch(
        {
          clean_data <- data %>%
            drop_na(all_of(c(feature, "tissue", "date", "video", "particle")))

          model <- lmer(
            formula,
            data = clean_data,
            control = lmerControl(optimizer = "bobyqa")
          )

          if (isSingular(model)) {
            warning(paste(
              "Singular fit for",
              feature,
              "after cleaning - random effects may be unreliable"
            ))
          }

          add_residuals_nested(model, clean_data, feature)
        },
        error = function(e2) {
          tryCatch(
            {
              simple_formula <- reformulate(
                "tissue + (1 | date)",
                response = feature
              )
              clean_data <- data %>%
                drop_na(all_of(c(feature, "tissue", "date")))

              model <- lmer(
                simple_formula,
                data = clean_data,
                control = lmerControl(optimizer = "bobyqa")
              )

              add_residuals_nested(
                model,
                clean_data,
                feature,
                note = "simplified_random_effects"
              )
            },
            error = function(e3) {
              tryCatch(
                {
                  fixed_formula <- reformulate("tissue", response = feature)
                  clean_data <- data %>%
                    drop_na(all_of(c(feature, "tissue")))

                  model <- lm(fixed_formula, data = clean_data)

                  add_residuals_nested(
                    model,
                    clean_data,
                    feature,
                    note = "fixed_effects_only"
                  )
                },
                error = function(e4) {
                  levels <- unique(data$tissue)
                  reference <- levels[1]
                  contrasts <- setdiff(levels, reference)
                  tibble(
                    effect = "fixed",
                    term = paste0("tissue", contrasts),
                    estimate = NA_real_,
                    std.error = NA_real_,
                    statistic = NA_real_,
                    df = NA_real_,
                    p.value = NA_real_,
                    feature = feature,
                    note = "model_failed",
                    residuals_df = list(tibble())
                  )
                }
              )
            }
          )
        }
      )
    }
  )
}


fit_model_interaction <- function(
  feature,
  data,
  fixed_effects = "tissue",
  use_temporal_correlation = TRUE
) {
  # Load required libraries
  require(lme4)
  require(nlme)
  require(broom)
  require(broom.mixed)
  require(dplyr)

  # Create formula with interactions between all fixed effects
  if (length(fixed_effects) > 1) {
    # Create all pairwise and higher-order interactions
    interaction_terms <- paste(fixed_effects, collapse = " * ")
    fixed_part <- interaction_terms
  } else {
    fixed_part <- fixed_effects[1]
  }

  # Helper to extract and format model results
  extract_model_results <- function(model, feature, note = NA_character_) {
    tidy_out <- tidy(model, effects = "fixed") %>%
      # filter(term != "(Intercept)") %>%
      mutate(feature = feature)

    if (!is.na(note)) {
      tidy_out <- tidy_out %>% mutate(note = note)
    }

    return(tidy_out)
  }

  tryCatch(
    {
      # Check that all required columns exist
      required_cols <- c(feature, fixed_effects, "date", "video", "particle")
      missing_cols <- setdiff(required_cols, names(data))
      if (length(missing_cols) > 0) {
        stop(paste("Missing columns:", paste(missing_cols, collapse = ", ")))
      }

      clean_data <- data %>%
        filter(is.finite(.data[[feature]])) %>%
        drop_na(all_of(required_cols))

      if (nrow(clean_data) < 1000) {
        stop("Insufficient data after removing infinite values")
      }

      # Try temporal correlation model first (if requested and frame_start is in fixed effects)
      if (use_temporal_correlation && "frame_start" %in% fixed_effects) {
        tryCatch(
          {
            model <- lme(
              fixed = reformulate(fixed_part, response = feature),
              random = ~ 1 | date / video / particle,
              correlation = corAR1(form = ~ 1 | date / video / particle),
              data = clean_data,
              control = lmeControl(opt = "optim")
            )

            return(extract_model_results(
              model,
              feature,
              note = "temporal_correlation"
            ))
          },
          error = function(e_temporal) {
            # Fall back to lmer if temporal correlation fails
            warning(paste(
              "Temporal correlation model failed for",
              feature,
              "- falling back to standard LMM"
            ))
          }
        )
      }

      # Standard lmer approach (fallback or if temporal correlation not requested)
      model <- lmer(
        reformulate(
          paste(fixed_part, "+ (1 | date/video/particle)"),
          response = feature
        ),
        data = clean_data,
        control = lmerControl(optimizer = "bobyqa")
      )

      if (isSingular(model)) {
        warning(paste(
          "Singular fit for",
          feature,
          "- random effects may be unreliable"
        ))
      }

      extract_model_results(model, feature)
    },
    error = function(e1) {
      tryCatch(
        {
          required_cols <- c(
            feature,
            fixed_effects,
            "date",
            "video",
            "particle"
          )
          clean_data <- data %>%
            drop_na(all_of(required_cols))

          model <- lmer(
            reformulate(
              paste(fixed_part, "+ (1 | date/video/particle)"),
              response = feature
            ),
            data = clean_data,
            control = lmerControl(optimizer = "bobyqa")
          )

          if (isSingular(model)) {
            warning(paste(
              "Singular fit for",
              feature,
              "after cleaning - random effects may be unreliable"
            ))
          }

          extract_model_results(model, feature)
        },
        error = function(e2) {
          tryCatch(
            {
              simple_formula <- reformulate(
                paste(fixed_part, "+ (1 | date)"),
                response = feature
              )
              required_cols <- c(feature, fixed_effects, "date")
              clean_data <- data %>%
                drop_na(all_of(required_cols))

              model <- lmer(
                simple_formula,
                data = clean_data,
                control = lmerControl(optimizer = "bobyqa")
              )

              extract_model_results(
                model,
                feature,
                note = "simplified_random_effects"
              )
            },
            error = function(e3) {
              tryCatch(
                {
                  fixed_formula <- reformulate(fixed_part, response = feature)
                  required_cols <- c(feature, fixed_effects)
                  clean_data <- data %>%
                    drop_na(all_of(required_cols))

                  model <- lm(fixed_formula, data = clean_data)

                  extract_model_results(
                    model,
                    feature,
                    note = "fixed_effects_only"
                  )
                },
                error = function(e4) {
                  # Return a minimal tibble with NA values when all models fail
                  tibble(
                    effect = "fixed",
                    term = paste0(fixed_effects[1], "NA"),
                    estimate = NA_real_,
                    std.error = NA_real_,
                    statistic = NA_real_,
                    df = NA_real_,
                    p.value = NA_real_,
                    feature = feature,
                    note = "model_failed"
                  )
                }
              )
            }
          )
        }
      )
    }
  )
}

# Debug function to identify why the model is failing
debug_model_fitting <- function(
  feature,
  data,
  fixed_effects = c("tissue", "frame_start")
) {
  cat("=== DEBUGGING MODEL FITTING ===\n")

  # 1. Check if feature exists and has correct name
  cat("1. Checking feature name and data...\n")
  cat("Feature requested:", feature, "\n")
  cat("Available columns:", paste(names(data), collapse = ", "), "\n")

  # Check for typo in your feature name
  if (
    !"angular_velocity_var" %in% names(data) &&
      "angular_velecity_var" %in% names(data)
  ) {
    cat(
      "WARNING: Found 'angular_velecity_var' - did you mean 'angular_velocity_var'?\n"
    )
  }

  if (!feature %in% names(data)) {
    cat("ERROR: Feature", feature, "not found in data!\n")
    return("Feature not found")
  }

  # 2. Check required columns
  required_cols <- c(feature, fixed_effects, "date", "video", "particle")
  missing_cols <- setdiff(required_cols, names(data))

  cat("\n2. Checking required columns...\n")
  cat("Required columns:", paste(required_cols, collapse = ", "), "\n")
  if (length(missing_cols) > 0) {
    cat("ERROR: Missing columns:", paste(missing_cols, collapse = ", "), "\n")
    return("Missing required columns")
  }
  cat("All required columns present ✓\n")

  # 3. Check data quality
  cat("\n3. Checking data quality...\n")
  cat("Total rows:", nrow(data), "\n")

  # Check feature values
  feature_values <- data[[feature]]
  cat("Feature summary:\n")
  print(summary(feature_values))
  cat("Infinite values:", sum(is.infinite(feature_values)), "\n")
  cat("NA values:", sum(is.na(feature_values)), "\n")
  cat("Finite values:", sum(is.finite(feature_values)), "\n")

  # Check fixed effects
  for (fe in fixed_effects) {
    cat("\nFixed effect '", fe, "':\n", sep = "")
    fe_values <- data[[fe]]
    if (is.numeric(fe_values)) {
      print(summary(fe_values))
      cat("NA values:", sum(is.na(fe_values)), "\n")
    } else {
      cat("Levels:", paste(unique(fe_values), collapse = ", "), "\n")
      cat("NA values:", sum(is.na(fe_values)), "\n")
    }
  }

  # 4. Check data after cleaning
  cat("\n4. Checking data after cleaning...\n")
  clean_data <- data %>%
    filter(is.finite(.data[[feature]])) %>%
    drop_na(all_of(required_cols))

  cat("Rows after cleaning:", nrow(clean_data), "\n")

  if (nrow(clean_data) < 10) {
    cat("ERROR: Too few rows after cleaning (", nrow(clean_data), ")\n")
    return("Insufficient data after cleaning")
  }

  # 5. Check random effects structure
  cat("\n5. Checking random effects grouping...\n")
  random_effects_summary <- clean_data %>%
    group_by(date, video, particle) %>%
    summarise(n = n(), .groups = "drop")

  cat(
    "Number of unique date/video/particle combinations:",
    nrow(random_effects_summary),
    "\n"
  )
  cat(
    "Observations per group - Min:",
    min(random_effects_summary$n),
    "Max:",
    max(random_effects_summary$n),
    "Mean:",
    round(mean(random_effects_summary$n), 2),
    "\n"
  )

  # Check if we have enough groups
  if (nrow(random_effects_summary) < 5) {
    cat(
      "WARNING: Very few random effect groups (",
      nrow(random_effects_summary),
      ")\n"
    )
  }

  # 6. Try the simplest model first
  cat("\n6. Testing simplest model (lm)...\n")

  tryCatch(
    {
      # Create interaction formula
      if (length(fixed_effects) > 1) {
        interaction_terms <- paste(fixed_effects, collapse = " * ")
        fixed_part <- interaction_terms
      } else {
        fixed_part <- fixed_effects[1]
      }

      cat("Formula:", paste(feature, "~", fixed_part), "\n")

      simple_model <- lm(
        reformulate(fixed_part, response = feature),
        data = clean_data
      )
      cat("Simple linear model: SUCCESS ✓\n")
      cat("Model summary:\n")
      print(summary(simple_model))

      return("Debug complete - simple model works")
    },
    error = function(e) {
      cat("ERROR in simple model:", e$message, "\n")
      return(paste("Simple model failed:", e$message))
    }
  )
}

# Also create a simplified version of your original function for testing
fit_model_interaction_debug <- function(
  feature,
  data,
  fixed_effects = "tissue",
  use_temporal_correlation = TRUE
) {
  # Load required libraries
  require(lme4)
  require(nlme)
  require(broom)
  require(broom.mixed)
  require(dplyr)

  cat("Starting model fitting for feature:", feature, "\n")

  # Create formula with interactions between all fixed effects
  if (length(fixed_effects) > 1) {
    interaction_terms <- paste(fixed_effects, collapse = " * ")
    fixed_part <- interaction_terms
  } else {
    fixed_part <- fixed_effects[1]
  }

  cat("Fixed effects formula:", fixed_part, "\n")

  # Helper to extract and format model results
  extract_model_results <- function(model, feature, note = NA_character_) {
    cat(
      "Extracting results with note:",
      ifelse(is.na(note), "none", note),
      "\n"
    )

    tryCatch(
      {
        tidy_out <- tidy(model, effects = "fixed") %>%
          filter(term != "(Intercept)") %>%
          mutate(feature = feature)

        if (!is.na(note)) {
          tidy_out <- tidy_out %>% mutate(note = note)
        }

        cat("Successfully extracted", nrow(tidy_out), "fixed effects\n")
        return(tidy_out)
      },
      error = function(e) {
        cat("ERROR in extract_model_results:", e$message, "\n")
        stop(e)
      }
    )
  }

  tryCatch(
    {
      # Check that all required columns exist
      required_cols <- c(feature, fixed_effects, "date", "video", "particle")
      missing_cols <- setdiff(required_cols, names(data))
      if (length(missing_cols) > 0) {
        stop(paste("Missing columns:", paste(missing_cols, collapse = ", ")))
      }

      cat("All required columns present\n")

      clean_data <- data %>%
        filter(is.finite(.data[[feature]])) %>%
        drop_na(all_of(required_cols))

      cat("Data cleaned, rows:", nrow(clean_data), "\n")

      if (nrow(clean_data) < 100) {
        # Lower threshold for debugging
        stop(paste(
          "Insufficient data after removing infinite values:",
          nrow(clean_data),
          "rows"
        ))
      }

      # Skip temporal correlation for now, go straight to lmer
      cat("Attempting lmer model...\n")

      model_formula <- reformulate(
        paste(fixed_part, "+ (1 | date/video/particle)"),
        response = feature
      )

      cat("Model formula:", deparse(model_formula), "\n")

      model <- lmer(
        model_formula,
        data = clean_data,
        control = lmerControl(optimizer = "bobyqa")
      )

      cat("lmer model fitted successfully\n")

      if (isSingular(model)) {
        warning(paste(
          "Singular fit for",
          feature,
          "- random effects may be unreliable"
        ))
      }

      return(extract_model_results(model, feature))
    },
    error = function(e1) {
      cat("lmer failed, error:", e1$message, "\n")
      cat("Trying simplified random effects...\n")

      tryCatch(
        {
          simple_formula <- reformulate(
            paste(fixed_part, "+ (1 | date)"),
            response = feature
          )
          required_cols <- c(feature, fixed_effects, "date")
          clean_data <- data %>%
            drop_na(all_of(required_cols))

          cat("Simplified model formula:", deparse(simple_formula), "\n")

          model <- lmer(
            simple_formula,
            data = clean_data,
            control = lmerControl(optimizer = "bobyqa")
          )

          cat("Simplified lmer model fitted successfully\n")

          return(extract_model_results(
            model,
            feature,
            note = "simplified_random_effects"
          ))
        },
        error = function(e2) {
          cat("Simplified lmer failed, error:", e2$message, "\n")
          cat("Trying fixed effects only...\n")

          tryCatch(
            {
              fixed_formula <- reformulate(fixed_part, response = feature)
              required_cols <- c(feature, fixed_effects)
              clean_data <- data %>%
                drop_na(all_of(required_cols))

              cat("Fixed effects formula:", deparse(fixed_formula), "\n")

              model <- lm(fixed_formula, data = clean_data)

              cat("Fixed effects model fitted successfully\n")

              return(extract_model_results(
                model,
                feature,
                note = "fixed_effects_only"
              ))
            },
            error = function(e3) {
              cat("All models failed. Final error:", e3$message, "\n")

              # Return detailed error information
              tibble(
                effect = "fixed",
                term = paste0(fixed_effects[1], "_FAILED"),
                estimate = NA_real_,
                std.error = NA_real_,
                statistic = NA_real_,
                df = NA_real_,
                p.value = NA_real_,
                feature = feature,
                note = paste("model_failed:", e3$message)
              )
            }
          )
        }
      )
    }
  )
}
