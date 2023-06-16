# DOAC_data_integrity
14 June, 23 | To-Do 


Assumes that should get a path of the data as input and return JSON
something like
```python
{
    "Subject ID": # 507-...
    {
        "Sample ID": # 001
        {
            "DM_input": "OK",
                # if there were more than 2 runs (criteria may change in future)
            "PD": "OK",
                {
                    "status": "OK", # if PD col is `EDC` is empty
                    "comment": "some comment", # value of PD col
                }
            "SI": "OK", # structural integrity
                # number of runs received (and it runs were problematic)

            "REP:
                # whether or not 2 replicate runs have distance more than 10 minutes
                # or data is missing
                {
                    "DTI": 
                        {
                            "status": "OK", # or "Missing Run Time"
                            "difference": 10, # float or "NA" (if status is "Missing Run Time")
                        }
                    "AFXa": # same as DTI
                }
            "DQR": "OK",
                # for now just return panir
            "FADS": "OK",
                # if AFX_a and "DTI_a" are both OK, else ...
            "AFXa_r": "OK",
                # only one run for a compound
                # difference over average check
                # 4 sigma deviation check
            "DTI_r": "OK",
                # same as for AFXa_r
            "LAB_comment": "OK",
                # is there a compound name mismatch
                # reportable res == 0
                # reportable res < LLOQ
            "EDC_timing": "OK",
                # last drug administration date > WBC date
        }
        "Sample Id": # 002
        ...
        
    }
}
```

Below is outdated

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