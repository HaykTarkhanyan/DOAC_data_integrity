# DOAC_data_integrity
14 June, 23 | To-Do 


Assumes that should get a path of the data as input and return JSON
something like
```python
{
    "EDC":
    {
        "Drug administation and WBC draw times": "OK",
        "Drug compound and LAB compound": "MISMATCH"
    }
    "TEG":
    {
        "ratio of absolute difference between 2 runs (by compound) and the mean": "OK",
        ...
    }
}
```

## Checks to perform
### EDC
1. Last drug administration date > WBC date (took the drug after blood draw)
2. `Drug_compound` is different from `LAB_compound` (LAB_DATA)
   
## TEG
1. difference between `TEG_RUN_DATE_TIME` and `WBC_date_time` (EDC) is not between 10 and 120 minutes
2. `TEG_RUN_DATE_TIME` is before `WBC_date_time` (EDC) (my suggestion)

*check this only if `TEG_STATUS`=`Test Completed`*
3. ratio of absolute difference between 2 runs (by compound) and the mean is more than 0.4  
4. We define
   - delta_r = for given sample and compound the difference between r times
   - r_bar = average of difference between r time by compound for all samples
   - str_r = standard deviation of difference between r time by compound for all samples
   **CHECK**
   delta_r - r_bar > 4 * str_r (should be less than 4 standard deviations from the mean)
    
5. received only one run for a compound 
6. R_time is Na (I will make this more concrete later)

## LAB
1. `LAB_compound` is different from `Drug_compound` (EDC) (same as EDC's 2nd check)
2. `LAB_REP_results` == 0
3. `LAB_REP_results` < `LAB_LLOQ` 

## Other to-do
1. Report data from which sources(EDC, TEG, LAB) is present for each patient
2. Symmorise the data for patient via Spyder plot