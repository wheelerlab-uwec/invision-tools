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


fit_model_screenchip <- function(
  feature,
  data,
  fixed_effects,
  control_level = "No Drug"
) {
  data <- data %>%
    mutate(treatment = relevel(factor(treatment), ref = control_level))

  # Build fixed effects formula with interactions
  if (length(fixed_effects) == 1) {
    fixed_part <- fixed_effects[1]
  } else {
    main_effects <- paste(fixed_effects, collapse = " + ")
    interactions <- paste(fixed_effects, collapse = " * ")
    fixed_part <- interactions
  }

  formula <- reformulate(
    paste(fixed_part, "+ (1 | date/screenchip/well/particle)"),
    response = feature
  )

  # Strategy 1: Try original model
  tryCatch(
    {
      clean_data <- data %>%
        filter(is.finite(.data[[feature]])) %>% # Remove Inf, -Inf, NaN
        drop_na(all_of(c(
          feature,
          fixed_effects,
          "date",
          "screenchip",
          "well",
          "particle"
        )))

      # Check if we have enough data left
      if (nrow(clean_data) < 1000) {
        stop("Insufficient data after removing infinite values")
      }

      model <- withCallingHandlers(
        lmer(
          formula,
          data = clean_data,
          control = lmerControl(optimizer = "bobyqa")
        ),
        warning = function(w) {
          if (grepl("rank deficient", w$message)) {
            message(paste(
              "Rank deficiency detected for",
              feature,
              "- dropping coefficients"
            ))
          } else {
            warning(w)
          }
          invokeRestart("muffleWarning")
        }
      )

      # Check if model is singular but still usable
      if (isSingular(model)) {
        warning(paste(
          "Singular fit for",
          feature,
          "- random effects may be unreliable"
        ))
      }

      return(
        tidy(model, effects = "fixed") %>%
          filter(str_detect(term, "^treatment")) %>%
          mutate(
            feature = feature,
            comparison = paste0(term, " vs ", control_level)
          )
      )
    },
    error = function(e1) {
      # Strategy 2: Try simplified random effects structure
      tryCatch(
        {
          simple_formula <- reformulate(
            paste(fixed_part, "+ (1 | date)"),
            response = feature
          )
          clean_data <- data %>%
            drop_na(all_of(c(feature, fixed_effects, "date")))

          model <- lmer(
            simple_formula,
            data = clean_data,
            control = lmerControl(optimizer = "bobyqa")
          )

          return(
            tidy(model, effects = "fixed") %>%
              filter(str_detect(term, "^treatment")) %>%
              mutate(
                feature = feature,
                comparison = paste0(term, " vs ", control_level),
                note = "simplified_random_effects"
              )
          )
        },
        error = function(e2) {
          # Strategy 3: Fall back to fixed effects only (regular lm)
          tryCatch(
            {
              fixed_formula <- reformulate(fixed_part, response = feature)
              clean_data <- data %>%
                drop_na(all_of(c(feature, fixed_effects)))

              model <- lm(fixed_formula, data = clean_data)

              return(
                tidy(model) %>%
                  filter(str_detect(term, "^treatment")) %>%
                  mutate(
                    feature = feature,
                    comparison = paste0(term, " vs ", control_level),
                    note = "fixed_effects_only",
                    original_error = as.character(e1$message)
                  )
              )
            },
            error = function(e3) {
              # Final fallback: return NA results
              levels <- unique(data$treatment)
              contrasts <- setdiff(levels, control_level)

              return(tibble(
                effect = "fixed",
                term = paste0("treatment", contrasts),
                estimate = NA_real_,
                std.error = NA_real_,
                statistic = NA_real_,
                df = NA_real_,
                p.value = NA_real_,
                feature = feature,
                comparison = paste0(
                  "treatment",
                  contrasts,
                  " vs ",
                  control_level
                ),
                note = "model_failed"
              ))
            }
          )
        }
      )
    }
  )
}
