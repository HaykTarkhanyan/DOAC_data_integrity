
# ! there is a lot of code duplication, need to refactor later
import pandas as pd 
import numpy as np
import logging
import json
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
        self.checks_list = []
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
        
        self.EDC["UID"] = self.EDC["Subject_ID"] + "_" + self.EDC["Sample_Num"].astype(str)
        self.EDC.set_index("UID", inplace=True)
        
        self.LAB['UID'] = self.LAB['LAB_SUB_ID'] + "_" + self.LAB['LAB_SAMPLE_NUM'].astype(str)
        self.LAB.set_index("UID", inplace=True)
        
        self.EDC_AND_LAB = self.EDC.join(self.LAB)
    
    def DM_input(self): # DM
        pass
    
    def PD_comment(self): # PD
        # ? how should I return this

        def protocol_deviation(x):
            no_code = pd.isna(x['Protocol_deviation_code'])
            no_description = pd.isna(x['Protocol_deviation_description'])
            
            if no_code and no_description:
                return "No Protocol Deviation"
            elif no_code and (not no_description):
                return x['Protocol_deviation_description']
            elif (not no_code) and no_description:
                return x['Protocol_deviation_code']
            else:
                return str(x['Protocol_deviation_code']) + " - " + x['Protocol_deviation_description']
        
        res = self.EDC.apply(protocol_deviation, axis=1)

        res_dict = res.to_dict()
        
        test_name = "PD"
        new_dict = {}
        for key, value in res_dict.items():
            sample_id, subject_id = key.split("_")
            if sample_id not in new_dict:
                new_dict[sample_id] = {}
            if subject_id not in new_dict[sample_id]:
                new_dict[sample_id][subject_id] = {}
            if test_name not in new_dict[sample_id][subject_id]:
                new_dict[sample_id][subject_id][test_name] = {}
            
            new_dict[sample_id][subject_id][test_name]["status"] = value

        self.checks_list.append(new_dict)

    def structural_integrity(self): # SI
        # !
        # ? What if one run is error and one is aborted? 
        def SI_check(x):
            if len(x) < 2:
                return "Received <2 runs"
            if len(x) > 2:
                return "Received >2 runs"
            if all(x.values == "Test Completed"):
                return "Received 2 runs with completed status"
            if "Test Error" in x.values:
                return "Received 2 runs containing error status"    
            if "Test Aborted" in x.values:
                return "Received 2 runs containing aborted status"
                    
        res = self.TEG.reset_index().groupby(['UID', "TEST_NAME"])["TEG_STATUS"].apply(SI_check)

        check_name = "SI"
        col_name = "TEG_STATUS"

        res_dict = res.reset_index()
        res_dict["UID_TEST_NAME"] = res_dict["UID"] + "_" + res_dict["TEST_NAME"]
        res_dict = res_dict[['UID_TEST_NAME', col_name]] \
                            .set_index("UID_TEST_NAME") \
                            .to_dict()[col_name]

        new_dict = {}

        # ! from copilot, later check better
        for key, value in res_dict.items():
            sample_id, subject_id, test_name = key.split("_")
            if sample_id not in new_dict:
                new_dict[sample_id] = {}
            if subject_id not in new_dict[sample_id]:
                new_dict[sample_id][subject_id] = {check_name: {}}
            if test_name not in new_dict[sample_id][subject_id]:
                new_dict[sample_id][subject_id][check_name][test_name] = {}
            
            new_dict[sample_id][subject_id][check_name][test_name]["status"] = value

        self.checks_list.append(new_dict)
        return new_dict
        
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
                new_dict[sample_id][subject_id]["REP"][test_name]["difference"] = value
            else:
                new_dict[sample_id][subject_id]["REP"][test_name]["status"] = "Missing Run Time"
                new_dict[sample_id][subject_id]["REP"][test_name]["difference"] = "NA"
    
        self.checks_list.append(new_dict)
        return new_dict
    
    def data_quality_requirement(self): # DQR
        # ! this just return OK for all the records
        records = set(self.EDC.index.to_list() + self.TEG.index.to_list() 
                    + self.LAB.index.to_list())
        res_dict = {i: "OK" for i in records}

        test_name = "DQR"

        new_dict = {}
        for key, value in res_dict.items():
            sample_id, subject_id = key.split("_")
            if sample_id not in new_dict:
                new_dict[sample_id] = {}
            if subject_id not in new_dict[sample_id]:
                new_dict[sample_id][subject_id] = {}
            if test_name not in new_dict[sample_id][subject_id]:
                new_dict[sample_id][subject_id][test_name] = {}
            
            new_dict[sample_id][subject_id][test_name]["status"] = value

        self.checks_list.append(new_dict)
        return new_dict
        
    
    def contribution_to_final_dataset(self): # FADS
        pass 
    
    def AFXa_r_contribution(self): # AFXa
        pass 
    
    def DTI_R_contribution(self): # DTI
        pass
    
    def lab_LLOQ(self): # might be only one comment, might be multiple keys 
        res = (self.LAB["LAB_REP_results"] < self.LAB["LAB_LLOQ"]) \
               .replace({False: "OK", True: "Below LLOQ"})
        res_dict = res.to_dict()
        
        new_dict = self.make_json_nested(res_dict, "LAB_LLOQ")
        
        self.checks_list.append(new_dict)
        return new_dict
        
    def lab_edc_compound_mismatch(self): 
        def mismatch_check_helper(x):
            if x['Cohort'] == "A":
                msg = "Healthy"
            else:
                if (pd.isna(x["Drug_compound"])) and (pd.isna(x["LAB_compound"])):
                    msg = "Drugs from both EDC and LAB are missing"
                elif pd.isna(x["Drug_compound"]):
                    msg = "Drug from EDC is missing"
                elif pd.isna(x["LAB_compound"]):
                    msg = "Drug from LAB is missing"
                elif x["Drug_compound"] != x["LAB_compound"]:
                    msg = "Drugs from EDC and LAB do not match"
                else:
                    msg = "OK"    
            return msg

        res = self.EDC_AND_LAB.apply(mismatch_check_helper, axis=1)

        res_dict = res.to_dict()
        
        new_dict = self.make_json_nested(res_dict, "Compound Mismatch")
    
        self.checks_list.append(new_dict)
        return new_dict
        
    def EDC_timing(self): # Last_drug_administration_date_time < WBC_date_time
        res = self.EDC['Last_drug_administration_date_time'] > self.EDC['WBC_date_time']
        res.replace({False: "OK", True: "Administration > WBC"}, inplace=True)
        res_dict = res.to_dict()

        new_dict = self.make_json_nested(res_dict, "EDC_timing")
        
        self.checks_list.append(new_dict)
        return new_dict
    
    def run_all_checks(self):
        checks = ["DM_input", "PD_comment", "structural_integrity",  \
                  "time_between_replicate_runs", "data_quality_requirement", \
                  "contribution_to_final_dataset", "AFXa_r_contribution", "DTI_R_contribution", \
                  "lab_LLOQ", "lab_edc_compound_mismatch", "EDC_timing"]
        for check in checks:
            print(f"Running {check} check")
            getattr(self, check)()
        
        self.restructure_json()
        return self.checks
    
    def restructure_json(self):     
        # TODO: rename variables
        new_data = {}
        for item in self.checks_list:
            for course_code, runs in item.items():
                for run_id, tasks in runs.items():
                    for task_id, results in tasks.items():
                        for test_name, test_results in results.items():
                            if course_code not in new_data:
                                new_data[course_code] = {}
                            if run_id not in new_data[course_code]:
                                new_data[course_code][run_id] = {}
                            if task_id not in new_data[course_code][run_id]:
                                new_data[course_code][run_id][task_id] = {}
                            new_data[course_code][run_id][task_id][test_name] = test_results

        self.checks = new_data
    
    @staticmethod
    def make_json_nested(res_dict, test_name):
        """For handling simple cases like 
        '501-701-101_1': 'OK'

        will return
        {
            "501-701-101": 
            {
                "1": 
                {
                    f"test_name":
                    {
                        "status": "OK"    
                    }
                }
            }
        }

        """
        new_dict = {}
        for key, value in res_dict.items():
            sample_id, subject_id = key.split("_")
            if sample_id not in new_dict:
                new_dict[sample_id] = {}
            if subject_id not in new_dict[sample_id]:
                new_dict[sample_id][subject_id] = {}
            if test_name not in new_dict[sample_id][subject_id]:
                new_dict[sample_id][subject_id][test_name] = {}
            
            new_dict[sample_id][subject_id][test_name]["status"] = value

        return new_dict
            
    # def administered_after_being_drawn(self):
    #     msg = "Checking if administered date is after drawn date"
    #     logger.info(msg)
        
    #     status = "OK"
        
    #     if self.EDC['Last_drug_administration_date_time'] > self.EDC['WBC_date_time']:
    #         status = "Administered date is after drawn date (EDC)"    
    #         logger.warning(status)
        
    #     self.checks['administered_after_being_drawn'] = status
               
    
    
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


    

if __name__ == "__main__":    
    ch = Checker(DATA_PATH)
    # ch.administered_after_being_drawn()
    # ch.compound_name_mismatch()
    
    print(dir(ch))
    ch.time_between_replicate_runs()
    ch.structural_integrity()
    ch.PD_comment()

    ch.restructure_json()

    with open("checks_new_format.json", "w") as f:
        f.write(json.dumps(ch.checks, indent=4))
        
        
