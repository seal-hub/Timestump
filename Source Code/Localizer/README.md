# Localizer
## Setup
1. Install all the required packages through **requirements.txt**
2. Python version 3.12
3. Currently, the dataset folder is set as "app_scenarios". Inside this folder, the structure should be:

   ```
   App Name
   └── Scenario Name
     ├── First Frame
     ├── Final Frame 
     ├── AccessibilityEvents
     ...
   ```
4. Run the localizer to get a list of problematic, dynamic content changes by using **python localizer.py**, or simply import it into your IDE and hit the run button
5. Results can be found under folder "results". Images starting with *sl* indicate problematic short-lived elements, while those beginning with *a* represent appearing elements, *d* for disappearing elements, *m* for moving elements, and *ca* for content modifications. Each problematic dynamic element is highlighted with a box in a distinct color.

