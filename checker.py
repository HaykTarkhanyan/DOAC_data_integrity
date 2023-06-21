
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
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(os.path.join("logs", "checker_.log"), mode="w")

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                              datefmt='%d-%b-%y %H:%M:%S')
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)



class Checker:
    def __init__(self, data_path, output_folder="output") -> None:
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
        
        self.output_folder = "output"
        self.file_name = "data_integrity.json"
        
        
    def DM_input(self): # DM
        counts = self.TEG.index.value_counts()
        res_dict = counts.apply(lambda x: {"status": "OK" if x == 4 else "Fail", 
                                           "run_count": x}).to_dict()
        
        new_dict = self.make_json_nested(res_dict, "DM", dont_include_status_key=True)
        
        self.checks_list.append(new_dict)
        return new_dict
      
    
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
        # ? What if one run is error and one is aborted? 
        # Error is prioritized over aborted
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
    
    def AFXa_and_DTI(self):
        # ! talk with Arman about what we will be displaying
        # getting info on which runs were successful
        group = self.TEG.groupby("UID")['TEG_STATUS']
        completed_or_not = group.apply(lambda x: np.all(x == "Test Completed")) \
                                .replace(False, "Not all tests completed") \
                                .reset_index()
    
        not_completed = completed_or_not[completed_or_not["TEG_STATUS"] == "Not all tests completed"]
        completed = completed_or_not[completed_or_not['TEG_STATUS'] == True]

        not_completed_ids = not_completed["UID"].to_list()
        completed_ids = completed["UID"].to_list()

        # will need this later
        not_completed_dict = list(not_completed.set_index('UID').to_dict().values())[0]
        not_completed_dict = {k: {"status": "Fail", "description": v} 
                              for k, v in not_completed_dict.items() }

        # difference over mean check 
        completed = self.TEG[self.TEG.index.isin(completed_ids)]

        res = completed.groupby(["UID", "TEST_NAME"]) \
                .agg(delta_r=("TEG_VALUE_R", lambda x: abs(x[0] - x[1])),  
                     mean_r= ("TEG_VALUE_R", lambda x: np.mean(x)))
        res = res.reset_index()

        res['difference_over_mean_check'] = np.where((res['delta_r'] / res['mean_r']) <= 0.4, "OK", "Fail")

        # over 4 standard deviations check
        means = res.groupby("TEST_NAME")["delta_r"].apply(np.mean)
        afxa_mean, dti_mean = means.loc["AFXa"], means.loc["DTI"]
        logger.debug(f"afxa mean: {afxa_mean}, dti mean: {dti_mean}")
        std_devs = res.groupby("TEST_NAME")["delta_r"].apply(np.std)
        afxa_std, dti_std = std_devs.loc["AFXa"], std_devs.loc["DTI"]
        logger.debug(f"afxa std: {afxa_std}, dti std: {dti_std}")


        def std_deviation_check(x):
            if x['TEST_NAME'] == "AFXa":
                sigmas = (x['delta_r'] - afxa_mean) / afxa_std 
            elif x['TEST_NAME'] == "DTI":
                sigmas = (x['delta_r'] - dti_mean) / dti_std
            
            if sigmas <= 4:
                return "OK"
            return "Fail"
            
        res["over_4_std_devs_check"] = res.apply(std_deviation_check, axis=1)

        res.drop(["delta_r", "mean_r"], axis=1)
        
        def get_r_time_status(x):
            diff = x['difference_over_mean_check']
            dev = x['over_4_std_devs_check']

            if diff == "Fail" and dev == "Fail":
                msg = "Failed both `difference over mean` and `over 4 std devs`"
            elif diff == "Fail":
                msg = "Failed `difference over mean` check"
            elif dev == "Fail":
                msg = "Failed `over 4 std devs` check"
            else:
                msg = "OK"
                
            status = "OK" if msg == "OK" else "Fail"
            
            return {"status": status, "description": msg}

        res["r_time_status"] = res.apply(get_r_time_status, axis=1)

        # ! Assumes that test status for the same run is the same for all channels (DTI, AFXa)
        def process_output(res, test_name):
            res = res[res["TEST_NAME"] == test_name]

            res = res[["UID", "r_time_status"]].set_index("UID")
            
            res = pd.Series(res["r_time_status"], name=test_name)
            res_dict = res.to_dict()
            res_dict.update(not_completed_dict)
            
            new_dict = self.make_json_nested(res_dict, test_name, dont_include_status_key=True)
            
            self.checks_list.append(new_dict)
            return new_dict
            
        process_output(res, "AFXa")
        process_output(res, "DTI")

    def FADS(self): # checks if both AFXa and DTI passed
        # ! has to be called after AFXa_and_DTI function
        for subject_id, info in self.checks.items():
            for sample_id, info in info.items():
                if "AFXa" in info and "DTI" in info:
                    afxa_ok = info["AFXa"] == "OK"
                    dti_ok = info["DTI"] == "OK"
                    if afxa_ok and dti_ok:
                        msg = "OK"
                    elif afxa_ok:
                        msg = "DTI failed"
                    elif dti_ok:
                        msg = "AFXa failed"
                    else:
                        msg = "Both DTI and AFXa failed"                

                    status = "OK" if msg == "OK" else "Fail"

                    self.checks[subject_id][sample_id]["FADS"] = {"status": status, "description": msg}
    
    
    
    def run_all_checks(self):
        checks = ["DM_input", "PD_comment", "structural_integrity",  \
                  "time_between_replicate_runs", "data_quality_requirement", \
                  "lab_LLOQ", "lab_edc_compound_mismatch", "EDC_timing", \
                  "AFXa_and_DTI"]
        
        for check in checks:
            logger.info(f"Running {check} check")
            res = getattr(self, check)()
            logger.debug(f"{res}\n")
        self.restructure_json()
        
        logger.info("Running FADS check")
        self.FADS()
        
        
        file_path = os.path.join(self.output_folder, self.file_name)
        
        logger.info(f"Saving checks to {file_path}")
        logger.info(f"Checks: {self.checks}")
        with open(file_path, 'w') as f:
            json.dump(self.checks, f)
        
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
    def make_json_nested(res_dict, test_name, dont_include_status_key=False):
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
            
            if dont_include_status_key:
                new_dict[sample_id][subject_id][test_name] = value
            else:
                new_dict[sample_id][subject_id][test_name]["status"] = value

        return new_dict

    
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
    
    
    ch.run_all_checks()
    

    with open("checks_new_format.json", "w") as f:
        f.write(json.dumps(ch.checks, indent=4))
        
        
