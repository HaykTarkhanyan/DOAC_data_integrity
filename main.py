from fastapi import FastAPI
from checker import Checker

DATA_PATH = "data_integrity.xlsx"

app = FastAPI()


@app.get("/all_checks")
def run_all_checks(data_path: str):
    ch = Checker(data_path)
    
    ch.time_between_replicate_runs()
    ch.structural_integrity()
    ch.PD_comment()
    ch.restructure_json()
    
    return ch.checks




