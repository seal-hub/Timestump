# Data Capturing Accuracy

## Results

In this study, we assess the accuracy of the captured data by *TIMESTAMP*. To ensure a comprehensive evaluation of data capturing across apps with various rendering mechanisms, we leverage a dataset from a previous study [1] that investigated proper timing in automated GUI testing for different apps. This study identified three distinct states in app transitions: **T1: implicit loading, T2: explicit loading, and T3: in transition**. From their findings, we randomly selected five apps to encompass all types of transitions. The dataset for this study is presented in Table below.

- *C1: Appearing Content*
- *C2: Disappearing Content*
- *C3: Short-Lived Content*
- *C4: Moving Content*
- *C5: Content Modification*

|           App Name           |     App Package Name      | Installs | Transitions | Changes |     Category     |
| :--------------------------: | :-----------------------: | :------: | :---------: | :-----: | :--------------: |
|      Simple Alarm Clock      |     com.better.alarm      |   >1M    |     T3      | C3, C5  |      Tools       |
|           CBS News           |      com.cbsnews.ott      |   >1M    |   T2, T3    |   C1    | News & Magazines |
|         Chick-fil-A®         | com.chickfila.cfaflagship |   >10M   |   T2, T3    | C1, C2  |   Food & Drink   |
| GoodRx: Prescription Coupons |        com.goodrx         |   >10M   |     T3      |   C5    |     Medical      |
| Investing.com: Stock Market  | com.fusionmedia.investing |   >50M   | T1, T2, T3  |   C5    |     Finance      |

To assess the data capturing process, one author manually navigated through each app, capturing three distinct states. This manual exploration ensured the inclusion of states resulting in various transition types and dynamic content changes. Subsequently, we employed *TIMESTEAMP* to traverse each app state, interact with actionable elements, and capture data.  Two authors independently reviewed the captured data to confirm alignment with our definitions of the first and last frames, and manually counting the number of failures. Out of 117 evaluated actions, we identified no errors.

## References

[1] S. Feng, M. Xie, and C. Chen, “Efficiency matters: Speeding up automated testing with gui rendering inference,” in 2023 IEEE/ACM 45th International Conference on Software Engineering (ICSE). IEEE, 2023, pp. 906–918.