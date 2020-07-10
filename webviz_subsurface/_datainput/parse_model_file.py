from bs4 import BeautifulSoup
import os
from pathlib import Path

def extract_surface_names(basedir):
    model_file = os.path.join(basedir, 'model_file.xml')
    with open(model_file, 'r') as file:
        soup = BeautifulSoup(file, 'xml')
    surface_wrappers = soup.find_all('surface')
    surface_names = []
    for s in surface_wrappers:
        name = s.find('name')
        surface_names.append(name.get_text())
    return surface_names

def get_surface_files(basedir):
    surface_names = extract_surface_names(basedir)
    surface_dir = os.path.join(basedir, 'output', 'surfaces')
    surface_files = [os.path.join(surface_dir, 'd_' + s + '.rxb') for s in surface_names]
    return surface_files

def get_error_files(basedir):
    surface_names = extract_surface_names(basedir)
    surface_dir = os.path.join(basedir, 'output', 'surfaces')
    error_files = [os.path.join(surface_dir, 'de_' + s + '.rxb') for s in surface_names]
    return error_files

def get_well_files(basedir):
    well_dir = os.path.join(basedir, 'input', 'welldata')
    well_dir_list = os.listdir(well_dir)
    well_files = []
    for i, w in enumerate(well_dir_list):
        if Path(w).suffix == '.txt':
            well_files.append(os.path.join(well_dir, w))
    return well_files


if __name__ == '__main__':
    basedir = Path(r"C:\Users\ivarb\OneDrive\Documents\webViz\Datasets\complex_model")
    print(get_well_files(basedir))

