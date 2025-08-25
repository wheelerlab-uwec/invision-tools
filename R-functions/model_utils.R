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

    return(list(
      results = tidy_out,
      model = model,
      model_type = class(model)[1],
      note = ifelse(is.na(note), "standard", note)
    ))
  }

  tryCatch(
    {
      # Check that all required columns exist
      required_cols <- c(feature, fixed_effects, "date", "particle")
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
              random = ~ 1 | date / particle,
              correlation = corAR1(form = ~ 1 | date / particle),
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
          paste(fixed_part, "+ (1 | date/particle)"),
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
            "particle"
          )
          clean_data <- data %>%
            drop_na(all_of(required_cols))

          model <- lmer(
            reformulate(
              paste(fixed_part, "+ (1 | date/particle)"),
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
                  # Return a minimal list with NA values when all models fail
                  list(
                    results = tibble(
                      effect = "fixed",
                      term = paste0(fixed_effects[1], "NA"),
                      estimate = NA_real_,
                      std.error = NA_real_,
                      statistic = NA_real_,
                      df = NA_real_,
                      p.value = NA_real_,
                      feature = feature,
                      note = "model_failed"
                    ),
                    model = NULL,
                    model_type = "failed",
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
