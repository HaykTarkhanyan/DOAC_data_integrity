from fastapi import FastAPI
from checker import Checker

DATA_PATH = "data_integrity.xlsx"

app = FastAPI()

# TODO summary table (which data sources are available )
# Seperate json

# ըստ 701ի, ֆունցկիա որ կընդունի սաբջեքթ այ դիներ

@app.get("/all_checks")
def run_all_checks(data_path: str):
    ch = Checker(data_path)
    
    ch.run_all_checks()
    
    return ch.checks


run_all_checks(DATA_PATH)


