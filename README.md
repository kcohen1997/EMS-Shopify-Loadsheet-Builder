# Create-Shopify-Loadsheet

This repository creates a GUI translating product information from e-commerce site Volusion. The resulting load sheet contains the following information:

* **Part #**: taken from "Variant SKU" field
* **Title**: taken from "Title" field
* **Retail Price**: taken from "Variant Price" field
* **Jobber Price (optional)**: calculated from "Variant Price" field, default is 0.85 times the Retail Price
* **Dealer Price (optional)**: calculated from "Variant Price" field, default is 0.75 times the Retail Price
* **OEM/WD Price (optional)**: calculated from "Variant Price" field, default is 0.675 times the Retail Price
* **Weight (lb)**: taken from "Product Grams" field (converted from "grams to lbs"
* **Description**: taken from "Body (HTML)" field
* **Image**: taken from "Image Src" field

For access to the completed exe file, visit the "Release" section.

## How To Create Executable File

### Step 1: Download Product CSV File from Volusion and Python File From Repository (create_shopify_loadsheet.py)

If using sample csv file, download "volusion_sample_data.csv"

### Step 2: Download the following onto your computer:

#### Python (Programming Language): 

How To Download:

https://www.python.org/downloads/

Run this command in terminal to see if downloaded properly:

```bash
python --version
```

pyinstaller --onefile --noconsole create_volusion_loadsheet.py

#### Pip (Python Package Manager):

How To Download:

pip install pyinstaller

Run this command in terminal to see if downloaded properly:

```bash
pip --version
```

#### Pyinstaller (Converts Python Scripts Into Executable Files):

How To Download:

pip download pyinstaller

Run this command in terminal to see if downloaded properly:

```bash
pyinstaller --version
```
### Step 3:  In terminal, go to the same folder/directory as the Python file and enter the following command:

```bash
pyinstaller --onefile --noconsole create_volusion_loadsheet.py
```
