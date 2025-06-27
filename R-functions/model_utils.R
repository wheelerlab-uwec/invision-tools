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
