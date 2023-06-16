import pandas as pd 
import numpy as np
import logging
import os

DATA_PATH = "data_integrity.xlsx"

df_dict = pd.read_excel(DATA_PATH, sheet_name=None)


# set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(os.path.join("logs", "checker.log"), mode="w")

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                              datefmt='%d-%b-%y %H:%M:%S')
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)


class Checker:
    def __init__(self, data_path) -> None:
        self.checks = {}
        self.data_path = data_path
        
        self.df_dict = pd.read_excel(self.data_path, sheet_name=None)
        self.EDC = self.df_dict['EDC_DATA']
        self.TEG = self.df_dict['TEG_DATA']
        self.LAB = self.df_dict['LAB_DATA']
        
        logger.debug("Data loaded")
        self.TEG['TEG_RUN_DATE_TIME'] = pd.to_datetime(self.TEG['TEG_RUN_DATE_TIME'])
        self.EDC['Last_drug_administration_date_time'] = pd.to_datetime(self.EDC['Last_drug_administration_date_time'])
        self.EDC['WBC_date_time'] = pd.to_datetime(self.EDC['WBC_date_time'])
        logger.debug("Dates converted to datetime")
        
        self.TEG['UID'] = self.TEG['TEG_SUB_ID'] + "_" + self.TEG['TEG_SAMPLE_NUM'].astype(str)
        self.TEG.set_index("UID", inplace=True)  
                
        self.EDC_AND_LAB = self.EDC.join(self.LAB)
    
    def DM_input(self): # DM
        pass 
    
    def PD_comment(self): # PD
        pass
    
    def structural_integrity(self): # SI
        pass 
    
    def time_between_replicate_runs(self): # REP
        def rep_check(x):
            if len(x) < 2:
                return "Missing Run Time"
            
            time_between_runs = abs(x.values[1] - x.values[0]) / np.timedelta64(1, 'm') 
            
            return time_between_runs

        res = self.TEG.reset_index().groupby(['UID', "TEST_NAME"])["TEG_RUN_DATE_TIME"].apply(rep_check)

        res_dict = res.reset_index()
        res_dict["UID_TEST_NAME"] = res_dict["UID"] + "_" + res_dict["TEST_NAME"]
        res_dict = res_dict[['UID_TEST_NAME', "TEG_RUN_DATE_TIME"]] \
                            .set_index("UID_TEST_NAME") \
                            .to_dict()["TEG_RUN_DATE_TIME"]
        res_dict


        # ! from copilot, later check better
        new_dict = {}
        
        for key, value in res_dict.items():
            sample_id, subject_id, test_name = key.split("_")
            if sample_id not in new_dict:
                new_dict[sample_id] = {}
            if subject_id not in new_dict[sample_id]:
                new_dict[sample_id][subject_id] = {"REP": {}}
            if test_name not in new_dict[sample_id][subject_id]:
                new_dict[sample_id][subject_id]["REP"][test_name] = {}
            if isinstance(value, float):
                new_dict[sample_id][subject_id]["REP"][test_name]["status"] = "OK"
                new_dict[sample_id][subject_id]["REP"][test_name]["run_time"] = value
            else:
                new_dict[sample_id][subject_id]["REP"][test_name]["status"] = "Missing Run Time"
                new_dict[sample_id][subject_id]["REP"][test_name]["run_time"] = "NA"
    
        return new_dict
    def data_quality_requirement(self): # DQR
        pass 
    
    def contribution_to_final_dataset(self): # FADS
        pass 
    
    def AFXA_r_contribution(self): # AFXA
        pass 
    
    def DTI_R_contribution(self): # DTI
        pass
    
    def lab(self): # might be only one comment, might be multiple keys 
        pass
    
    def EDC_timing(self): # Last_drug_administration_date_time < WBC_date_time
        pass 
        
        
    # def administered_after_being_drawn(self):
    #     msg = "Checking if administered date is after drawn date"
    #     logger.info(msg)
        
    #     status = "OK"
        
    #     if self.EDC['Last_drug_administration_date_time'] > self.EDC['WBC_date_time']:
    #         status = "Administered date is after drawn date (EDC)"    
    #         logger.warning(status)
        
    #     self.checks['administered_after_being_drawn'] = status
               
    
    # EDC and LAB
    # def compound_name_mismatch(self):
    #     def mismatch_check_helper(x):
    #         if x['Cohort'] == "A":
    #             msg = "Healthy"
    #         else:
    #             print(x["Drug_compound"], x["LAB_compound"])
    #             if (pd.isna(x["Drug_compound"])) and (pd.isna(x["LAB_compound"])):
    #                 msg = "Drugs from both EDC and LAB are missing"
    #             elif pd.isna(x["Drug_compound"]):
    #                 msg = "Drug from EDC is missing"
    #             elif pd.isna(x["LAB_compound"]):
    #                 msg = "Drug from LAB is missing"
    #             elif x["Drug_compound"] != x["LAB_compound"]:
    #                 msg = "Drugs from EDC and LAB do not match"
    #             else:
    #                 msg = "OK"    
    #         return msg
    
    #     msg = "Checking if compound name in EDC and LAB match"
    #     logger.info(msg)
        
    #     self.EDC_AND_LAB.apply(mismatch_check_helper, axis=1)
        
    #     if self.EDC['Drug_compound'] != self.LAB['LAB_compound']:
    #         status = "Compound name mismatch in EDC and LAB"
    #         logger.warning("Administered date is after drawn date")
        
    #     self.checks['compound_name_mismatch'] = status
    
    
    # TEG
    # def r_time_checks(self):
    #     completed_or_not = self.TEG.groupby("UID")['TEG_STATUS'].apply(lambda x: np.all(x == "Test Completed"))  \
    #                                .replace(False, "Not all tests completed") \
    #                                .reset_index()
                                   
    #     not_completed = completed_or_not[completed_or_not["TEG_STATUS"] == "Not all tests completed"]
    #     completed = completed_or_not[completed_or_not['TEG_STATUS'] == True]

    #     completed_ids = completed["UID"].to_list()
        
    #     completed = self.TEG[self.TEG.index.isin(completed_ids)]

    #     res = completed.groupby(["UID", "TEST_NAME"]).agg(delta_r=("TEG_VALUE_R", lambda x: abs(x[0] - x[1])), 
    #                                                       mean_r= ("TEG_VALUE_R", lambda x: np.mean(x))) \
        
    #     res = res.reset_index()

    #     res['difference_over_mean_check'] = np.where((res['delta_r'] / res['mean_r']) <= 0.4, "OK", "FAIL")


    
    

ch = Checker(DATA_PATH)

ch.administered_after_being_drawn()
ch.compound_name_mismatch()

print(ch.checks)
        
        
        