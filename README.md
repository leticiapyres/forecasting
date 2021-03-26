# TSPerf

TSPerf is a framework that allows discovery and comparison of various time-series forecasting algorithms and architectures on a cloud-based environment. This framework allows data scientists to discover the best approach that fits their use case from cost, time and quality perspective.
 TSPerf framework is designed to facilitate data science community participation and contribution through the development of benchmark implementations against a given set of forecasting problems and datasets. Benchmark implementations are measured in terms of standard metrics of model accuracy, training cost and model training time. Each implementation includes all the necessary instructions and tools that ensure its reproducibility on Azure customer's subscription. We plan to leverage TSPerf to propose a new time-series forecasting track in [MLPerf](https://mlperf.org/).
The following table summarizes benchmarks that are currently included in TSPerf.

Benchmark                                   |  Dataset               |  Benchmark directory
--------------------------------------------|------------------------|---------------------------------------------
Probabilistic electricity load forecasting  |  GEFCom2017            |  `energy_load/GEFCom2017-D_Prob_MT_Hourly`
Retail sales forecasting                    |  Orange Juice dataset  |  `retail_sales/OrangeJuice_Pt_3Weeks_Weekly`




A complete documentation of TSPerf, along with the instructions for submitting and reviewing benchmark implementations, can be found [here](./docs/tsperf_rules.md). The tables below show performance of benchmark implementations that are developed so far. These tables are referred to as *performance boards*. Source code of benchmark implementations and instructions for reproducing their performance can be found in submission folders, which are linked in the last column of performance boards.

## Probabilistic energy forecasting performance board


The following table lists the current submision for the energy foercasting and their respective performances.


Submission Name                                                                 |  Pinball Loss  |  Training and Scoring Time (sec)  |  Training and Scoring Cost($)  |  Architecture                                 |  Framework                         |  Algorithm                            |  Uni/Multivariate  |  External Feature Support
--------------------------------------------------------------------------------|----------------|-----------------------------------|--------------------------------|-----------------------------------------------|------------------------------------|---------------------------------------|--------------------|--------------------------
[Baseline](energy_load%2FGEFCom2017_D_Prob_MT_hourly%2Fsubmissions%2Fbaseline)  |  84.11         |  444                              |  0.0474                        |  Linux DSVM (Standard D8s v3 - Premium SSD)   |  quantreg package of R             |  Linear Quantile Regression           |  Multivariate      |  Yes
[GBM](energy_load%2FGEFCom2017_D_Prob_MT_hourly%2Fsubmissions%2FGBM)            |  78.71         |  888                              |  0.0947                        |  Linux DSVM (Standard D8s v3 - Premium SSD)   |  gbm package of R                  |  Gradient Boosting Decision Tree      |  Multivariate      |  Yes
[QRF](energy_load%2FGEFCom2017_D_Prob_MT_hourly%2Fsubmissions%2Fqrf)            |  76.48         |  22709                            |  19.03                         |   Linux DSVM (F72s v2 - Premium SSD)          |   scikit-garden package of Python  |   Quantile Regression Forest          |   Multivariate     |   Yes
[FNN](energy_load%2FGEFCom2017_D_Prob_MT_hourly%2Fsubmissions%2Ffnn)            |  79.27         |  4604                             |  0.4911                        |   Linux DSVM (Standard D8s v3 - Premium SSD)  |   qrnn package of R                |   Quantile Regression Neural Network  |   Multivariate     |   Yes


The following chart compares the submissions performance on accuracy in Pinball Loss vs. Training and Scoring cost in $:

 
![EnergyPBLvsTime](./docs/images/Energy-Cost.png)




## Retail sales forecasting performance board


The following table lists the current submision for the retail foercasting and their respective performances.


Submission Name                                                                             |  MAPE (%)  |  Training and Scoring Time (sec)  |  Training and Scoring Cost ($)  |  Architecture                                |  Framework                   |  Algorithm                                                          |  Uni/Multivariate  |  External Feature Support
--------------------------------------------------------------------------------------------|------------|-----------------------------------|---------------------------------|----------------------------------------------|------------------------------|---------------------------------------------------------------------|--------------------|--------------------------
[Baseline](retail_sales%2FOrangeJuice_Pt_3Weeks_Weekly%2Fsubmissions%2Fbaseline)            |  109.67    |  114.06                           |  0.003                          |  Linux DSVM(Standard D2s v3 - Premium SSD)   |  forecast package of R       |  Naive Forecast                                                     |  Univariate        |  No
[AutoARIMA](retail_sales%2FOrangeJuice_Pt_3Weeks_Weekly%2Fsubmissions%2FARIMA)              |  70.80     |  265.94                           |  0.0071                         |  Linux DSVM(Standard D2s v3 - Premium SSD)   |  forecast package of R       |  Auto ARIMA                                                         |  Multivariate      |  Yes
[ETS](retail_sales%2FOrangeJuice_Pt_3Weeks_Weekly%2Fsubmissions%2FETS)                      |  70.99     |  277                              |  0.01                           |  Linux DSVM(Standard D2s v3 - Premium SSD)   |  forecast package of R       |  ETS                                                                |  Multivariate      |  No
[MeanForecast](retail_sales%2FOrangeJuice_Pt_3Weeks_Weekly%2Fsubmissions%2FMeanForecast)    |  70.74     |  69.88                            |  0.002                          |  Linux DSVM(Standard D2s v3 - Premium SSD)   |  forecast package of R       |  Mean forecast                                                      |   Univariate       |  No
[SeasonalNaive](retail_sales%2FOrangeJuice_Pt_3Weeks_Weekly%2Fsubmissions%2FSeasonalNaive)  |  165.06    |  160.45                           |  0.004                          |  Linux DSVM(Standard D2s v3 - Premium SSD)   |  forecast package of R       |  Seasonal Naive                                                     |  Univariate        |  No
[LightGBM](retail_sales%2FOrangeJuice_Pt_3Weeks_Weekly%2Fsubmissions%2FLightGBM)            |  36.28     |  625.10                           |  0.0167                         |  Linux DSVM (Standard D2s v3 - Premium SSD)  |  lightGBM package of Python  |  Gradient Boosting Decision Tree                                    |  Multivariate      |  Yes
[DilatedCNN](retail_sales%2FOrangeJuice_Pt_3Weeks_Weekly%2Fsubmissions%2FDilatedCNN)        |  37.09     |  413                              |  0.1032                         |  Ubuntu VM(NC6 - Standard HDD)               |  Keras and Tensorflow        |  Python + Dilated convolutional neural network                      |   Multivariate     |  Yes
[RNN Encoder-Decoder](retail_sales%2FOrangeJuice_Pt_3Weeks_Weekly%2Fsubmissions%2FRNN)      |  37.68     |  669                              |  0.2                            |  Ubuntu VM(NC6 - Standard HDD)               |  Tensorflow                  |  Python + Encoder-decoder architecture of recurrent neural network  |   Multivariate     |  Yes






The following chart compares the submissions performance on accuracy in %MAPE vs. Training and Scoring cost in $:

 
![EnergyPBLvsTime](./docs/images/Retail-Cost.png)




