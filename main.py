from fastapi import FastAPI
from Checke import Checker

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

@app.get("/data_sources")
def get_available_sources(data_path: str):
    ch = Checker(data_path) 
    
    return ch.get_available_sources()   

if __name__ == "__main__":
    run_all_checks(DATA_PATH)


