# Introduction to Tidyverts with the Australian retail turnover data

This case study is meant to be a quick introduction to time series analysis in R, using the [**Tidyverts**](https://tidyverts.org) family of R packages. Tidyverts is the work of Rob Hyndman, professor of statistics at Monash University, and his team. The family is intended to be the next-generation replacement for the very popular `forecast` package, and is currently under active development.

The main reference for Tidyverts is the textbook [_Forecasting: Principles and Practice, 3rd Edition_](https://otexts.com/fpp3/), by Hyndman and Athanasopoulos. It's highly recommended to read that in conjunction with working through the notebooks here.

## Summary

The R Notebooks in this directory are as follows. Each notebook also has a corresponding HTML file, which is the rendered output from running the code. This is best viewed on our [https://microsoft.github.io/forecasting/](https://microsoft.github.io/forecasting/) GitHub Page.

- [`01_explore.Rmd`](01_explore.Rmd) [`(.html)`](01_explore.nb.html) introduces the `aus_retail` dataset and performs some exploratory analysis, generating graphs and tables.
- [`02_model.Rmd`](02_model.Rmd) [`(.html)`](02_model.nb.html) fits a range of simple time series models to the data and discusses the results, including various issues relevant to forecasting in general.

## Package installation

The following packages and their dependencies are needed to run the notebooks in this directory:


| Framework | Packages |
| --------- | -------- |
| Tidyverse | dplyr, tidyr, ggplot2 |
| Tidyverts | tsibble, tsibbledata, fabletools, fable, feasts |
| Future    | future, future.apply |
| Other     | urca, rmarkdown, distributional, devtools (see below) |

It's likely that you will already have many of these (particularly the Tidyverse packages) installed. However, currently (June 2020) the notebooks do require the _development_ versions of the Tidyverts packages; these can be installed from GitHub using the devtools package.

```r
install.packages("tidyverse")
install.packages(c("future", "future.apply"))
install.packages(c("rmarkdown", "urca"))

# install Tidyverts packages from GitHub
install.packages("devtools")

devtools::install_github("tidyverts/tsibble@a19cda281c3f1e0061b5b0de93b059c52052ebda")
devtools::install_github("tidyverts/tsibbledata@b06a965b788722157a149296c47f821c99cc41f0")
devtools::install_github("mitchelloharawild/distributional@e668b520b415f417f71eacd7e1e940561eecffd6")
devtools::install_github("tidyverts/fabletools@864b2daa983446017f2ed757a3b8889b935cc2cb")
devtools::install_github("tidyverts/fable@d2600c151fde1609cc491d8f94bd136c71f87523")
devtools::install_github("tidyverts/feasts@f006746effa10bc223479441ebede136ca016b11")
```

## Acknowledgements

Mitchell O'Hara-Wild (@mitchelloharawild) provided many comments that helped improve this example.
